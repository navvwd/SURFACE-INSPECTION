"""Train a model from a YAML config.

Usage:
    python -m training.train --config configs/custom_cnn.yaml [--overwrite]

Writes models/<name>/<version>/:
    model.keras         final model (best val_loss weights of the last stage)
    history.csv         per-epoch loss/accuracy/lr for every stage
    train_meta.json     config snapshot, seed, library versions, timing, best epochs, val metrics
    config.yaml         copy of the training config
    data_config.yaml    copy of the data config (class order!)
and reports/<name>_<version>/training_curves.png
"""
from __future__ import annotations

import os

# Must be set before TensorFlow is imported (DECISIONS D-014).
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "1")

import argparse
import json
import platform
import shutil
import sys
import time
from datetime import datetime, timezone

import keras
import numpy as np
import pandas as pd
import tensorflow as tf

from ml.data.pipeline import make_dataset, read_manifest
from ml.models import build_model
from ml.models.resnet18 import set_trainable
from ml.utils.config import load_config, rel, resolve, write_json
from ml.utils.plots import plot_training_curves
from ml.utils.seed import set_global_seed


class _LRLogger(keras.callbacks.Callback):
    def on_epoch_end(self, epoch, logs=None):
        logs["lr"] = float(keras.ops.convert_to_numpy(self.model.optimizer.learning_rate))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    mcfg, dcfg_ref, tcfg = cfg["model"], cfg["data"], cfg["training"]
    data_cfg = load_config(dcfg_ref["config"])
    classes = data_cfg["dataset"]["classes"]
    seed = tcfg["seed"]
    set_global_seed(seed)

    out_dir = resolve(f"models/{mcfg['name']}/{mcfg['version']}")
    if out_dir.exists() and any(out_dir.iterdir()) and not args.overwrite:
        sys.exit(f"{rel(out_dir)} already exists; use --overwrite or bump model.version")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir = resolve(f"reports/{mcfg['name']}_{mcfg['version']}")
    report_dir.mkdir(parents=True, exist_ok=True)

    split_dir = data_cfg["split"]["out_dir"]
    split_report = json.loads((resolve(split_dir) / "split_report.json").read_text())
    norm = split_report["normalization_train_only"]

    bs = dcfg_ref["batch_size"]
    train_ds = make_dataset(read_manifest(split_dir, "train"), bs, training=True, seed=seed,
                            augmentation=dcfg_ref.get("augmentation"))
    val_ds = make_dataset(read_manifest(split_dir, "val"), bs, training=False, seed=seed)

    model = build_model(mcfg, len(classes), norm)
    ckpt = out_dir / "_best.weights.h5"
    history_rows, stage_meta, epoch_offset = [], [], 0
    t_all = time.perf_counter()

    for stage in tcfg["stages"]:
        set_trainable(model, stage["trainable"])
        model.compile(
            optimizer=keras.optimizers.Adam(stage["learning_rate"]),
            loss=keras.losses.SparseCategoricalCrossentropy(),
            metrics=[keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
        )
        n_trainable = int(sum(np.prod(w.shape) for w in model.trainable_weights))
        print(f"\n=== stage '{stage['name']}'  lr={stage['learning_rate']}  trainable params={n_trainable:,} ===")
        callbacks = [
            keras.callbacks.ModelCheckpoint(str(ckpt), monitor="val_loss", save_best_only=True,
                                            save_weights_only=True),
            keras.callbacks.EarlyStopping(monitor="val_loss", patience=tcfg["early_stopping_patience"]),
            keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=tcfg["reduce_lr_factor"],
                                              patience=tcfg["reduce_lr_patience"], min_lr=tcfg["min_lr"]),
            _LRLogger(),
        ]
        t0 = time.perf_counter()
        hist = model.fit(train_ds, validation_data=val_ds, epochs=epoch_offset + stage["epochs"],
                         initial_epoch=epoch_offset, callbacks=callbacks, verbose=2)
        dur = time.perf_counter() - t0
        model.load_weights(str(ckpt))  # best val_loss of this stage

        h = hist.history
        n_ep = len(h["loss"])
        best_i = int(np.argmin(h["val_loss"]))
        for i in range(n_ep):
            history_rows.append({"epoch": epoch_offset + i + 1, "stage": stage["name"],
                                 **{k: float(v[i]) for k, v in h.items()}})
        stage_meta.append({
            "name": stage["name"], "trainable": stage["trainable"], "learning_rate": stage["learning_rate"],
            "trainable_params": n_trainable, "epochs_run": n_ep, "best_epoch": epoch_offset + best_i + 1,
            "best_val_loss": float(h["val_loss"][best_i]), "best_val_accuracy": float(h["val_accuracy"][best_i]),
            "seconds": round(dur, 1), "seconds_per_epoch": round(dur / n_ep, 1),
        })
        epoch_offset += n_ep

    total_s = time.perf_counter() - t_all
    ckpt.unlink(missing_ok=True)
    val_loss, val_acc = model.evaluate(val_ds, verbose=0)
    model.save(out_dir / "model.keras")

    hist_df = pd.DataFrame(history_rows)
    hist_df.to_csv(out_dir / "history.csv", index=False)
    plot_training_curves(hist_df, report_dir / "training_curves.png", title=f"{mcfg['name']} {mcfg['version']}")
    shutil.copy(resolve(args.config), out_dir / "config.yaml")
    shutil.copy(resolve(dcfg_ref["config"]), out_dir / "data_config.yaml")

    meta = {
        "model_name": mcfg["name"], "model_version": mcfg["version"], "architecture": mcfg["architecture"],
        "classes": classes, "input_shape": mcfg["input_shape"], "gradcam_layer": mcfg["gradcam_layer"],
        "total_params": int(model.count_params()),
        "seed": seed, "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_training_seconds": round(total_s, 1), "stages": stage_meta,
        "final_val_loss": float(val_loss), "final_val_accuracy": float(val_acc),
        "normalization_train_only": norm,
        "environment": {"python": platform.python_version(), "tensorflow": tf.__version__,
                        "keras": keras.__version__, "numpy": np.__version__, "platform": platform.platform(),
                        "processor": platform.processor(), "device": "CPU",
                        "TF_ENABLE_ONEDNN_OPTS": os.environ.get("TF_ENABLE_ONEDNN_OPTS"),
                        "TF_DETERMINISTIC_OPS": os.environ.get("TF_DETERMINISTIC_OPS")},
    }
    write_json(meta, out_dir / "train_meta.json")
    print(f"\nTraining done in {total_s/60:.1f} min. val_loss={val_loss:.4f} val_acc={val_acc:.4f}")
    print(f"Saved {rel(out_dir / 'model.keras')}")


if __name__ == "__main__":
    main()
