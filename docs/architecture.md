# Architecture

Diagrams are written in Mermaid (render in GitHub, VS Code with a Mermaid extension, or https://mermaid.live) so they can be exported as images for the Review 2 PPT.

## 1. System architecture

```mermaid
flowchart TD
    U[User] --> FE[React + Vite frontend]
    FE -->|REST/JSON| API[FastAPI backend]
    API --> DOC[Document API<br/>upload / list / status / delete]
    API --> CHAT[Chat API]
    API --> RET[Retrieval API]
    API --> EVAL[Evaluation API]
    DOC --> ING[Ingestion service]
    ING --> EXT[PDF / DOCX / TXT extraction]
    EXT --> CHK[Cleaning + recursive chunking]
    CHK --> EMB[Local Sentence-Transformer]
    EMB --> CH[(ChromaDB<br/>persistent)]
    CHK --> REG[(documents.json + chunks.jsonl)]
    RET --> RS[Retrieval service]
    RS --> BM[BM25 index<br/>rank-bm25]
    RS --> CH
    RS --> AD[Adaptive query analyser<br/>features -> class -> alpha]
    CHAT --> RS
    CHAT --> GEN[Generation service<br/>evidence gate + prompt + citations]
    GEN --> OL[Ollama local LLM]
    EVAL --> RS
    EVAL --> MET[Metrics + charts<br/>CSV / JSON / PNG]
    FILES[(data/documents)] --- DOC
```

## 2. DFD Level 0

```mermaid
flowchart LR
    User((User)) -- "documents, questions, method choice" --> S[Secure Adaptive Hybrid RAG System]
    S -- "answers, citations, retrieval details, evaluation results" --> User
    S <-- "prompt / completion (localhost)" --> LLM[(Local LLM - Ollama)]
```

## 3. DFD Level 1

```mermaid
flowchart TD
    User((User))
    P1[1.0 Upload and validate]
    P2[2.0 Extract, clean, chunk]
    P3[3.0 Embed and index]
    P4[4.0 Analyse query and retrieve]
    P5[5.0 Generate grounded answer]
    P6[6.0 Evaluate retrieval]
    D1[(D1 Uploaded files)]
    D2[(D2 Registry + chunks)]
    D3[(D3 ChromaDB vectors)]
    D4[(D4 Evaluation results)]
    User -->|file| P1 --> D1
    D1 --> P2 --> D2
    P2 --> P3 --> D3
    User -->|question, method, top-k| P4
    D2 --> P4
    D3 --> P4
    P4 -->|ranked chunks + weights| P5
    P5 -->|answer + citations| User
    P4 --> P6
    P6 --> D4 -->|tables, charts| User
```

## 4. UML use-case diagram

```mermaid
flowchart LR
    A((User))
    A --- UC1[Upload document]
    A --- UC2[View status / list documents]
    A --- UC3[Delete document]
    A --- UC4[Ask question]
    A --- UC5[Choose retrieval method]
    A --- UC6[Inspect sources and weights]
    A --- UC7[Run evaluation]
    UC4 -.include.-> UC8[Retrieve evidence]
    UC4 -.include.-> UC9[Generate answer with local LLM]
    UC5 -.extend.-> UC4
```

## 5. Sequence: query processing

```mermaid
sequenceDiagram
    actor U as User
    participant F as React UI
    participant A as FastAPI /api/chat/query
    participant R as RetrievalService
    participant Q as Adaptive analyser
    participant B as BM25
    participant V as ChromaDB
    participant G as GenerationService
    participant L as Ollama
    U->>F: question + method + top-k
    F->>A: POST JSON
    A->>R: search(query, method, k)
    opt method = adaptive_hybrid
        R->>Q: decide(query)
        Q-->>R: class, alpha(q), reasons
    end
    R->>B: top-N lexical candidates
    R->>V: top-N dense candidates
    R->>R: min-max normalise, fuse, dedupe, rank
    R-->>A: ranked chunks
    A->>G: answer(query, chunks)
    G->>G: evidence gate (cosine / lexical coverage)
    alt evidence insufficient
        G-->>A: fixed "insufficient evidence" reply (LLM not called)
    else sufficient
        G->>L: context + question
        L-->>G: answer with [S#] labels
        G->>G: drop labels that were not retrieved
    end
    A-->>F: answer, citations, weights, latencies
    F-->>U: answer + expandable sources
```

## 6. Module map

| Module | File |
|---|---|
| Config | `backend/app/core/config.py` |
| Wiring (future auth / RBAC / audit hook point) | `backend/app/core/container.py` |
| Upload API | `backend/app/api/routes/documents.py` |
| Extraction + ingestion | `services/ingestion_service.py` |
| Chunking | `services/chunking_service.py` |
| Embeddings / vector store | `services/embedding_service.py`, `services/vector_service.py` |
| BM25 | `services/bm25_service.py` |
| Fixed + adaptive orchestration | `services/hybrid_retrieval_service.py` |
| Query analysis (core research) | `services/adaptive_retrieval_service.py` |
| Fusion / normalisation | `utils/scoring.py` |
| Generation | `services/generation_service.py` |
| Evaluation | `services/evaluation_service.py`, `experiments/` |

Extension points: every route obtains services from `get_container()`, so authentication, RBAC and permission-aware retrieval can be added as a dependency on the routes and a filter inside `RetrievalService.search` (chunk metadata already carries `document_id`).
