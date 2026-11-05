"""Pydantic request/response schemas."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RetrievalMethod(str, Enum):
    bm25 = "bm25"
    dense = "dense"
    fixed_hybrid = "fixed_hybrid"
    adaptive_hybrid = "adaptive_hybrid"


class DocStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    processed = "processed"
    failed = "failed"


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    size_bytes: int
    status: DocStatus
    pages: int = 0
    chunks: int = 0
    error: Optional[str] = None
    uploaded_at: str
    processed_at: Optional[str] = None
    synthetic: bool = False


class DocumentStatus(BaseModel):
    document_id: str
    status: DocStatus
    chunks: int = 0
    error: Optional[str] = None


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page: int
    text: str
    source: str  # human readable, e.g. "policy.pdf, p.3"


class AdaptiveConfig(BaseModel):
    """Optional per-request overrides of base alpha (BM25 weight) for each query class."""

    identifier: Optional[float] = Field(None, ge=0, le=1)
    exact_keyword: Optional[float] = Field(None, ge=0, le=1)
    mixed: Optional[float] = Field(None, ge=0, le=1)
    semantic: Optional[float] = Field(None, ge=0, le=1)
    conceptual: Optional[float] = Field(None, ge=0, le=1)


class RetrievedChunk(BaseModel):
    chunk: Chunk
    score: float  # final score of the selected method
    bm25_score: Optional[float] = None  # normalized
    dense_score: Optional[float] = None  # normalized
    rank: int


class AdaptiveInfo(BaseModel):
    query_class: str
    bm25_weight: float
    dense_weight: float
    reasons: list[str]
    features: dict


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000)
    method: RetrievalMethod = RetrievalMethod.adaptive_hybrid
    top_k: int = Field(5, ge=1, le=20)
    fixed_alpha: Optional[float] = Field(None, ge=0, le=1)
    adaptive_config: Optional[AdaptiveConfig] = None


class SearchResponse(BaseModel):
    method: RetrievalMethod
    query: str
    results: list[RetrievedChunk]
    adaptive: Optional[AdaptiveInfo] = None
    fixed_alpha: Optional[float] = None
    latency_ms: float


class Citation(BaseModel):
    label: str  # "S1"
    chunk_id: str
    document_id: str
    document_name: str
    page: int
    excerpt: str
    cited_by_model: bool


class ChatRequest(SearchRequest):
    pass


class ChatResponse(BaseModel):
    answer: str
    sufficient_evidence: bool
    method: RetrievalMethod
    retrieved: list[RetrievedChunk]
    citations: list[Citation]
    adaptive: Optional[AdaptiveInfo] = None
    model: str
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float


class EvaluationRequest(BaseModel):
    k: int = Field(5, ge=1, le=20)
    fixed_alpha: Optional[float] = Field(None, ge=0, le=1)
