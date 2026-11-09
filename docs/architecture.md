# Architecture

## Components

- **Browser app (React, Vite)**: sign-in screen, then Ask, Search, Documents, Spaces, and Administration pages. It stores only the sign-in token and calls the backend over HTTP with it.
- **Backend (FastAPI)**: all business rules. Each request is authenticated from the token, checked for revocation, and then authorized by role and document or space permissions.
- **MongoDB**: `users`, `documents`, `chunks`, `spaces`, `conversations`, `messages`, `audit_logs`, `revoked_tokens` (expires automatically).
- **ChromaDB**: vector index for passages, filtered by the document IDs the user may read.
- **Ollama**: local model that writes answers and summaries from retrieved passages only.
- **Filesystem**: original uploaded files under `data/documents`.

## Request path for a question

1. The token is verified and the user is loaded; the conversation must belong to that user.
2. The conversation scope (all documents, a space, or specific documents) is re-checked against current permissions.
3. The readable document IDs are computed, and keyword and vector search run only over those documents.
4. An evidence check rejects weak matches before the model is called. Answers that cannot be supported say so.
5. Citations are kept only for passages actually supplied to the model. The question, answer, and citations are stored in the conversation, and the audit log records the question's length.

## Access model

- Roles: administrator, editor, viewer. The first account created is an administrator.
- Documents: private, shared with named users, or organization-wide. Owners and administrators can change access.
- Spaces: readable by the owner, members, and administrators; editable by the owner and administrators.
- Every rule lives in one module (`services/access_service.py`), and listings use the same rule as a database filter.

## Document processing

Uploads are stored, extracted page by page, split into overlapping chunks, indexed for keyword and vector search, and analysed for type, title, identifiers, dates, keywords, and key points. Processing status is shown on each document until it completes.

## Internal evaluation

Retrieval and evaluation metrics are internal. Administrators can run the evaluation from the admin API; end users see only answers and sources.
