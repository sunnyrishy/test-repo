# Sources

## Implemented

| Source | Access | Configuration |
|---|---|---|
| Greenhouse | Public job board API (`boards-api.greenhouse.io`), no auth | `GREENHOUSE_BOARDS=stripe,figma` |
| Lever | Public postings API (`api.lever.co/v0/postings`), no auth | `LEVER_BOARDS=netflix,plaid` |

Each value is the company's board token, taken from its careers URL:
`https://boards.greenhouse.io/**stripe**` → `stripe`.

## Access-order preference

1. Official APIs
2. Public job feeds
3. ATS APIs (where we are today)
4. Public company career pages
5. Permitted aggregators
6. Browser automation, only where legally and technically permitted

Fragile scraping is deliberately not the default architecture.

## Not yet implemented

LinkedIn, Indeed, Handshake, Wellfound, EchoJobs and Ashby are Phase 10. Each
requires its own compliance answer — terms of use, authentication, rate limits
— before a connector is written. Adding one means implementing
`JobSourceConnector` in `backend/app/sources/` and registering it in
`sources/registry.py`; nothing else in the pipeline changes.

## Adding a connector

```python
class MySource(JobSourceConnector):
    name = "mysource"

    async def fetch(self) -> list[NormalizedJob]:
        ...
```

Rules: never invent a posting date, an application URL, a salary or a location.
Anything the source does not state stays `None`. Prefer the employer's own
application URL over an aggregator's.
