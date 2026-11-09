"""Natural-language assistant: scoped Q&A with citations, cross-document comparison, search and summaries.

Retrieval technique and scores stay internal; callers only receive answers, citations and passages.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.schemas.models import Chunk, DocStatus, RetrievalMethod, RetrievedChunk
from app.schemas.workspace import Citation
from app.services.access_service import Principal, can_read_space
from app.services.audit_service import AuditLog
from app.services.conversation_service import ConversationRepository
from app.services.document_service import DocumentStore
from app.services.generation_service import GenerationService, summary_passages
from app.services.hybrid_retrieval_service import RetrievalService
from app.services.space_service import SpaceRepository
from app.utils.clock import now_iso

TOP_K = 5
COMPARE_PER_DOCUMENT = 2
COMPARE_MAX_DOCUMENTS = 6
SEARCH_POOL = 25
NO_DOCUMENTS_REPLY = "There are no documents you can access in this scope yet."


class ScopeError(LookupError):
    pass


@dataclass(frozen=True)
class QueryOutcome:
    text: str
    sufficient: bool
    citations: list[Citation]
    note: str = ""


class AssistantService:
    def __init__(
        self,
        store: DocumentStore,
        spaces: SpaceRepository,
        conversations: ConversationRepository,
        retrieval: RetrievalService,
        generation: GenerationService,
        audit: AuditLog,
    ) -> None:
        self.store, self.spaces, self.conversations = store, spaces, conversations
        self.retrieval, self.generation, self.audit = retrieval, generation, audit

    # ---- scope -------------------------------------------------------
    def resolve_scope(self, p: Principal, scope: dict) -> set[str]:
        """Document ids the principal may use for this scope (permissions re-checked on every question)."""
        readable = self.store.readable_ids(p)
        kind = scope.get("type", "all")
        if kind == "all":
            return readable
        if kind == "documents":
            return readable & set(scope.get("document_ids", []))
        space = self.spaces.get(scope.get("space_id") or "")
        if space is None or not can_read_space(p, space):
            raise ScopeError("That space was not found.")
        return readable & set(space.get("document_ids", []))

    def validate_scope(self, p: Principal, scope: dict) -> None:
        if scope.get("type") == "documents":
            wanted = set(scope.get("document_ids", []))
            if not wanted or not wanted <= self.store.readable_ids(p):
                raise ScopeError("One or more selected documents are not available to you.")
        elif scope.get("type") == "space":
            self.resolve_scope(p, scope)

    # ---- questions ---------------------------------------------------
    def answer(self, p: Principal, scope: dict, question: str, compare: bool) -> QueryOutcome:
        doc_ids = self.resolve_scope(p, scope)
        if not doc_ids:
            return QueryOutcome(NO_DOCUMENTS_REPLY, False, [])

        if compare and len(doc_ids) > 1:
            ranked_docs = sorted(doc_ids)[:COMPARE_MAX_DOCUMENTS]
            results = self._balanced_results(question, ranked_docs)
            note = (
                f"Comparing the first {COMPARE_MAX_DOCUMENTS} of {len(doc_ids)} documents."
                if len(doc_ids) > COMPARE_MAX_DOCUMENTS
                else ""
            )
        else:
            results = self.retrieval.search(
                question, RetrievalMethod.adaptive_hybrid, TOP_K, document_ids=doc_ids
            ).results
            note = ""

        generated = self.generation.answer(question, results, compare=compare and len(doc_ids) > 1)
        citations = [
            Citation(
                label=f"S{r.rank}",
                chunk_id=r.chunk.chunk_id,
                document_id=r.chunk.document_id,
                document_name=r.chunk.document_name,
                page=r.chunk.page,
                excerpt=r.chunk.text,
                cited_by_model=f"S{r.rank}" in generated.cited_labels,
            )
            for r in results
        ]
        return QueryOutcome(generated.text, generated.sufficient, citations, note)

    def _balanced_results(self, question: str, document_ids: list[str]) -> list[RetrievedChunk]:
        """Top passages from every document, so no document is crowded out by a larger one."""
        merged: list[RetrievedChunk] = []
        for doc_id in document_ids:
            res = self.retrieval.search(
                question, RetrievalMethod.adaptive_hybrid, COMPARE_PER_DOCUMENT, document_ids={doc_id}
            )
            merged.extend(res.results)
        merged.sort(key=lambda r: r.score, reverse=True)
        return [r.model_copy(update={"rank": i}) for i, r in enumerate(merged, start=1)]

    # ---- semantic search ---------------------------------------------
    def search(self, p: Principal, query: str, limit: int) -> list[dict]:
        doc_ids = self.store.readable_ids(p)
        if not doc_ids:
            return []
        res = self.retrieval.search(query, RetrievalMethod.adaptive_hybrid, SEARCH_POOL, document_ids=doc_ids)
        groups: dict[str, dict] = {}
        for r in res.results[:limit]:
            group = groups.setdefault(
                r.chunk.document_id,
                {"document_id": r.chunk.document_id, "document_name": r.chunk.document_name, "passages": []},
            )
            group["passages"].append({"chunk_id": r.chunk.chunk_id, "page": r.chunk.page, "excerpt": r.chunk.text})
        return list(groups.values())

    # ---- summaries ---------------------------------------------------
    def summarize(self, p: Principal, document_id: str, refresh: bool) -> dict:
        doc = self.store.get(document_id)
        if doc is None or document_id not in self.store.readable_ids(p):
            raise ScopeError("Document not found.")
        if doc.status != DocStatus.processed:
            raise ScopeError("This document is still being processed.")
        if doc.summary and not refresh:
            return {"summary": doc.summary, "generated_at": doc.summary_at, "citations": []}

        passages: list[Chunk] = summary_passages(self.store.chunks_for_document(document_id))
        generated = self.generation.summarize(passages)
        when = now_iso()
        self.store.update(document_id, summary=generated.text, summary_at=when)
        self.audit.record("document.summarize", p, "document", document_id)
        citations = [
            Citation(
                label=f"S{i}",
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_name=c.document_name,
                page=c.page,
                excerpt=c.text,
                cited_by_model=f"S{i}" in generated.cited_labels,
            )
            for i, c in enumerate(passages, start=1)
        ]
        return {"summary": generated.text, "generated_at": when, "citations": [c.model_dump() for c in citations]}
