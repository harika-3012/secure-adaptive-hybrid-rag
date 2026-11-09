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

## Not yet done

- API-level tests for sign-in, document permissions over HTTP, scoped answers, and the last-administrator guard. These need an in-memory MongoDB or a test database and have not been written.
- Tests have not been run in this environment. Run `pytest` in the backend after setup.
- The evaluation service is updated to the database-backed store but has not been exercised end to end.
