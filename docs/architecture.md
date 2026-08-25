# Architecture

The system is a deterministic pipeline with AI used only where semantic
reasoning is genuinely required. It is not one autonomous agent.

```
SOURCE CONNECTORS → NORMALIZATION → DEDUPLICATION → DETERMINISTIC FILTERS
      → [AI VERIFICATION → SCORING]  → DATABASE → DASHBOARD → HUMAN APPLIES
```

The bracketed stages are Phase 5–6 and are not implemented yet. Everything
before them is.

## Stage responsibilities

| Stage | Module | Optimizes for |
|---|---|---|
| Discovery | `app/sources/*`, `app/services/discovery.py` | recall |
| Normalization | `app/services/normalization.py` | one internal schema |
| Deduplication | `app/services/deduplication.py` | one canonical job |
| Deterministic filters | `app/services/filtering.py` | cheap precision |
| AI verification | *(Phase 5)* | precision |
| Scoring / ranking | *(Phase 6)* | ordering |

## Dates

Four timestamps are tracked separately and never conflated:

- `posted_at` — the employer's posting date, from the source. Left `NULL` when
  the source does not publish one.
- `source_updated_at` — when the source last changed the posting.
- `first_seen_at` — when this system first ingested it. **Never** used as the
  posting date.
- `last_verified_at` — when AI verification last ran (Phase 5).

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
