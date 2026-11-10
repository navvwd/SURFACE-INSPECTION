"""ResNet18 (He et al., 2016; BasicBlock, [2,2,2,2]) in Keras, layer-for-layer compatible with
torchvision.models.resnet18 so ImageNet weights can be ported (see training/port_resnet18_weights.py).

PyTorch pads symmetrically; TensorFlow's padding="same" pads asymmetrically for stride 2. Every
padded convolution therefore uses explicit ZeroPadding2D + padding="valid" to match torchvision.
BatchNorm epsilon = 1e-5 (PyTorch default).

Layer names mirror torchvision parameter names with "." replaced by "_", e.g.
torch `layer2.0.downsample.0`  ->  keras `layer2_0_downsample_0`.
"""
from __future__ import annotations

import keras
from keras import layers

BN_EPS = 1e-5
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def _conv_bn(x, filters, kernel, stride, pad, name_conv, name_bn):
    if pad:
        x = layers.ZeroPadding2D(pad, name=f"{name_conv}_pad")(x)
    x = layers.Conv2D(filters, kernel, strides=stride, padding="valid", use_bias=False, name=name_conv)(x)
    return layers.BatchNormalization(epsilon=BN_EPS, name=name_bn)(x)


def _basic_block(x, filters, stride, prefix):
    shortcut = x
    y = _conv_bn(x, filters, 3, stride, 1, f"{prefix}_conv1", f"{prefix}_bn1")
    y = layers.ReLU(name=f"{prefix}_relu1")(y)
    y = _conv_bn(y, filters, 3, 1, 1, f"{prefix}_conv2", f"{prefix}_bn2")
    if stride != 1 or x.shape[-1] != filters:
        shortcut = _conv_bn(x, filters, 1, stride, 0, f"{prefix}_downsample_0", f"{prefix}_downsample_1")
    y = layers.Add(name=f"{prefix}_add")([y, shortcut])
    return layers.ReLU(name=f"{prefix}_out")(y)


def resnet18_backbone(input_tensor) -> keras.KerasTensor:
    """Input: ImageNet-normalised RGB tensor (N,224,224,3). Output: layer4 feature map (N,7,7,512)."""
    x = _conv_bn(input_tensor, 64, 7, 2, 3, "conv1", "bn1")
    x = layers.ReLU(name="relu")(x)
    x = layers.ZeroPadding2D(1, name="maxpool_pad")(x)  # zero-pad == -inf pad after ReLU (values >= 0)
    x = layers.MaxPooling2D(3, strides=2, name="maxpool")(x)
    for stage, (filters, stride) in enumerate([(64, 1), (128, 2), (256, 2), (512, 2)], start=1):
        x = _basic_block(x, filters, stride, f"layer{stage}_0")
        x = _basic_block(x, filters, 1, f"layer{stage}_1")
    return x


def build_resnet18_imagenet() -> keras.Model:
    """Full ImageNet classifier (with fc) - used only to verify the weight port against torchvision."""
    inp = keras.Input((224, 224, 3), name="rgb_normalized")
    x = resnet18_backbone(inp)
    x = layers.GlobalAveragePooling2D(name="avgpool")(x)
    out = layers.Dense(1000, name="fc")(x)
    return keras.Model(inp, out, name="resnet18_imagenet")


def build_resnet18_classifier(cfg: dict, num_classes: int) -> keras.Model:
    """Steel-defect classifier. Input: raw gray (200,200,1) 0-255, same contract as the custom CNN."""
    size = cfg.get("resize_to", 224)
    inp = keras.Input(shape=tuple(cfg["input_shape"]), name="image")
    x = layers.Resizing(size, size, interpolation="bilinear", name="resize")(inp)
    x = layers.Rescaling(1.0 / 255, name="rescale")(x)
    x = layers.Concatenate(axis=-1, name="gray_to_rgb")([x, x, x])
    x = layers.Normalization(mean=IMAGENET_MEAN, variance=[s ** 2 for s in IMAGENET_STD],
                             name="imagenet_normalize")(x)
    x = resnet18_backbone(x)
    x = layers.GlobalAveragePooling2D(name="avgpool")(x)
    x = layers.Dropout(cfg.get("dropout_head", 0.0), name="head_dropout")(x)
    logits = layers.Dense(num_classes, name="logits")(x)
    probs = layers.Softmax(name="probs")(logits)
    model = keras.Model(inp, probs, name="resnet18")

    weights = cfg.get("pretrained_weights")
    if weights:
        from ml.utils.config import resolve
        backbone_names = _backbone_layer_names(model)
        _load_backbone_weights(model, resolve(weights), backbone_names)
    return model


HEAD_LAYERS = {"head_dropout", "logits", "probs"}


def _backbone_layer_names(model: keras.Model) -> list[str]:
    return [l.name for l in model.layers if l.weights and l.name not in HEAD_LAYERS
            and l.name not in {"imagenet_normalize"}]


def _load_backbone_weights(model: keras.Model, path, names: list[str]) -> None:
    """Load ported backbone weights from an h5 file with one group per layer name
    (written by training/port_resnet18_weights.py). Matching by name is robust to head changes."""
    import h5py
    import numpy as np

    with h5py.File(path, "r") as f:
        missing = [n for n in names if n not in f]
        if missing:
            raise ValueError(f"Pretrained file lacks layers: {missing[:5]}")
        for n in names:
            layer = model.get_layer(n)
            layer.set_weights([np.asarray(f[n][str(i)]) for i in range(len(layer.weights))])


def set_trainable(model: keras.Model, spec) -> None:
    """spec: 'all' | 'head' | list of prefixes (e.g. ['layer3','layer4','head']).
    BatchNorm layers are ALWAYS frozen (inference mode) for the ResNet - see config comment."""
    for layer in model.layers:
        if not layer.weights:
            continue
        if spec == "all":
            on = True
        elif spec == "head":
            on = layer.name in HEAD_LAYERS
        else:
            prefixes = [p for p in spec if p != "head"]
            on = (layer.name in HEAD_LAYERS and "head" in spec) or any(layer.name.startswith(p) for p in prefixes)
        if isinstance(layer, keras.layers.BatchNormalization) and model.name == "resnet18":
            on = False
        if isinstance(layer, keras.layers.Normalization):
            on = False
        layer.trainable = on
