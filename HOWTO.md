# How to run AI Customer Support

These instructions are for running the backend and Phase 6 dashboard locally
on Windows with PowerShell.

## Prerequisites

- Python 3.12
- Poetry
- Node.js and npm
- A Groq API key for live chat responses

## 1. Install backend dependencies

From the project root:

```powershell
poetry install
```

## 2. Create the environment file

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and set your Groq key:

```env
GROQ_API_KEY=your_real_groq_api_key
```

The knowledge management token is also configured in this same `.env` file:

```env
KNOWLEDGE_ADMIN_TOKEN=change-this-local-token
```

`KNOWLEDGE_ADMIN_TOKEN` is not provided by Groq and is not fetched from another
service. It is a private token that you create for this local application. You
can replace `change-this-local-token` with any long, private value. You will use
the exact same value in the reindex command in Step 5.

The complete example is available in [.env.example](.env.example). The actual
secret-bearing file is `.env`, which should remain local and should not be
committed.

## 3. Create the database

The default local database is SQLite:

```powershell
poetry run alembic upgrade head
```

The application seeds demo customer `C001` and order `ORD-1001` when it starts.

## 4. Start the API

From the project root, start the backend:

```powershell
poetry run uvicorn app.main:app --reload
```

The API is available at:

```text
http://127.0.0.1:8000
```

Open the interactive API documentation at:

```text
http://127.0.0.1:8000/docs
```

Check that the service is running:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Leave this terminal running.

## 5. Index the knowledge base

Open a second PowerShell window in the project root. Use the value assigned to
`KNOWLEDGE_ADMIN_TOKEN` in `.env`:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/knowledge/reindex `
  -Headers @{ Authorization = "Bearer change-this-local-token" }
```

Replace `change-this-local-token` with your actual token if you changed it in
`.env`.

The command indexes documents from the `knowledge_base` folder. Re-run it after
adding or editing Markdown, text, or PDF knowledge documents.

## 6. Start the React dashboard

In the second terminal:

```powershell
cd dashboard
npm install
npm run dev
```

Open the URL printed by Vite, normally:

```text
http://localhost:5173
```

The dashboard connects to the API at
`http://127.0.0.1:8000/api/v1` by default. To use another API address, set
`VITE_API_URL` before starting Vite:

```powershell
$env:VITE_API_URL = "http://127.0.0.1:9000/api/v1"
npm run dev
```

## 7. Start the Streamlit application

Streamlit is an alternative dashboard. It uses the same FastAPI backend and can
run alongside the React dashboard. Install the Python dependencies from the
project root first:

```powershell
poetry install
```

Create Streamlit's local secrets file:

```powershell
New-Item -ItemType Directory -Force .streamlit
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

The token is configured in `.streamlit\secrets.toml` under
`KNOWLEDGE_ADMIN_TOKEN`. This is the same kind of private local token as the
`KNOWLEDGE_ADMIN_TOKEN` in the root `.env`; it should not be committed.

Start Streamlit from the project root:

```powershell
poetry run streamlit run streamlit_app.py
```

Open:

```text
http://localhost:8501
```

The Streamlit app provides chat, source citations, conversation history, the
human review queue, ticket assignment and notes, resolution controls, and
analytics. The React dashboard and Streamlit dashboard are interchangeable
frontends for the same API.

## 8. Test a chat request directly

The seeded demo customer is `C001`:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/chat `
  -ContentType "application/json" `
  -Body '{"customer_id":"C001","message":"How do I reset my password?"}'
```

Try these dashboard scenarios:

1. Ask how to reset a password and inspect the account-guide source.
2. Ask about order `ORD-1001` and inspect the order context.
3. Request a return or refund and inspect the human-review state.
4. Send an urgent complaint or fraud concern and resolve its ticket from the
   review queue.

## 9. Run automated checks

From the project root:

```powershell
poetry run pytest -q
poetry run ruff check .
```

## Troubleshooting

### Chat returns a provider error

Confirm that `.env` contains a valid `GROQ_API_KEY`, then restart Uvicorn.

### Reindex returns unauthorized

The bearer token must exactly match `KNOWLEDGE_ADMIN_TOKEN` in the root `.env`
file. Restart the API after changing `.env`.

### Dashboard cannot reach the API

Confirm that Uvicorn is running on port `8000`. If it uses another address, set
`VITE_API_URL` before running `npm run dev`.

### npm install cannot download packages

The dashboard dependencies must be downloaded from the npm registry. Retry when
network access is available, then run `npm run dev` again.
