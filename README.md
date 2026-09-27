# AI Customer Support Automation

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
3. Start the API:

   ```bash
   poetry run uvicorn app.main:app --reload
   ```

4. Open the generated API documentation at `http://127.0.0.1:8000/docs`.

For a fresh database managed through migrations, run:

```bash
poetry run alembic upgrade head
```

The application also creates the local development schema at startup and seeds
customer `C001` with order `ORD-1001` when that customer is absent.

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

## Quality checks

```bash
poetry run ruff check .
poetry run pytest -q
```

## Next milestones

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the full roadmap. The
next implementation phase adds structured intent classification, escalation
rules, and controlled customer-support tools.
