# Methodology

## Ingestion
Extract text (PyMuPDF per page / python-docx paragraphs + tables / UTF-8 text), clean (de-hyphenate line wraps, collapse whitespace), chunk each page separately with a recursive splitter (paragraph → line → sentence → clause → word; default 800 characters, 120 overlap, both configurable) so every chunk has an exact page number. DOCX and TXT have no reliable pagination and are reported as page 1.

## Retrieval methods
All methods draw a candidate pool (default 30) and return top-k.

* **BM25** – Okapi BM25 over lowercase tokens. Compound identifiers are indexed both whole and split (`POL-SEC-007` → `pol`, `sec`, `007`, `pol-sec-007`) so identifier queries match exactly.
* **Dense** – local Sentence-Transformer embeddings (default `all-MiniLM-L6-v2`), L2-normalised, cosine search in ChromaDB.
* **Fixed hybrid** – `H(d,q) = α·BM25ₙ(d,q) + (1−α)·Denseₙ(d,q)`, default α = 0.5.
* **Adaptive hybrid** – same fusion with `α(q)` computed per query (below).

**Normalisation.** Scores are min-max normalised over each retriever's candidate list. A chunk absent from one list receives 0 from it; candidates are merged by chunk ID, so duplicates cannot occur. Known limitation: min-max over a small candidate set always maps the best candidate to 1.0, so normalised scores carry no absolute-relevance information. For that reason the evidence gate uses *raw* cosine similarity, not the fused score.

## Adaptive weighting (`adaptive_retrieval_service.py`)
1. **Features**: token count, identifiers (regex for `POL-SEC-007`, `Section 4.2.1`, `ISO 27001`, …), quoted phrases, acronyms, conceptual cue words (why/how/explain/ensure…), paraphrase hints, question type, content-word ratio.
2. **Classification** (first matching rule wins): identifier+long conceptual → *mixed*; identifier → *identifier*; quoted phrase → *exact keyword*; short keyword-style → *exact keyword*; acronym-centred short query → *exact keyword*; acronym+conceptual → *mixed*; strong explanatory intent → *conceptual*; long/loosely worded → *semantic*; else *mixed*.
3. **Base α (BM25 weight)** per class, all configurable (`.env` or per request): identifier 0.85, exact 0.75, mixed 0.50, semantic 0.30, conceptual 0.20.
4. **Bounded adjustments** (±0.05 each): long query → dense; very short → BM25; wh-question in a non-lexical class → dense; several identifiers or a quoted phrase → BM25.
5. **Clamp** to [0.05, 0.95]; dense weight = 1 − α.
Every decision returns its reasons, shown in the UI and API.

**Honest status.** This is a hand-designed rule system. The base weights are initial priors, not tuned values. Whether it beats fixed hybrid is an empirical question answered only by the evaluation below; no performance claim is made here.

## Answer generation
Top-k chunks are labelled `[S1]…[Sk]` and placed in the prompt. The system prompt requires: use only the context, never invent, cite labels, and reply with the fixed insufficient-evidence sentence otherwise. Before calling the LLM an **evidence gate** requires best raw cosine ≥ `MIN_EVIDENCE_SCORE` (0.25) *or* ≥ 60 % of the query's content words in some retrieved chunk; otherwise the fixed sentence is returned without calling the model. After generation, any `[S#]` label that does not correspond to a retrieved chunk is discarded, and each source is flagged `cited_by_model` or context-only. The gate threshold is an untuned heuristic.

## Evaluation protocol
* Corpus: 4 synthetic documents (24 sections) in `data/evaluation/corpus/`, labelled SYNTHETIC. Ingested into an isolated temporary index each run.
* Questions: 24 in `data/evaluation/eval_dataset.json` – 4 each of exact keyword, identifier, conceptual, paraphrased, mixed, insufficient-evidence.
* Ground truth: each question names a relevant document and an `evidence_phrase`; relevant chunk IDs are resolved at run time as all chunks of that document containing the phrase (so results stay valid when chunk settings change; overlapping chunks may both count).
* Metrics: Precision@K, Recall@K, MRR, NDCG@K (binary relevance) over the 20 answerable questions; mean/median/p95 retrieval latency over all 24 after a warm-up; for the 4 unanswerable questions, the share the evidence gate correctly rejects.
* Limitations: tiny, synthetic, written by the system author with knowledge of the retrievers; paraphrase questions are hand-written. Results are PRELIMINARY and cannot support a significance claim. Next step: a public-document corpus (e.g. RBI circulars) with independently written questions.

## Related work (verified bibliographic details)
1. Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., Kiela, D. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *Advances in Neural Information Processing Systems 33 (NeurIPS 2020)*. https://arxiv.org/abs/2005.11401
2. Robertson, S., Zaragoza, H. (2009). The Probabilistic Relevance Framework: BM25 and Beyond. *Foundations and Trends in Information Retrieval*, 3(4), 333–389. DOI 10.1561/1500000019.
3. Karpukhin, V., Oguz, B., Min, S., Lewis, P., Wu, L., Edunov, S., Chen, D., Yih, W. (2020). Dense Passage Retrieval for Open-Domain Question Answering. *Proc. EMNLP 2020*, pp. 6769–6781.
4. Reimers, N., Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. arXiv:1908.10084 (preprint; confirm the conference citation before submission).
5. Hsu, H.-L., Tzeng, J. (2025). DAT: Dynamic Alpha Tuning for Hybrid Retrieval in Retrieval-Augmented Generation. arXiv:2503.23013 (unpublished preprint, under review at time of checking). Closest related work: it also sets a per-query α over min-max-normalised BM25/dense scores, but uses an LLM to score each retriever's top result, whereas this prototype uses rule-based query features with no extra LLM call.

Items 1–5 were checked against their source pages (arXiv / NeurIPS / ACL Anthology / publisher). Complete the literature survey with further sources you have read yourself.
