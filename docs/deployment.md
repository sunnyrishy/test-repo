# Deploying to Vercel

Two Vercel projects from this one repository:

| Project | Root directory | What it serves |
|---|---|---|
| `ai-job-intelligence-api` | repository root | FastAPI, as a Python serverless function, plus the cron |
| `ai-job-intelligence-web` | `frontend` | the React dashboard |

The API project builds from the repository root, not `backend/`, because the
service reads `config/candidate_profile.yaml` and `prompts/job_verification.txt`
at runtime and both live outside the backend package.

## What changes when you host it

Vercel has no always-on process, so the APScheduler worker does not run there.
`vercel.json` schedules `GET /api/admin/cron` every three hours instead, and
that endpoint does one discovery pass plus a bounded verification batch
(`VERIFICATION_BATCH_SIZE`) so it finishes inside the function's time limit;
whatever is left is picked up by the next run. The `worker` service in
`docker-compose.yml` is still the right answer for a self-hosted stack.

You also need a managed PostgreSQL database — Vercel Postgres, Neon and
Supabase all work. **Use the pooled connection string.** Serverless
invocations are short-lived and would otherwise exhaust the server's
connections; the engine disables its own pool when `VERCEL` is set.

## 1. Database

Create the database, then run the migrations from your machine (they are
excluded from the function bundle):

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg://…pooler…/db?sslmode=require'
alembic upgrade head
python ../scripts/seed_profile.py
```

## 2. API project

```bash
npm i -g vercel
vercel login
vercel link            # at the repository root; create the API project
vercel env add DATABASE_URL production      # the pooled URL, sslmode=require
vercel env add API_KEY production           # generate one: openssl rand -hex 32
vercel env add AI_PROVIDER production       # anthropic | openai
vercel env add AI_API_KEY production
vercel env add AI_MODEL production
vercel env add GREENHOUSE_BOARDS production
vercel env add LEVER_BOARDS production
vercel env add CORS_ORIGINS production      # https://<your-web-project>.vercel.app
vercel deploy --prod
```

`API_KEY` is required in production. Without it every admin route is open to
anyone who finds the URL, including the one that spends your model budget.

Vercel Cron authenticates with `Authorization: Bearer $CRON_SECRET`, and the
guard accepts a bearer token, so **set `CRON_SECRET` to the same value as
`API_KEY`**.

Optional: `MAX_JOB_AGE_HOURS`, `MIN_MATCH_SCORE`, `NOTIFICATION_MIN_SCORE`,
`VERIFICATION_BATCH_SIZE`, and the SMTP/Telegram/Discord variables from
`.env.example`.

## 3. Frontend project

```bash
cd frontend
vercel link            # create the web project, root directory "frontend"
vercel env add VITE_API_BASE_URL production   # https://<your-api-project>.vercel.app
vercel deploy --prod
```

Then set `CORS_ORIGINS` on the API project to the web project's URL and
redeploy the API.

The admin key is **not** a build variable. Anything compiled into the bundle is
public, and this key triggers model spend — so the dashboard asks for it in the
"Admin key" field and keeps it in that browser's localStorage.

## 4. Check it

```bash
curl https://<api>.vercel.app/health
curl -H "X-API-Key: $API_KEY" -X POST https://<api>.vercel.app/api/admin/pipeline/run
```

Then open the web URL; the statistics page shows what the run did.

## Cost and limits

- One cron run verifies at most `VERIFICATION_BATCH_SIZE` jobs (default 50).
  Deterministic filters run first and are free, so only survivors cost tokens,
  and verifications are cached until the posting or profile changes.
- `maxDuration` is 60s in `vercel.json` — the Hobby ceiling. On Pro you can
  raise it and increase the batch size.
- Cron on Hobby is limited to a daily schedule; the three-hourly schedule here
  needs Pro. Lower it to `0 6 * * *` to stay on Hobby.

## Alternative

A single always-on host (Railway, Render, Fly.io) runs `docker-compose.yml`
essentially as-is, keeps the real scheduler, and avoids the batching and
connection-pooling constraints above. Vercel is the better fit if you want the
dashboard on a CDN and are happy with cron-driven ingestion.
