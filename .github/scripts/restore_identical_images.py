"""Put back modified PNGs whose pixels are identical to the committed ones.

Pillow's wheels compress with zlib-ng, which picks a different match finder
on different CPUs, so the same figure can encode to different bytes on two
runners while every pixel is the same. A byte comparison then reports drift
in a figure nobody changed. This decodes both versions and restores the
committed file when the images match exactly, so the drift check compares
what a reader sees rather than how the compressor happened to pack it. Any
pixel that differs leaves the file modified, and the check fails as before.
"""

from __future__ import annotations

import io
import subprocess
import sys

import numpy as np
from PIL import Image


def _pixels(data: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(data)) as image:
        return np.asarray(image.convert("RGBA"))


def main() -> int:
    changed = subprocess.run(
        ["git", "diff", "--name-only", "--", "*.png"],
        check=True, capture_output=True, text=True,
    ).stdout.split()
    restored = 0
    for path in changed:
        committed = subprocess.run(
            ["git", "show", f"HEAD:{path}"], check=True, capture_output=True,
        ).stdout
        with open(path, "rb") as handle:
            current = handle.read()
        a, b = _pixels(committed), _pixels(current)
        if a.shape == b.shape and np.array_equal(a, b):
            subprocess.run(["git", "checkout", "--", path], check=True)
            restored += 1
    print(f"{restored} of {len(changed)} changed PNGs were byte-only differences; restored.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
