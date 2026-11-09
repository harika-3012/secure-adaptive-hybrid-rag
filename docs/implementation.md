# Implementation status

## Built

| Area | Where | Status |
| --- | --- | --- |
| Sign-in, registration, sign-out, token revocation | `api/routes/auth.py`, `core/security.py` | Built |
| Roles and document/space permissions | `services/access_service.py` | Built, unit tested |
| Document upload, visibility, sharing, delete, summaries | `api/routes/documents.py` | Built |
| Document intelligence (type, title, identifiers, dates, keywords, key points) | `services/document_intelligence.py` | Built, unit tested |
| Question answering with citations, compare mode | `services/assistant_service.py`, `services/generation_service.py` | Built |
| Knowledge Spaces | `api/routes/spaces.py`, `services/space_service.py` | Built |
| Conversation history | `api/routes/conversations.py`, `services/conversation_service.py` | Built |
| Semantic search | `api/routes/workspace.py` | Built |
| Audit trail and administration | `api/routes/admin.py`, `services/audit_service.py` | Built |
| Frontend pages | `frontend/src/pages` | Built; production build passes |

- API tests (`backend/tests/test_api.py`) use an in-memory database and cover sign-in, sign-out, document visibility, uploads by role, spaces, conversation scope and privacy, and administrator guards. They have been written but not run in this environment.
- The last-administrator check can only be reached by an administrator demoting or disabling themselves when they are the sole administrator; the test covers the self-demotion path.
- Assistant answer quality (retrieval, citations, compare mode) is not covered by automated tests; it needs the local model.
- The evaluation service is updated to the database-backed store but has not been exercised end to end.
