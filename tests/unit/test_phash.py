"""Sanity tests for the v0 pHash dedup primitive (components/phash.py)."""

from __future__ import annotations

import math
import random

import pytest

from components.phash import hamming, phash64


def _solid(val: float, size: int = 64) -> list[list[float]]:
    return [[val] * size for _ in range(size)]


def _gradient(size: int = 64) -> list[list[float]]:
    return [[(x + y) / (2 * (size - 1)) for x in range(size)] for y in range(size)]


def _noise(size: int = 64, seed: int = 0) -> list[list[float]]:
    rng = random.Random(seed)
    return [[rng.random() for _ in range(size)] for _ in range(size)]


def test_phash_deterministic():
    img = _gradient(48)
    assert phash64(img) == phash64(img)


def test_phash_format():
    h = phash64(_gradient(48))
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


def test_phash_distinguishes_different_content():
    h1 = phash64(_gradient(48))
    h2 = phash64(_noise(48, seed=42))
    assert hamming(h1, h2) >= 8  # comfortably different


def test_phash_invariant_under_resize():
    """Same gradient at different resolutions hashes much closer than to noise.

    The v0 pHash uses pure-Python nearest-neighbour resize, so we don't expect
    bit-exact equality across resolutions; we only require that the same
    content-at-different-resolution distance is much smaller than the
    content-vs-noise distance.
    """
    big = _gradient(96)
    small = _gradient(32)
    h_big = phash64(big)
    h_small = phash64(small)
    h_noise = phash64(_noise(48, seed=7))
    d_same = hamming(h_big, h_small)
    d_diff = hamming(h_big, h_noise)
    assert d_same < d_diff, (d_same, d_diff)
    assert d_same <= 24  # comfortable upper bound for nearest-neighbour resize


def test_hamming_self_zero():
    h = phash64(_gradient(48))
    assert hamming(h, h) == 0


def test_hamming_validates_input():
    with pytest.raises(ValueError):
        hamming("00", "00")  # too short


def test_phash_rejects_empty_image():
    with pytest.raises(ValueError):
        phash64([])


def test_phash_handles_uint8_range():
    """Both [0,1] and [0,255] inputs should be handled equivalently."""
    img_unit = _gradient(48)
    img_255 = [[v * 255.0 for v in row] for row in img_unit]
    h_unit = phash64(img_unit)
    h_255 = phash64(img_255)
    # Floating-point makes exact equality fragile; require very close.
    assert hamming(h_unit, h_255) <= 2, (h_unit, h_255)


def test_hamming_is_symmetric_and_bounded():
    a = phash64(_gradient(48))
    b = phash64(_noise(48, seed=1))
    d = hamming(a, b)
    assert d == hamming(b, a)
    assert 0 <= d <= 64
    # sanity: should not be exactly equal to math.inf or NaN
    assert not math.isinf(d) and not math.isnan(d)
