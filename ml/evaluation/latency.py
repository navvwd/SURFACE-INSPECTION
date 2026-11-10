"""CPU inference latency benchmark.

Measures the model forward pass only (no file decoding, no Grad-CAM), using a direct
`model(x, training=False)` call wrapped in tf.function, after warm-up runs. Reported numbers are
specific to this machine's CPU and thread settings and are not a hardware real-time guarantee.
"""
from __future__ import annotations

import time

import numpy as np
import tensorflow as tf


def benchmark(model, input_shape, runs: int = 200, warmup: int = 20, batch_sizes=(1, 32), seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    fwd = tf.function(lambda x: model(x, training=False), reduce_retracing=True)
    out = {}
    for bs in batch_sizes:
        x = tf.constant(rng.uniform(0, 255, (bs, *input_shape)).astype("float32"))
        for _ in range(warmup):
            fwd(x).numpy()
        n = runs if bs == 1 else max(20, runs // 10)
        times = []
        for _ in range(n):
            t0 = time.perf_counter()
            fwd(x).numpy()
            times.append((time.perf_counter() - t0) * 1000)
        t = np.array(times)
        out[f"batch_{bs}"] = {
            "runs": n,
            "median_ms": float(np.median(t)), "p95_ms": float(np.percentile(t, 95)),
            "mean_ms": float(t.mean()), "per_image_median_ms": float(np.median(t) / bs),
            "throughput_img_per_s": float(bs / (np.median(t) / 1000)),
        }
    return out
