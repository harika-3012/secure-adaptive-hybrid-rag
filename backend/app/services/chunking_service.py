"""Recursive text chunking with configurable size/overlap. Pure Python (no heavy deps)."""
from __future__ import annotations

import re
from dataclasses import dataclass

SEPARATORS = ["\n\n", "\n", ". ", "; ", ", ", " "]


@dataclass
class PageText:
    page: int  # 1-based; TXT/DOCX use 1
    text: str


@dataclass
class RawChunk:
    page: int
    text: str


def clean_text(text: str) -> str:
    """Remove control chars, de-hyphenate line breaks and collapse whitespace."""
    text = text.replace("\x00", " ")
    text = re.sub(r"-\n(?=[a-z])", "", text)  # join hyphenated line-wraps
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_recursive(text: str, size: int, seps: list[str]) -> list[str]:
    if len(text) <= size:
        return [text]
    if not seps:
        return [text[i : i + size] for i in range(0, len(text), size)]
    sep, rest = seps[0], seps[1:]
    parts = text.split(sep)
    if len(parts) == 1:
        return _split_recursive(text, size, rest)
    out: list[str] = []
    buf = ""
    for i, part in enumerate(parts):
        piece = part + (sep if i < len(parts) - 1 else "")
        if len(piece) > size:
            if buf:
                out.append(buf)
                buf = ""
            out.extend(_split_recursive(piece, size, rest))
        elif len(buf) + len(piece) <= size:
            buf += piece
        else:
            out.append(buf)
            buf = piece
    if buf:
        out.append(buf)
    return out


def chunk_pages(pages: list[PageText], chunk_size: int = 800, overlap: int = 120) -> list[RawChunk]:
    """Chunk each page separately so every chunk keeps an exact page number.

    Overlap is applied inside a page by prefixing each chunk with the tail of the previous one.
    """
    if overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    chunks: list[RawChunk] = []
    for page in pages:
        text = clean_text(page.text)
        if not text:
            continue
        pieces = [p.strip() for p in _split_recursive(text, chunk_size - overlap, SEPARATORS) if p.strip()]
        prev_tail = ""
        for piece in pieces:
            body = (prev_tail + " " + piece).strip() if prev_tail else piece
            chunks.append(RawChunk(page=page.page, text=body))
            prev_tail = piece[-overlap:] if overlap else ""
    return chunks
