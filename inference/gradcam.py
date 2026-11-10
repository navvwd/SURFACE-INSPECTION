"""Grad-CAM (Selvaraju et al., 2017) for the Keras models in this project.

    weights_k = mean over (i,j) of d logit_c / d A_k(i,j)        (A = target conv feature maps)
    CAM       = ReLU( sum_k weights_k * A_k )                    normalised to [0, 1]

The gradient is taken w.r.t. the PRE-softmax logit of the explained class (layer "logits").

INTERPRETATION CAVEAT - shown wherever a heatmap is displayed:
Grad-CAM highlights regions that most increased the model's score for the predicted class. It is a
coarse explanation of model behaviour (25x25 grid for the custom CNN, 7x7 for ResNet18, upsampled),
NOT a measured or verified defect boundary, and it can highlight background texture if the model
relies on it.
"""
from __future__ import annotations

import cv2
import numpy as np

CAVEAT = ("Grad-CAM shows image regions that most influenced the model's prediction. It is an "
          "explanation of model behaviour, not a measured or verified defect boundary.")


class GradCAM:
    def __init__(self, model, layer_name: str, logits_layer: str = "logits"):
        import keras
        import tensorflow as tf

        self._tf = tf
        self.layer_name = layer_name
        self.grad_model = keras.Model(model.inputs,
                                      [model.get_layer(layer_name).output, model.get_layer(logits_layer).output])

    def compute(self, gray: np.ndarray, class_index: int | None = None) -> tuple[np.ndarray, int]:
        """gray: (200,200) uint8. Returns (heatmap in [0,1] at input resolution, explained class)."""
        tf = self._tf
        x = tf.constant(gray.astype(np.float32)[None, ..., None])
        with tf.GradientTape() as tape:
            feats, logits = self.grad_model(x, training=False)
            if class_index is None:
                class_index = int(tf.argmax(logits[0]))
            score = logits[:, class_index]
        grads = tape.gradient(score, feats)[0].numpy()        # (h, w, k)
        fmap = feats[0].numpy()
        weights = grads.mean(axis=(0, 1))                      # (k,)
        cam = np.maximum((fmap * weights).sum(axis=-1), 0)
        cam = cam / cam.max() if cam.max() > 1e-12 else np.zeros_like(cam)
        cam = cv2.resize(cam.astype(np.float32), (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_LINEAR)
        return np.clip(cam, 0, 1), class_index


def overlay(gray: np.ndarray, heatmap: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    """Blend a JET-coloured heatmap over the grayscale image. Returns BGR uint8."""
    base = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    colour = cv2.applyColorMap((heatmap * 255).astype(np.uint8), cv2.COLORMAP_JET)
    return cv2.addWeighted(colour, alpha, base, 1 - alpha, 0)


def heatmap_stats(heatmap: np.ndarray) -> dict:
    """Simple descriptive statistics of the explanation (not a defect measurement)."""
    y, x = np.unravel_index(int(np.argmax(heatmap)), heatmap.shape)
    return {"peak_xy": [int(x), int(y)], "area_above_0_5": float((heatmap >= 0.5).mean())}
