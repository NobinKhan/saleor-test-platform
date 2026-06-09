"""Seed harness_reference volume from baked corpus, then exec the app."""

from __future__ import annotations

import os
import shutil
import sys

REFERENCE_DIR = "/app/reference"
BAKED_DIR = "/app/reference-baked"
REGISTRY_MARKER = os.path.join(REFERENCE_DIR, "corpora", "registry.json")


def _seed_reference_volume() -> None:
    if os.path.isfile(REGISTRY_MARKER):
        return
    os.makedirs(REFERENCE_DIR, exist_ok=True)
    for name in os.listdir(BAKED_DIR):
        src = os.path.join(BAKED_DIR, name)
        dst = os.path.join(REFERENCE_DIR, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)


def main() -> None:
    _seed_reference_volume()
    os.execvp("python", ["python", *sys.argv[1:]])


if __name__ == "__main__":
    main()
