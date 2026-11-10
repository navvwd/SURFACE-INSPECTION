"""Port torchvision's ImageNet ResNet18 weights into the Keras ResNet18 and verify numerically.

Usage:
    python -m training.port_resnet18_weights

Steps
  1. Load torchvision.models.resnet18(weights=IMAGENET1K_V1) (downloaded to the torch hub cache).
  2. Copy every conv / BN / fc tensor into the Keras model (layout conversion below).
  3. Verify: run both models on identical inputs (random + real NEU images) and compare logits.
  4. Save backbone weights (no fc) to models/pretrained/resnet18_imagenet_backbone.h5
     and a verification report next to it.

Layout conversion
  conv weight  torch [out, in, kh, kw]  -> keras [kh, kw, in, out]
  BN           weight, bias, running_mean, running_var -> gamma, beta, moving_mean, moving_variance
  fc weight    torch [out, in]          -> keras [in, out]
"""
from __future__ import annotations

import os

os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "1")

import h5py
import numpy as np
import pandas as pd
import torch
import torchvision
from PIL import Image

from ml.models.resnet18 import IMAGENET_MEAN, IMAGENET_STD, build_resnet18_imagenet
from ml.utils.config import resolve, write_json

OUT = resolve("models/pretrained/resnet18_imagenet_backbone.h5")


def torch_to_keras_name(torch_prefix: str) -> str:
    return torch_prefix.replace(".", "_")


def port(tmodel: torch.nn.Module, kmodel) -> int:
    sd = {k: v.detach().cpu().numpy() for k, v in tmodel.state_dict().items()}
    copied = 0
    for name, module in tmodel.named_modules():
        if isinstance(module, torch.nn.Conv2d):
            kmodel.get_layer(torch_to_keras_name(name)).set_weights([sd[f"{name}.weight"].transpose(2, 3, 1, 0)])
            copied += 1
        elif isinstance(module, torch.nn.BatchNorm2d):
            kmodel.get_layer(torch_to_keras_name(name)).set_weights(
                [sd[f"{name}.weight"], sd[f"{name}.bias"], sd[f"{name}.running_mean"], sd[f"{name}.running_var"]])
            copied += 1
        elif isinstance(module, torch.nn.Linear):
            kmodel.get_layer("fc").set_weights([sd[f"{name}.weight"].T, sd[f"{name}.bias"]])
            copied += 1
    return copied


def main() -> None:
    torch.manual_seed(0)
    weights = torchvision.models.ResNet18_Weights.IMAGENET1K_V1
    tmodel = torchvision.models.resnet18(weights=weights).eval()
    kmodel = build_resnet18_imagenet()
    n = port(tmodel, kmodel)

    # verification inputs: 8 random normalised tensors + 6 real NEU images (one per class, gray->RGB)
    rng = np.random.default_rng(0)
    rand = rng.normal(0, 1, (8, 224, 224, 3)).astype("float32")
    df = pd.read_csv(resolve("dataset/splits/train.csv")).groupby("label").head(1)
    real = []
    for p in df["filepath"]:
        g = np.asarray(Image.open(resolve(p)).convert("L").resize((224, 224), Image.BILINEAR), dtype="float32") / 255
        rgb = np.repeat(g[..., None], 3, axis=-1)
        real.append((rgb - np.array(IMAGENET_MEAN)) / np.array(IMAGENET_STD))
    x = np.concatenate([rand, np.array(real, dtype="float32")])

    with torch.no_grad():
        t_out = tmodel(torch.from_numpy(x.transpose(0, 3, 1, 2))).numpy()
    k_out = kmodel(x, training=False).numpy()
    diff = np.abs(t_out - k_out)
    top1 = float((t_out.argmax(1) == k_out.argmax(1)).mean())
    top5 = float(np.mean([set(np.argsort(-a)[:5]) == set(np.argsort(-b)[:5]) for a, b in zip(t_out, k_out)]))
    rel_err = float(diff.max() / np.abs(t_out).max())
    ok = diff.max() < 1e-3 and top1 == 1.0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(OUT, "w") as f:
        for layer in kmodel.layers:
            if layer.weights and layer.name != "fc":
                g = f.create_group(layer.name)
                for i, w in enumerate(layer.get_weights()):
                    g.create_dataset(str(i), data=w)
        f.attrs["source"] = f"torchvision {torchvision.__version__} ResNet18_Weights.IMAGENET1K_V1"

    report = {
        "source": f"torchvision {torchvision.__version__}, ResNet18_Weights.IMAGENET1K_V1",
        "torchvision_imagenet_top1_reported": weights.meta["_metrics"]["ImageNet-1K"]["acc@1"],
        "modules_copied": n, "verification_inputs": int(len(x)),
        "max_abs_logit_diff": float(diff.max()), "mean_abs_logit_diff": float(diff.mean()),
        "max_relative_diff": rel_err, "top1_agreement": top1, "top5_set_agreement": top5,
        "passed": bool(ok), "output_file": "models/pretrained/resnet18_imagenet_backbone.h5",
    }
    write_json(report, OUT.with_name("resnet18_port_verification.json"))
    print(report)
    if not ok:
        raise SystemExit("Weight port verification FAILED")


if __name__ == "__main__":
    main()
