---
name: market-data
description: External price and FX data for this portfolio tracker. Use when implementing, testing, or reviewing price/FX/news providers, the shared HTTP client, quota ledger and rate limiting, polling or backfill jobs, the prices/fx_rates cache, gap detection, trading calendars, stale/missing price handling, provider fallback, or data provenance (PT-014 to PT-021, PT-040's benchmark fetches, PT-042).
---

# Market data

How prices and FX rates get from free-tier providers into Postgres, and from
there into valuation, without wasting quota or fabricating numbers.

The core principle: **Postgres is the durable system of record for retrieved
market data. Providers are sources, asked only for what is missing.**

## Implementation state

Built so far: `Settings.providers`, which holds the API key and
`daily_quota` for each configured provider, in `core/settings.py`. A provider
without a key is simply not wired. Nothing else exists yet.

| Piece | Planned location | Issue |
|---|---|---|
| `PriceProvider`, `FxProvider`, `NewsProvider` Protocols | `interfaces/` | PT-005 |
| Shared HTTP client and quota manager on `AppContext` | `core/context.py`, `core/quota.py` | PT-004, PT-015 |
| `prices` cache, `missing_dates`, `latest_price` | core repository | PT-014 |
| Twelve Data (primary), then Finnhub (fallback) | `features/providers/<name>/` | PT-016, PT-017 |
| Daily EOD polling job | `core/scheduling.py` plus a job | PT-018 |
| Resumable backfill | a job | PT-019 |
| `fx_rates` | core repository plus `FxProvider` | PT-020 |
| Stale and unpriced indicators | API layer | PT-021 |

Settings currently model only a **daily** budget. PT-015 adds per-minute
rates and provider-specific reset times. Volatile provider facts, such as free
tiers and limits, are in `docs/market-data.md`. Treat them as unverified, and
when you rely on a figure, record it in the settings defaults with a dated
comment (PT-016).

## Pipeline

```
scheduler job (one per provider; daily poll > backfill priority)
    │  asks the cache what is missing
    ▼
gap detection: missing_dates(instrument, start, end) against the trading calendar
    │  only genuine gaps, batched into the fewest requests
    ▼
QuotaManager.reserve(provider, cost)   → refused: stop the job cleanly, log remaining work
    ▼
shared rate-limited HTTP client (from AppContext; never a new httpx.AsyncClient)
    ▼
provider feature: map canonical instrument → provider symbol, call, parse
    ▼
normalisation: Pydantic model → Decimal, date, currency, source, fetched_at
    ▼
upsert into prices / fx_rates (instrument, date, source)
    ▼
invalidate portfolio_valuations from the earliest changed date
    ▼
valuation and analytics read the cache, with staleness carried through
```

## Rules by stage

### Provider contract (PT-016)

- Implements the Protocol, and nothing imports the provider directly except
  `wiring.py`.
- Provider symbol formats (for example LSE suffixes) are mapped inside the
  provider feature to and from canonical instruments (PT-008).
- **Partial success:** return the prices obtained plus per-symbol errors. One
  bad symbol never fails the batch.
- **Typed failures,** which the job must handle differently:

| Failure | Job behaviour |
|---|---|
| quota refused by `QuotaManager` | stop this provider for the window, log the remaining work, no retry |
| rate limited (429 / per-minute) | bounded backoff, each attempt reserves quota; give up after the cap |
| provider error (5xx, timeout) | bounded exponential backoff, each attempt costs quota |
| malformed response (fails the Pydantic model) | treated as a failed fetch for those symbols: no partial write, no repair |
| no data for a symbol/date | a gap stays a gap; the next provider in priority may try (PT-017) |

### Quota (PT-015)

- No call goes out without a successful `reserve()`. Retries reserve again.
- Every call is recorded in `provider_calls` (provider, endpoint, timestamp,
  symbol count, outcome).
- Exhaustion is a normal outcome, not an exception storm. The job stops,
  records what is left, and resumes next window.
- The reset follows the provider's stated reset time, not local midnight.
- Daily polling has priority over backfill. Backfill uses its own
  lower-priority share and must never starve the poll (PT-019).

### Normalisation

- **JSON numbers lose precision by default.** This was verified with Pydantic
  2.13.5 on 2026-10-07: `response.json()`, and
  `Model.model_validate_json(...)` on a JSON **number**, both go through
  `float`, so `123.456789012345678901` becomes
  `Decimal('123.45678901234568')`. Parse with
  `json.loads(response.content, parse_float=Decimal)` and then
  `Model.model_validate(...)`. `model_validate_json` is only safe when the
  provider sends numbers as JSON **strings**. Every provider gets a test with
  a high-precision numeric literal.
- The market date comes from the provider's bar date. Never derive it from
  `fetched_at` or the current UTC time. `fetched_at` is a UTC `datetime`.
- **Currency units:** LSE prices often arrive in GBX/GBp (pence). How GBX is
  normalised is undecided. Ask before the first LSE instrument is stored. A
  silent 100× error is the likeliest UK bug in this whole pipeline.
- **Close vs adjusted close:** store both (PT-014). Valuation pairs raw close
  with ledger quantity. Dividend-adjusted closes would double-count dividends
  already in the ledger. PT-028 documents the split convention.

### Cache (PT-014, PT-020)

- Primary key is `(instrument, date, source)`. A repeat fetch upserts and
  never duplicates.
- If an upsert **changes** an existing close (a provider revision), it must
  invalidate valuations from that date, the same as a new price.
- No null rows, and no forward-fill written to storage. Forward-fill happens
  at read time only, flagged as carried (PT-014, PT-022).
- `latest_price` and the FX lookup return the value **and its age**.
- A same-currency FX lookup returns exactly `Decimal(1)` without a DB hit
  (PT-020).
- FX rates are stored with an explicit base/quote pair. Never store a bare
  "rate". Test conversions with a rate far from 1.

### Gaps, calendar, and backfill (PT-014, PT-019)

- `missing_dates` checks against a trading calendar (weekends and exchange
  holidays). A simple calendar table is preferred over a dependency;
  `pandas-market-calendars` only if justified in the PR.
- Backfill work is stored as durable units (instrument + date range). A
  restart resumes; it does not start over. It requests only genuinely missing
  ranges, and is triggered automatically when a new instrument appears in the
  ledger.
- Progress is observable as the percentage of required instrument-days
  present.

### Polling (PT-018)

- One run per exchange after that exchange's close, in the exchange's
  timezone. Only instruments with an open position are polled.
- Idempotent: a second run in the same window fetches nothing.
- Record the outcome: symbols requested, filled, failed, and quota consumed.
- Intraday refresh is optional and off by default. No websockets or live
  ticks.

### Provenance and fallback (PT-017)

- Every row keeps its `source` and `fetched_at`.
- Providers are tried in configured priority. The next provider is tried only
  when the first has no data or no quota.
- Conflicting closes for the same instrument and date are logged, and the
  higher-priority source wins **deterministically** at read time. Rebuild
  equivalence depends on this.
- PT-017's context says it justifies revisiting explicit wiring in favour of a
  plugin registry. Raise that decision with the user then; don't pre-build it.

### Staleness (PT-021)

- Every API value that depends on a price carries the price date and a
  staleness flag. The threshold is configurable, defaulting to more than one
  trading day old.
- No price at all means an explicit **unpriced** state, excluded from totals,
  with the exclusion reported. Never zero.
- Read-time forward-fill across non-trading days is flagged as carried.

## Failure scenarios

| Scenario | Correct outcome |
|---|---|
| Quota runs out halfway through a batch | Fetched rows are saved, the remaining symbols logged, the job ends cleanly, and the next window resumes from the gaps |
| Provider is down all day | Prices go stale, the UI shows a stale indicator, and the fallback provider is tried if it is configured and has quota |
| One symbol in a batch is unknown to the provider | Other symbols are saved; the error is recorded per symbol |
| Response fails validation | Nothing is written for the affected symbols; they count as failed, with no repair |
| Process killed during backfill | On restart, durable work units resume |
| Provider revises yesterday's close | The upsert changes the row, and valuations are invalidated from that date |
| Daily poll runs twice | The second run finds no gaps and makes no calls |
| Holiday on the exchange | It is not a gap, so nothing is fetched and nothing is flagged missing |

## Not allowed

- Yahoo Finance unofficial endpoints.
- A feature creating its own HTTP client, or calling without a reservation.
- Unbounded retries, or retries that don't count against quota.
- Writing zero, null, or carried-forward values into `prices` or `fx_rates`.
- Treating the provider as the source of truth for data already cached.
- Scraping, except behind the provider interface in an isolated subprocess.

## Testing

- **Recorded fixtures only,** with credentials and account identifiers
  scrubbed. No live calls in tests or CI.
- **Fake quota manager and fake HTTP transport** via the fake `AppContext`.
- **Must-have tests:**
  - exhaustion mid-batch stops cleanly with the remaining work recorded;
  - retries consume quota and stop at the cap;
  - partial batch success;
  - a malformed response writes nothing;
  - a second poll in the same window makes zero calls;
  - backfill resumes after a simulated kill;
  - a holiday is not reported as a gap;
  - an upsert revision invalidates valuations;
  - Decimal parsing is exact;
  - an FX same-currency lookup returns 1;
  - the deterministic source choice under conflict.

For a final pass, run the `financial-correctness-review` skill.
