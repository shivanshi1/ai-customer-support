# AI Customer Support Automation

For complete Windows setup, run, dashboard, indexing, and testing instructions,
see [HOWTO.md](HOWTO.md).

The project includes both the original React dashboard and an optional
Streamlit client. Start the latter with `poetry run streamlit run
streamlit_app.py` after configuring `.streamlit/secrets.toml`.

An AI-powered customer-support backend built with FastAPI and Groq. It stores
customer conversations, maintains message history, and exposes a foundation for
safe support automation, knowledge retrieval, and human escalation.

## Current capabilities

- Groq-backed support responses through `POST /api/v1/chat`.
- Persistent SQLite-backed customers, conversations, messages, orders, tickets,
  actions, and audit-event data.
- Conversation continuation via an optional `conversation_id`.
- Pydantic-validated AI intent, priority, sentiment, confidence, and suggested
  action for every response.
- Deterministic escalation rules for security/fraud, legal, payment-dispute,
  safety, threat, urgent, model-requested, and low-confidence cases.
- Customer-scoped order-status lookup, idempotent human-review tickets, and
  return requests that remain pending approval until a human acts.
- A Markdown/text/PDF knowledge base with persisted chunks, relevance-ranked
  retrieval, grounded policy answers, and source citations in chat responses.
- Protected knowledge reindex endpoint (`POST /api/v1/knowledge/reindex`).
- React operations dashboard with customer chat, conversation history, agent
  decision/source cards, human review queue, and live support metrics.
- Conversation-history endpoints for support review.
- Shared application lifecycle for the database and LLM client.
- Consistent provider-unavailable responses, request IDs, CORS, and logs.
- Alembic migration baseline and seeded demo customer/order data.

## Tech stack

- Python 3.12, FastAPI, Uvicorn
- Groq API
- SQLAlchemy async ORM, SQLite/aiosqlite
- Alembic migrations
- Pytest and Ruff

## Local setup

1. Install dependencies with `poetry install`.
2. Copy `.env.example` to `.env` and provide `GROQ_API_KEY`.
   Set `KNOWLEDGE_ADMIN_TOKEN` to a private token before using the reindex
   endpoint. Sources live under `knowledge_base/` by default.
3. Start the API:

   ```bash
   poetry run uvicorn app.main:app --reload
   ```

4. Open the generated API documentation at `http://127.0.0.1:8000/docs`.

Start the Phase 6 dashboard in a second terminal:

```bash
cd dashboard
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). It connects to the API at
`http://127.0.0.1:8000/api/v1`; set `VITE_API_URL` when the backend runs at a
different address. The seeded demo customer is `C001`.

For a fresh database managed through migrations, run:

```bash
poetry run alembic upgrade head
```

The application also creates the local development schema at startup and seeds
customer `C001` with order `ORD-1001` when that customer is absent.
Apply `poetry run alembic upgrade head` to create the knowledge chunk table in
databases managed through migrations. After editing knowledge documents, rebuild
the index with:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/knowledge/reindex \
  -H "Authorization: Bearer YOUR_KNOWLEDGE_ADMIN_TOKEN"
```

The retriever uses deterministic feature-hashed 384-dimension embeddings and
cosine similarity without an external embedding API. PostgreSQL stores them in
pgvector; SQLite stores the same values as JSON for local development. PDF
ingestion uses `pypdf` text extraction; scanned image-only PDFs need OCR before
ingestion.

## Example chat request

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"C001","message":"How do I reset my password?"}'
```

Pass the returned `conversation_id` in the next request to retain history.

## API endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Service health check |
| `POST` | `/api/v1/chat` | Create or continue a support conversation |
| `GET` | `/api/v1/conversations?customer_id=C001` | List a customer's conversations |
| `GET` | `/api/v1/conversations/{id}?customer_id=C001` | Get a conversation transcript |
| `POST` | `/api/v1/knowledge/reindex` | Reindex local knowledge files (Bearer token required) |
| `GET` | `/api/v1/dashboard/tickets` | List the human review queue |
| `PATCH` | `/api/v1/dashboard/tickets/{id}` | Resolve or update a ticket |
| `GET` | `/api/v1/dashboard/metrics` | Conversation, ticket, automation, and intent metrics |

## Quality checks

```bash
poetry run ruff check .
poetry run pytest -q
```

## Dashboard demo flow

1. Ask “How do I reset my password?” in the chat panel and inspect the grounded
   answer and account-guide source.
2. Ask about `ORD-1001` to see customer-scoped order context.
3. Ask for a refund or return and inspect the pending human-review state.
4. Send an urgent complaint or fraud concern, then resolve its ticket from the
   review queue.
