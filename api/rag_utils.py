"""Pure helpers for the RAG pipeline.

Kept free of heavy ML dependencies (torch, faiss, sentence-transformers) so
tests can import from here without the full runtime.
"""

from __future__ import annotations

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character-based chunks.

    - Empty / whitespace input → [].
    - Text shorter than `size` → single chunk.
    - Otherwise: sliding window of `size` chars stepping by `size - overlap`.
    """
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    step = max(1, size - overlap)
    chunks: list[str] = []
    for start in range(0, len(text), step):
        piece = text[start:start + size].strip()
        if piece:
            chunks.append(piece)
        if start + size >= len(text):
            break
    return chunks
