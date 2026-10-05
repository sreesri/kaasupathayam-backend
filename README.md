# kaasupathayam-backend

FastAPI + PostgreSQL API for Kaasupathayam, a household expense tracker.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and PostgreSQL 15+.

```sh
cp .env.example .env              # then set KAASU_JWT_SECRET and KAASU_GOOGLE_CLIENT_IDS
docker compose up -d db           # or use a local Postgres matching KAASU_DATABASE_URL
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0
```

Sign-in is Google-only: clients send a Google ID token to `POST /auth/google`, and the API returns its own bearer token. Tokens are accepted only when their audience is one of `KAASU_GOOGLE_CLIENT_IDS`.

Interactive API docs: http://localhost:8000/docs

## Development

```sh
uv run pytest                     # tests use in-memory SQLite, no Postgres needed
uv run ruff check . && uv run ruff format .
uv run alembic revision --autogenerate -m "describe change"   # after editing models.py
```

## Deployment

On every push and pull request, GitHub Actions (`.github/workflows/ci.yml`) runs lint, the tests on SQLite and on Postgres, and the migrations. Render deploys `main` only after those checks pass (`render.yaml`, `autoDeployTrigger: checksPass`). Migrations run when the service starts.

One-time setup:

1. **Neon:** create a project (region: AWS Singapore, to match Render) and copy the connection string. It can be pasted as-is; the `postgresql://` prefix is converted for psycopg automatically.
2. **Render:** go to New → Blueprint, select this repo, and fill in:
   - `KAASU_DATABASE_URL`: the Neon connection string.
   - `KAASU_GOOGLE_CLIENT_IDS`: `["<Google web client id>"]`.
   - `KAASU_CORS_ORIGINS`: `["https://<website>.onrender.com"]`.

   `KAASU_JWT_SECRET` is generated for you.
3. Check `https://<service>.onrender.com/health`.

The free instance sleeps after 15 minutes without traffic, so the first request afterwards takes about a minute.
