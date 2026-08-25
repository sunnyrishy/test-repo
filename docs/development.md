# Development

## Run everything

```bash
cp .env.example .env      # then fill in board tokens
docker compose up --build
```

- API: http://localhost:8000 (docs at `/docs`)
- Dashboard: http://localhost:5173

Migrations run automatically on backend start.

## Backend without Docker

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/job_agent
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
cd backend && pytest tests -q
```

The suite covers date filtering, experience parsing, seniority filtering,
location filtering, employment filtering, role classification, deduplication
and canonical merging, connector normalization, AI response validation,
verification caching, scoring, notifications, and one end-to-end pipeline test
that runs ingest → merge → verify → score → API. It needs no network and no
PostgreSQL server (the JSON columns fall back to plain JSON on SQLite).

## Scripts

```bash
python scripts/seed_profile.py    # load config/candidate_profile.yaml into the DB
python scripts/run_discovery.py   # discovery only
python scripts/run_pipeline.py    # discover → merge → verify → score
```

## Migrations

```bash
cd backend
alembic revision --autogenerate -m "add scores"
alembic upgrade head
```

## Using a real model

The default `AI_PROVIDER=mock` performs no reasoning: it reports only what a
literal read of the text supports and leaves the semantic checks unknown, so
every job it touches lands in `REVIEW` and none reach the dashboard. That is
intentional — a development stand-in must not manufacture verdicts. For real
results:

```env
AI_PROVIDER=anthropic     # or openai
AI_API_KEY=...
AI_MODEL=<model id>
```

Then `POST /api/admin/verification/run` (or let the worker do it). Adding a
provider means one file in `app/services/ai/` implementing `AIProvider` and one
entry in `PROVIDERS`; nothing else changes.

## Extending it further

- **More sources** — implement `JobSourceConnector` in `app/sources/` and
  register it in `sources/registry.py`. See `docs/sources.md`.
- **Resume matching** — the architecture leaves room: parse the resume into the
  same skill vocabulary the profile uses, and add a resume-fit component to
  `WEIGHTS`. Nothing in the pipeline needs to move.
- **Semantic duplicate detection** — add an embedding step in
  `services/deduplication.py` after the fingerprint pass.
