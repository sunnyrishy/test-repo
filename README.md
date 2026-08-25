# AI Job Intelligence & Qualification Engine

A personal job discovery and qualification pipeline: it pulls newly posted jobs
from configured sources, normalizes them into one schema, removes duplicates,
filters them against a configurable candidate profile, and presents the
survivors in a dashboard that links to the employer's own application page.

The system optimizes for **genuinely applicable jobs delivered**, not for the
number of jobs found.

## Status

Phases 1–3 of the plan in `docs/architecture.md` are implemented:

- **Phase 1 — Foundation:** PostgreSQL + FastAPI + React + Docker, database
  models, Alembic migrations, configurable candidate profile, dashboard.
- **Phase 2 — Ingestion:** Greenhouse and Lever connectors behind a shared
  interface, normalization into one internal schema, storage with per-source
  provenance.
- **Phase 3 — Filtering:** date, location, employment, seniority, experience
  and role filters, each with tests.

Not implemented yet: canonical-job merging (Phase 4), AI verification
(Phase 5), scoring and ranking (Phase 6), notifications (Phase 9), and the
remaining sources (Phase 10). `docs/development.md` says where each one goes.

Nothing in the pipeline fabricates data: a posting date the source does not
publish stays unknown and is shown as "Posted date unavailable", and jobs
without an application URL say so rather than linking somewhere invented.

## Quick start

```bash
cp .env.example .env     # add GREENHOUSE_BOARDS / LEVER_BOARDS
docker compose up --build
```

Dashboard on http://localhost:5173, API on http://localhost:8000/docs.

With no boards configured the pipeline runs and finds nothing — there is no
sample data in production code. Set, for example:

```env
GREENHOUSE_BOARDS=stripe,figma
LEVER_BOARDS=plaid
```

## Layout

```
backend/app/sources/     source connectors (one interface, one file each)
backend/app/services/    normalization, deduplication, filtering, discovery
backend/app/api/         jobs, profile, settings, admin endpoints
backend/app/workers/     scheduled discovery worker
backend/tests/           filter, dedup and connector tests
config/                  candidate profile (never hard-coded in code)
frontend/src/            React + TypeScript dashboard
prompts/                 AI verification prompt (Phase 5)
docs/                    architecture, sources, development
```

## Configuration

Every threshold is an environment variable — see `.env.example`. The discovery
interval, freshness window and score thresholds are never hard-coded. Secrets
live in `.env`, which is git-ignored and never exposed to the frontend.

## Compliance

Only documented public endpoints are used. No connector bypasses anti-bot
measures, CAPTCHAs, authentication or access controls, and the system never
submits an application on the user's behalf.
