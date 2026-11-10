"""tf.data input pipelines built from the split manifests.

Contract shared by every model: the pipeline yields float32 images of shape (200, 200, 1) with raw
gray values in [0, 255]. Scaling/normalisation/resizing live INSIDE each model, so the deployed
model receives exactly what the inference API receives (no train/serve skew).

Augmentation (train split only) uses stateless random ops seeded from a seeded tf.data random
stream, so a given seed reproduces exactly the same augmented sequence. Val/test pipelines never
augment and never shuffle.
"""
from __future__ import annotations

import pandas as pd
import tensorflow as tf

from ml.utils.config import resolve

AUTOTUNE = tf.data.AUTOTUNE


def _load_png(path: tf.Tensor) -> tf.Tensor:
    img = tf.io.decode_png(tf.io.read_file(path), channels=1)
    return tf.cast(img, tf.float32)  # (H, W, 1), 0..255


def _make_augment(aug: dict):
    lo, hi = aug.get("contrast_range", [1.0, 1.0])
    delta = float(aug.get("brightness_max_delta", 0.0))

    def augment(img: tf.Tensor, seed: tf.Tensor) -> tf.Tensor:
        s = tf.random.experimental.stateless_split(seed, num=5)
        x = img / 255.0
        if aug.get("flip_horizontal"):
            x = tf.image.stateless_random_flip_left_right(x, s[0])
        if aug.get("flip_vertical"):
            x = tf.image.stateless_random_flip_up_down(x, s[1])
        if aug.get("rot90"):
            k = tf.random.stateless_uniform([], s[2], minval=0, maxval=4, dtype=tf.int32)
            x = tf.image.rot90(x, k)
        if delta > 0:
            x = tf.image.stateless_random_brightness(x, delta, s[3])
        if (lo, hi) != (1.0, 1.0):
            x = tf.image.stateless_random_contrast(x, lo, hi, s[4])
        return tf.clip_by_value(x, 0.0, 1.0) * 255.0

    return augment


def read_manifest(split_dir, split: str) -> pd.DataFrame:
    return pd.read_csv(resolve(split_dir) / f"{split}.csv")


def make_dataset(df: pd.DataFrame, batch_size: int, training: bool, seed: int,
                 augmentation: dict | None = None) -> tf.data.Dataset:
    paths = [str(resolve(p)) for p in df["filepath"]]
    labels = df["label_idx"].astype("int32").tolist()
    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if training:
        ds = ds.shuffle(len(paths), seed=seed, reshuffle_each_iteration=True)
    ds = ds.map(lambda p, y: (_load_png(p), y), num_parallel_calls=AUTOTUNE, deterministic=True)
    if training and augmentation:
        augment = _make_augment(augmentation)
        seeds = tf.data.Dataset.random(seed=seed, rerandomize_each_iteration=True).batch(2)
        ds = tf.data.Dataset.zip((ds, seeds)).map(
            lambda xy, s: (augment(xy[0], s), xy[1]), num_parallel_calls=AUTOTUNE, deterministic=True)
    return ds.batch(batch_size).prefetch(AUTOTUNE)
