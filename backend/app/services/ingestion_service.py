"""Extraction (PDF/DOCX/TXT) and the ingestion pipeline."""
from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.schemas.models import Chunk, DocStatus
from app.services.bm25_service import BM25Service
from app.services.chunking_service import PageText, chunk_pages
from app.services.document_service import DocumentStore, now_iso
from app.services.vector_service import VectorService


class ExtractionError(RuntimeError):
    pass


def extract_pages(path: Path) -> list[PageText]:
    """Extract text, preserving page numbers for PDFs (DOCX/TXT are treated as page 1)."""
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            import fitz  # PyMuPDF

            with fitz.open(path) as pdf:
                pages = [PageText(i + 1, page.get_text("text")) for i, page in enumerate(pdf)]
        elif ext == ".docx":
            import docx

            d = docx.Document(str(path))
            parts = [p.text for p in d.paragraphs]
            for table in d.tables:
                for row in table.rows:
                    parts.append(" | ".join(cell.text.strip() for cell in row.cells))
            pages = [PageText(1, "\n".join(parts))]
        elif ext == ".txt":
            pages = [PageText(1, path.read_text(encoding="utf-8", errors="replace"))]
        else:
            raise ExtractionError(f"Unsupported file type: {ext}")
    except ExtractionError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"Could not read {path.name}: {exc}") from exc
    if not any(p.text.strip() for p in pages):
        raise ExtractionError(
            "No extractable text found (scanned/image-only PDFs need OCR, which is not part of this prototype)."
        )
    return pages


class IngestionService:
    def __init__(self, store: DocumentStore, vectors: VectorService, bm25: BM25Service) -> None:
        self.store, self.vectors, self.bm25 = store, vectors, bm25

    def process(self, document_id: str) -> None:
        """Run the full pipeline for one stored document. Never raises; failures are recorded."""
        s = get_settings()
        info = self.store.get(document_id)
        if info is None:
            return
        self.store.update(document_id, status=DocStatus.processing, error=None)
        try:
            path = self.store.stored_file(document_id)
            if path is None:
                raise ExtractionError("Stored file not found on disk.")
            pages = extract_pages(path)
            raw = chunk_pages(pages, s.chunk_size, s.chunk_overlap)
            chunks = [
                Chunk(
                    chunk_id=f"{document_id}_c{i:04d}",
                    document_id=document_id,
                    document_name=info.filename,
                    page=rc.page,
                    text=rc.text,
                    source=f"{info.filename}, p.{rc.page}",
                )
                for i, rc in enumerate(raw)
            ]
            self.vectors.delete_document(document_id)  # idempotent re-processing
            self.vectors.add_chunks(chunks)
            self.store.set_chunks(document_id, chunks)
            self.store.update(
                document_id, status=DocStatus.processed, pages=len(pages), chunks=len(chunks), processed_at=now_iso()
            )
        except Exception as exc:  # noqa: BLE001
            self.store.update(document_id, status=DocStatus.failed, error=str(exc))
