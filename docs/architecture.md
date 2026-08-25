# Architecture

The system is a deterministic pipeline with AI used only where semantic
reasoning is genuinely required. It is not one autonomous agent.

```
SOURCE CONNECTORS → NORMALIZATION → DEDUPLICATION → DETERMINISTIC FILTERS
      → AI VERIFICATION → SCORING → DATABASE → DASHBOARD → HUMAN APPLIES
```

`services/pipeline.py` runs the stages in that order. Each stage commits before
the next begins, so a later failure never discards earlier work, and a stage
that raises is recorded in the run result instead of aborting the pipeline.

## Stage responsibilities

| Stage | Module | Optimizes for |
|---|---|---|
| Discovery | `app/sources/*`, `app/services/discovery.py` | recall |
| Normalization | `app/services/normalization.py` | one internal schema |
| Deduplication | `app/services/deduplication.py` | one canonical job |
| Deterministic filters | `app/services/filtering.py` | cheap precision |
| AI verification | `app/services/verification.py`, `app/services/ai/*` | precision |
| Scoring / ranking | `app/services/scoring.py` | ordering |
| Notifications | `app/services/notification.py` | one digest, no repeats |

## Dates

Four timestamps are tracked separately and never conflated:

- `posted_at` — the employer's posting date, from the source. Left `NULL` when
  the source does not publish one.
- `source_updated_at` — when the source last changed the posting.
- `first_seen_at` — when this system first ingested it. **Never** used as the
  posting date.
- `last_verified_at` — when AI verification last ran.

`freshness_status` is derived: `FRESH` within `MAX_JOB_AGE_HOURS`, `STALE`
beyond it, and `UNKNOWN` when there is no employer date. An unknown date is
displayed as "Posted date unavailable"; it is never presented as new and never
invented.

## Deterministic filters

`hard_filter()` returns the first failing check as a machine-readable reason,
which the statistics endpoint aggregates:

| Reason | Meaning |
|---|---|
| `OLDER_THAN_MAX_AGE` | posted outside the freshness window |
| `POSTING_DATE_UNKNOWN` | no employer date (only when unknowns are disallowed) |
| `INTERNSHIP` / `NOT_FULL_TIME` | employment type outside the profile |
| `NOT_US` | location resolves to a non-US country |
| `LOCATION_UNDETERMINED` | e.g. a bare "Remote" with no geography |
| `SENIORITY_TOO_HIGH` | Senior/Staff/Principal/Lead/Manager/... in the title |
| `ROLE_EXCLUDED` / `ROLE_UNRELATED` | title outside the profile's role sets |
| `EXPERIENCE_TOO_HIGH` | a **required** mention exceeds the profile's ceiling |

Experience parsing works clause by clause, so "Required: 3 years of Java.
5 years preferred." yields one required mention (3y) and one preferred (5y);
a neighbouring sentence's "preferred" cannot soften a hard requirement.

An `Unknown` employment type is **not** a rejection — the description may state
it, which is AI verification's job, not a regex's.

## Source connectors

`JobSourceConnector` gives every source the same interface plus configurable
timeout, retry count with exponential backoff, rate limit and concurrency. A
connector that fails is logged into `discovery_runs.per_source` and skipped; the
pipeline continues with the remaining sources.

Only documented public endpoints are used (Greenhouse job board API, Lever
postings API). No connector implements a bypass for anti-bot measures, CAPTCHAs,
authentication or other access controls; a source that cannot be accessed
compliantly is simply not added.

## Candidate profile

The profile lives in `config/candidate_profile.yaml` and, once the app runs, in
the `candidate_profile` table (editable via `PUT /api/profile`). No candidate
detail is written into business logic — every filter takes the profile as an
argument.

## Deduplication

Matching runs in priority order: exact `source` + `external_id` (in the
ingestion path), then the `company + title + location` fingerprint. When one
vacancy is seen twice in a single run, the second sighting is recorded as an
extra `job_sources` row rather than dropped, so no provenance is lost.

`merge_duplicates()` folds each fingerprint group into one canonical job. The
employer's own ATS wins over an aggregator (`CANONICAL_SOURCE_PRIORITY`), so
the Apply button points at the employer's application URL. Duplicates are not
deleted — they are deactivated and given a `canonical_job_id`, so an old link
still resolves and a later run recognizes them. The canonical job inherits a
posting date, description or salary the winner lacked, but nothing that neither
posting stated.

Semantic-similarity matching is deliberately not implemented: it needs
embeddings, and the cheaper keys resolve the duplicates these sources actually
produce.

## AI verification

Only jobs that survived the deterministic filters are sent, and only when
something changed: `needs_verification()` re-runs a job when its description
changed, the candidate profile changed, the previous attempt errored, or the
verification is older than `VERIFICATION_MAX_AGE_DAYS`. Everything else reuses
the stored verdict, which is what keeps model spend proportional to new work.

The provider is chosen by `AI_PROVIDER` / `AI_MODEL` (`openai`, `anthropic`, or
the development-only `mock`); business logic never imports a vendor SDK.

Model output is never trusted:

1. The response is parsed out of any prose or code fence.
2. It is validated against `VerificationResult`, which forbids unknown fields
   and range-checks every number.
3. **The decision must follow from the checks.** A response that reports a
   failed hard requirement but says `PASS` is corrected to `FAIL`, and one with
   an undetermined check becomes `REVIEW`. The checks are the evidence; the
   decision field is not taken on trust.
4. Invalid output is retried up to `AI_MAX_ATTEMPTS`, then stored as
   `decision=ERROR` with the reason — never as a guess, and never as malformed
   data in the jobs tables.

A `null` check means "could not be determined", which is why unknowns produce
`REVIEW` rather than a pass. The mock provider reasons about nothing and
reports everything as unknown, so it can never wave a job through.

## Scoring

`score_job()` returns `None` for anything that is not a verified `PASS`, so a
score can only ever order jobs that are already eligible — a role requiring 30
years cannot be rescued by a strong title match. Weights total 100 and are
listed in `WEIGHTS`.

Two deliberate choices: an unknown work authorization or sponsorship scores at
the midpoint rather than zero (absence of information is not evidence of a
problem), and a missing salary scores above a low salary rather than below it.
There is no company-reputation signal because we have no reputation data, and
inventing one would be fabricating information; posting completeness stands in
for it.

## Notifications

Digests only, above `NOTIFICATION_MIN_SCORE`, one message per channel per run.
The `notifications` table records job + channel, so a job is never sent twice.
A channel that fails is logged and leaves its jobs unmarked, so the next run
retries them.
