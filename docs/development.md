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
fingerprints and connector normalization. It needs no database and no network.

## Scripts

```bash
python scripts/seed_profile.py    # load config/candidate_profile.yaml into the DB
python scripts/run_discovery.py   # one discovery pass, with logging
```

## Migrations

```bash
cd backend
alembic revision --autogenerate -m "add scores"
alembic upgrade head
```

## Where the next phases go

- **Phase 4** — extend `services/deduplication.py` to merge fingerprint matches
  into a canonical `Job` (`canonical_job_id`) and attach every `JobSource`.
- **Phase 5** — add `services/ai/{base,openai_provider,anthropic_provider}.py`
  behind `AI_PROVIDER`/`AI_MODEL`, a `job_verifications` table, and Pydantic
  validation of the model's JSON with retry-then-`verification_error`.
- **Phase 6** — a `job_scores` table and the 0–100 weighting; scores must never
  override a hard rejection.
