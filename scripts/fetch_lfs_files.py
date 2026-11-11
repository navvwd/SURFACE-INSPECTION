"""Replace Git LFS pointer files with the real files when a host clones without LFS (e.g. some PaaS builders).

Usage: python scripts/fetch_lfs_files.py <path> [<path> ...]

A file is treated as a pointer when it starts with the LFS spec line. It is then downloaded from GitHub's
media endpoint for the repo/branch given by $GITHUB_REPO (default navvwd/SURFACE-INSPECTION) and
$RENDER_GIT_BRANCH / $GIT_BRANCH (default main). The download is checked against the pointer's sha256 and size.
"""
from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = os.environ.get("GITHUB_REPO", "navvwd/SURFACE-INSPECTION")
BRANCH = os.environ.get("RENDER_GIT_BRANCH") or os.environ.get("GIT_BRANCH") or "main"


def pointer_info(p: Path) -> dict | None:
    if p.stat().st_size > 1024:
        return None
    text = p.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("version https://git-lfs.github.com/spec"):
        return None
    info = dict(line.split(" ", 1) for line in text.strip().splitlines() if " " in line)
    return {"sha256": info["oid"].split(":", 1)[1], "size": int(info["size"])}


def main(paths: list[str]) -> int:
    failed = 0
    for rel in paths:
        p = ROOT / rel
        if not p.exists():
            print(f"missing: {rel}"); failed += 1; continue
        ptr = pointer_info(p)
        if ptr is None:
            print(f"ok (real file, {p.stat().st_size / 1e6:.1f} MB): {rel}"); continue
        url = f"https://media.githubusercontent.com/media/{REPO}/{BRANCH}/{rel}"
        print(f"downloading {rel} ({ptr['size'] / 1e6:.1f} MB) from {url}")
        tmp = p.with_suffix(p.suffix + ".part")
        h = hashlib.sha256()
        with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk); h.update(chunk)
        if h.hexdigest() != ptr["sha256"] or tmp.stat().st_size != ptr["size"]:
            tmp.unlink(missing_ok=True)
            print(f"CHECKSUM MISMATCH: {rel}"); failed += 1; continue
        tmp.replace(p)
        print(f"ok (downloaded, verified): {rel}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
