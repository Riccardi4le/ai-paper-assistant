"""Unit tests for chunk_text. No heavy deps required."""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.rag_utils import chunk_text, CHUNK_SIZE, CHUNK_OVERLAP


def test_empty_returns_empty_list():
    assert chunk_text("") == []
    assert chunk_text("   \n\t  ") == []
    assert chunk_text(None) == []  # type: ignore[arg-type]


def test_shorter_than_size_returns_single_chunk():
    text = "Attention is all you need."
    out = chunk_text(text, size=100, overlap=10)
    assert out == [text]


def test_exactly_size_returns_single_chunk():
    text = "x" * 100
    out = chunk_text(text, size=100, overlap=10)
    assert out == [text]
    assert len(out) == 1


def test_long_text_produces_overlapping_chunks():
    text = "abcdefghij" * 300  # 3000 chars
    out = chunk_text(text, size=900, overlap=150)
    # step = 750; ceil((3000 - 900) / 750) + 1 = 4
    assert len(out) == 4
    assert [len(c) for c in out] == [900, 900, 900, 750]


def test_overlap_is_respected():
    text = "".join(f"{i:04d}" for i in range(500))  # 2000 chars, unique 4-char markers
    out = chunk_text(text, size=200, overlap=50)
    # Every consecutive pair should share the last 50 chars of one == first 50 of the next
    for a, b in zip(out, out[1:]):
        assert a[-50:] == b[:50], "overlap boundary broken"


def test_step_never_zero_when_overlap_equals_size():
    # Pathological but must not infinite-loop; size==overlap → step clamped to 1
    out = chunk_text("abcd" * 50, size=10, overlap=10)
    assert isinstance(out, list) and len(out) > 0


def test_default_constants_sane():
    assert CHUNK_SIZE > 0
    assert 0 <= CHUNK_OVERLAP < CHUNK_SIZE


def test_chunks_reconstruct_original_when_no_boundary_whitespace():
    """Stitching chunks by removing the overlap should recover the source."""
    # No spaces → per-chunk .strip() is a no-op, reconstruction is clean
    text = "ABCDEFGHIJ" * 300  # 3000 chars, no whitespace
    size, overlap = 500, 100
    out = chunk_text(text, size=size, overlap=overlap)
    reconstructed = out[0]
    for c in out[1:]:
        reconstructed += c[overlap:]
    assert reconstructed == text


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
