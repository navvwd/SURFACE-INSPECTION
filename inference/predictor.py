"""Model loading, input validation and prediction.

Input contract (identical to training): single-channel gray image, 200x200, values 0-255.
Inputs that deviate are converted, but each deviation is recorded as an *input flag* so the
decision engine can route the image to manual review - the model was never trained on them.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np

EXPECTED_SIZE = (200, 200)          # (width, height)
COLOR_TOLERANCE = 2.0               # mean |R-G| or |G-B| above this => genuinely colour image
UNIFORM_STD = 2.0                   # gray-level std below this => blank / uniform image


@dataclass
class PreparedImage:
    gray: np.ndarray                 # (200, 200) uint8 - exactly what the model sees
    original_shape: tuple
    flags: list[str] = field(default_factory=list)


@dataclass
class Prediction:
    model_name: str
    model_version: str
    predicted_class: str
    class_index: int
    confidence: float
    margin: float
    normalized_entropy: float
    probabilities: dict[str, float]
    latency_ms: float
    input_flags: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def prepare_image(data: bytes | np.ndarray) -> PreparedImage:
    """Decode bytes (PNG/BMP/JPG/TIFF...) or accept an array, and coerce to the model contract."""
    if isinstance(data, (bytes, bytearray)):
        arr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_UNCHANGED)
        if arr is None:
            raise ValueError("File could not be decoded as an image")
    else:
        arr = np.asarray(data)
    flags: list[str] = []
    original_shape = tuple(arr.shape)

    if arr.dtype != np.uint8:
        flags.append(f"bit_depth_converted_from_{arr.dtype}")
        arr = cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    if arr.ndim == 3:
        if arr.shape[2] == 4:
            arr = arr[..., :3]
        c = arr.astype(np.int16)
        if max(np.abs(c[..., 0] - c[..., 1]).mean(), np.abs(c[..., 1] - c[..., 2]).mean()) > COLOR_TOLERANCE:
            flags.append("colour_image_converted_to_gray")
        arr = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    h, w = arr.shape[:2]
    if (w, h) != EXPECTED_SIZE:
        flags.append(f"resized_from_{w}x{h}")
        arr = cv2.resize(arr, EXPECTED_SIZE, interpolation=cv2.INTER_AREA if w > 200 else cv2.INTER_LINEAR)
    if float(arr.std()) < UNIFORM_STD:
        flags.append("near_uniform_image")
    return PreparedImage(gray=arr, original_shape=original_shape, flags=flags)


class ModelBundle:
    """A trained model from the registry folder models/<name>/<version>/."""

    def __init__(self, model_dir: str | Path):
        import keras
        import tensorflow as tf

        self.dir = Path(model_dir)
        self.meta = json.loads((self.dir / "train_meta.json").read_text())
        eval_path = self.dir / "evaluation.json"
        self.evaluation = json.loads(eval_path.read_text()) if eval_path.exists() else None
        self.name = self.meta["model_name"]
        self.version = self.meta["model_version"]
        self.classes: list[str] = self.meta["classes"]
        self.gradcam_layer: str = self.meta["gradcam_layer"]
        self.model = keras.models.load_model(self.dir / "model.keras")
        self._forward = tf.function(lambda x: self.model(x, training=False), reduce_retracing=True)
        self._forward(np.zeros((1, 200, 200, 1), np.float32))  # warm-up / trace once
        self._gradcam = None

    @property
    def key(self) -> str:
        return f"{self.name}:{self.version}"

    def predict(self, img: PreparedImage) -> Prediction:
        x = img.gray.astype(np.float32)[None, ..., None]
        t0 = time.perf_counter()
        probs = self._forward(x).numpy()[0].astype(float)
        latency = (time.perf_counter() - t0) * 1000
        order = np.argsort(-probs)
        p = np.clip(probs, 1e-12, 1.0)
        entropy = float(-(p * np.log(p)).sum() / math.log(len(p)))
        return Prediction(
            model_name=self.name, model_version=self.version,
            predicted_class=self.classes[order[0]], class_index=int(order[0]),
            confidence=float(probs[order[0]]), margin=float(probs[order[0]] - probs[order[1]]),
            normalized_entropy=entropy,
            probabilities={c: float(v) for c, v in zip(self.classes, probs)},
            latency_ms=round(latency, 2), input_flags=list(img.flags),
        )

    @property
    def gradcam(self):
        if self._gradcam is None:
            from inference.gradcam import GradCAM
            self._gradcam = GradCAM(self.model, self.gradcam_layer)
        return self._gradcam
