"""Custom CNN for 6-class steel-surface defect classification.

    input (200,200,1) raw gray 0-255
    Rescaling(1/255) -> Normalization(train mean/std)
    [Conv(5x5,32)  - BN - ReLU - MaxPool]  -> 100x100
    [Conv(3x3,64)  - BN - ReLU - MaxPool]  -> 50x50
    [Conv(3x3,128) - BN - ReLU - MaxPool]  -> 25x25
    [Conv(3x3,256) - BN - ReLU ("gradcam_target") - MaxPool] -> 12x12
    GlobalAveragePooling - Dropout - Dense(128, ReLU) - Dropout - Dense(6) "logits" - Softmax "probs"

Logits are a separate layer so Grad-CAM can differentiate the pre-softmax class score.
BatchNorm momentum is 0.9 (not the Keras default 0.99): with only 40 steps per epoch the 0.99
moving averages need ~12 epochs to forget their initialisation, which made inference-mode
validation accuracy collapse to near chance early in training (DECISIONS D-015).
Convolutions have no bias because BatchNorm's beta already provides the offset.
"""
from __future__ import annotations

import keras
from keras import layers, regularizers


def build_custom_cnn(cfg: dict, num_classes: int, norm_stats: dict) -> keras.Model:
    reg = regularizers.l2(cfg.get("l2", 0.0))
    inp = keras.Input(shape=tuple(cfg["input_shape"]), name="image")
    x = layers.Rescaling(1.0 / 255, name="rescale")(inp)
    x = layers.Normalization(mean=norm_stats["mean"], variance=norm_stats["std"] ** 2, name="normalize")(x)

    filters = cfg["filters"]
    for i, f in enumerate(filters, start=1):
        k = 5 if i == 1 else 3
        x = layers.Conv2D(f, k, padding="same", use_bias=False, kernel_regularizer=reg, name=f"conv{i}")(x)
        x = layers.BatchNormalization(momentum=cfg.get("bn_momentum", 0.9), name=f"bn{i}")(x)
        last = i == len(filters)
        x = layers.ReLU(name="gradcam_target" if last else f"relu{i}")(x)
        x = layers.MaxPooling2D(2, name=f"pool{i}")(x)

    x = layers.GlobalAveragePooling2D(name="gap")(x)
    x = layers.Dropout(cfg["dropout_conv_head"], name="drop_gap")(x)
    x = layers.Dense(cfg["dense_units"], activation="relu", kernel_regularizer=reg, name="fc")(x)
    x = layers.Dropout(cfg["dropout_dense"], name="drop_fc")(x)
    logits = layers.Dense(num_classes, name="logits")(x)
    probs = layers.Softmax(name="probs")(logits)
    return keras.Model(inp, probs, name="custom_cnn")
