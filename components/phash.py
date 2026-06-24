"""DCT-based 64-bit perceptual hash, dependency-light implementation.

This is the v0 dedup primitive (db_structured.md §5). For real workloads
we'll layer embedding-based dedup on top, but pHash is the cheap
prefilter.

Inputs / outputs:
  - `phash64(image: list[list[float]]) -> str`
      image is a 2D grayscale array (rows x cols), values in [0, 255]
      or [0, 1]. Returns a 16-char lowercase hex string.
  - `hamming(a: str, b: str) -> int`
      Hamming distance between two 16-char hex strings, 0..64.

We avoid numpy/cv2 here so the pre-commit and CI environment stays
minimal. A future faster implementation can drop in behind the same
interface.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

_DCT_SIZE = 32
_HASH_SIZE = 8  # 8x8 DCT coefficients => 64 bits


def _resize_grayscale(img: Sequence[Sequence[float]], target: int = _DCT_SIZE) -> list[list[float]]:
    """Nearest-neighbour resize to (target x target). Pure python."""
    h = len(img)
    if h == 0:
        raise ValueError("empty image")
    w = len(img[0])
    if any(len(row) != w for row in img):
        raise ValueError("non-rectangular image")
    out: list[list[float]] = [[0.0] * target for _ in range(target)]
    for y in range(target):
        sy = min(int(y * h / target), h - 1)
        src_row = img[sy]
        out_row = out[y]
        for x in range(target):
            sx = min(int(x * w / target), w - 1)
            out_row[x] = float(src_row[sx])
    return out


def _dct_1d(vec: list[float]) -> list[float]:
    n = len(vec)
    out = [0.0] * n
    for k in range(n):
        s = 0.0
        for i in range(n):
            s += vec[i] * math.cos(math.pi * (2 * i + 1) * k / (2 * n))
        out[k] = s
    return out


def _dct_2d(block: list[list[float]]) -> list[list[float]]:
    n = len(block)
    rows = [_dct_1d(row) for row in block]
    cols: list[list[float]] = [[rows[r][c] for r in range(n)] for c in range(n)]
    cols_dct = [_dct_1d(c) for c in cols]
    return [[cols_dct[c][r] for c in range(n)] for r in range(n)]


def phash64(image: Sequence[Sequence[float]]) -> str:
    """Compute a 64-bit DCT pHash; return as 16 lowercase hex chars.

    The image is normalized into [0, 255] before DCT — we accept
    [0, 1] floats too (multiplied by 255).
    """
    if not image or not image[0]:
        raise ValueError("empty image")
    # If max <= 1.0, assume normalized floats and rescale.
    max_v = max(max(row) for row in image)
    if max_v <= 1.0:
        scaled: list[list[float]] = [[v * 255.0 for v in row] for row in image]
    else:
        scaled = [list(row) for row in image]

    small = _resize_grayscale(scaled, _DCT_SIZE)
    dct = _dct_2d(small)

    # Take top-left HASH_SIZE x HASH_SIZE excluding the DC term.
    coeffs: list[float] = []
    for y in range(_HASH_SIZE):
        for x in range(_HASH_SIZE):
            coeffs.append(dct[y][x])
    # Median over coeffs[1:] (skip DC).
    rest = sorted(coeffs[1:])
    n = len(rest)
    median = rest[n // 2] if n % 2 == 1 else 0.5 * (rest[n // 2 - 1] + rest[n // 2])

    bits = ["1" if c > median else "0" for c in coeffs]
    bitstr = "".join(bits)
    val = int(bitstr, 2)
    return f"{val:016x}"


def hamming(a: str, b: str) -> int:
    """Hamming distance between two 16-hex-char (64-bit) hashes."""
    if len(a) != 16 or len(b) != 16:
        raise ValueError("phash strings must be 16 hex chars")
    return bin(int(a, 16) ^ int(b, 16)).count("1")
