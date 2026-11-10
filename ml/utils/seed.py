"""Reproducibility helpers.

Call `set_global_seed` at the very start of every entry point, before TensorFlow builds any graph.
Note: bit-exact reproducibility is only guaranteed on the same hardware, OS and library versions
(see requirements.lock.txt). CPU training with deterministic ops is used for this project.
"""
from __future__ import annotations

import os
import random
import sys

import numpy as np


def set_global_seed(seed: int, deterministic_tf: bool = True) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    if deterministic_tf:
        os.environ["TF_DETERMINISTIC_OPS"] = "1"
    random.seed(seed)
    np.random.seed(seed)
    # Seed TensorFlow only if the caller already imported it; data-only scripts stay TF-free.
    tf = sys.modules.get("tensorflow")
    if tf is not None:
        tf.random.set_seed(seed)
        if deterministic_tf:
            tf.config.experimental.enable_op_determinism()
