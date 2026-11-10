from ml.models.custom_cnn import build_custom_cnn
from ml.models.resnet18 import build_resnet18_classifier


def build_model(model_cfg: dict, num_classes: int, norm_stats: dict):
    arch = model_cfg["architecture"]
    if arch == "custom_cnn":
        return build_custom_cnn(model_cfg, num_classes, norm_stats)
    if arch == "resnet18":
        return build_resnet18_classifier(model_cfg, num_classes)
    raise ValueError(f"Unknown architecture: {arch}")
