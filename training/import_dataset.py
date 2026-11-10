"""Step 1 - import the downloaded NEU-CLS parquet mirror into dataset/raw/NEU-CLS/<Class>/.

Usage (from project root):
    python -m training.import_dataset [--config configs/data.yaml] [--force]

Skip this step if you placed an official NEU-CLS copy into dataset/raw/NEU-CLS/<Class>/ yourself.
"""
import argparse
import json

from ml.data.importer import import_hf_parquet
from ml.utils.config import PROJECT_ROOT, load_config


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="configs/data.yaml")
    ap.add_argument("--force", action="store_true", help="overwrite an existing raw_dir")
    args = ap.parse_args()
    cfg = load_config(args.config)
    print(json.dumps(import_hf_parquet(cfg, PROJECT_ROOT, force=args.force), indent=2))


if __name__ == "__main__":
    main()
