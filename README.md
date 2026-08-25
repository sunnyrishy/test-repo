# AI Job Intelligence & Qualification Engine

A personal job discovery and qualification pipeline: it pulls newly posted jobs
from configured sources, normalizes them into one schema, removes duplicates,
filters them against a configurable candidate profile, and presents the
survivors in a dashboard that links to the employer's own application page.

The system optimizes for **genuinely applicable jobs delivered**, not for the
number of jobs found.

## The pipeline

```
SOURCES → NORMALIZE → DEDUPLICATE → DETERMINISTIC FILTERS
        → AI VERIFICATION → SCORE → DASHBOARD → you apply
```

- **Discovery** favours recall: Greenhouse and Lever connectors behind one
  interface, each with its own timeout, retry, rate limit and concurrency. A
  source that fails is recorded and skipped, never fatal.
- **Deduplication** folds one vacancy seen on several sources into one
  canonical job, preferring the employer's own ATS so the Apply button goes to
  the employer.
- **Deterministic filters** do the cheap work — freshness, US location,
  full-time, seniority, role, and required-vs-preferred experience — so the
  model is never asked what a regex can answer.
- **AI verification** does the semantic work, and its output is validated
  rather than trusted: the decision must follow from the checks it reported,
  unknowns become `REVIEW` instead of a pass, and invalid output is retried and
  then recorded as an error.
- **Scoring** orders what is already eligible. It can never promote a job that
  failed a hard requirement.
- **Notifications** are digests above a score threshold, once per job.

Nothing in the pipeline fabricates data: a posting date the source does not
publish stays unknown and is shown as "Posted date unavailable", jobs without
an application URL say so rather than linking somewhere invented, and the
system never submits an application for you.

## Status

Everything above works end to end, with 130 tests. Two deliberate limits:

- **Sources.** Greenhouse and Lever are implemented. LinkedIn, Indeed,
  Handshake, Wellfound, EchoJobs and Ashby are not: each needs its own
  compliance answer (terms, authentication, rate limits) before a connector is
  written, and fragile scraping is not the default architecture here. Adding
  one is a single file — see `docs/sources.md`.
- **AI provider.** `AI_PROVIDER` defaults to `mock`, which performs no
  reasoning and leaves every semantic check unknown, so its jobs land in
  "needs review" rather than on the dashboard. Set `openai` or `anthropic` with
  a model and key for real verification.

Resume matching and the other future AI features in the plan are not
implemented; `docs/development.md` says where they attach.

## Quick start

```bash
cp .env.example .env     # add GREENHOUSE_BOARDS / LEVER_BOARDS and an AI key
docker compose up --build
```

Dashboard on http://localhost:5173, API on http://localhost:8000/docs. The
worker runs the whole pipeline on `JOB_DISCOVERY_INTERVAL_MINUTES`; the
dashboard's "Run pipeline" button does it on demand.

With no boards configured the pipeline runs and finds nothing — there is no
sample data in production code. Set, for example:

```env
GREENHOUSE_BOARDS=stripe,figma
LEVER_BOARDS=plaid
```

## Hosting

`docs/deployment.md` covers deploying to Vercel as two projects (API +
dashboard) with a managed Postgres and a cron-driven pipeline — from the
dashboard or the CLI, with `docs/schema.sql` for setting up the database
without a terminal — and says what changes there: no always-on worker, bounded verification batches, and a
required `API_KEY` on the admin routes. A single always-on host running
`docker-compose.yml` is the simpler alternative.

## Layout

```
backend/app/sources/     source connectors (one interface, one file each)
backend/app/services/    normalization, dedup, filtering, verification, scoring
backend/app/services/ai/ pluggable LLM providers (openai, anthropic, mock)
backend/app/api/         jobs, profile, settings, admin endpoints
backend/app/workers/     scheduled pipeline, verification and cleanup workers
backend/tests/           filter, dedup, AI-validation, scoring and pipeline tests
config/                  candidate profile (never hard-coded in code)
frontend/src/            React + TypeScript dashboard
api/index.py             Vercel serverless entry point for the API
prompts/                 AI verification prompt
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
