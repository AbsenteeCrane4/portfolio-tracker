# Architecture

The project is a modular monolith with plugin-shaped seams. Everything runs in
one process. Features are internal packages, wired together by explicit
dependency injection at startup. They are not entry-point plugins yet.

The seams are shaped so that a later move to `importlib.metadata` entry points
is mechanical. Don't build a plugin registry, entry-point loading, or dynamic
discovery until two real implementations of the same interface are competing.
The second price provider (PT-017) is the first likely trigger, and even then
explicit wiring may well be enough.

## Layout

The tree below is the target. Files are created by the issues that need them,
so not all of them exist yet.

```
src/portfolio/
  core/                 # stable; never imports features/
    settings.py         # typed settings; the only reader of the environment
    db.py               # declarative Base, Money/Quantity types, engine/session
    ledger.py           # append-only transaction log
    positions.py        # position + cost-basis engine
    valuation.py        # daily value series
    performance.py      # IRR, return attribution
    instruments.py      # symbol/instrument registry
    scheduling.py       # job runner
    quota.py            # per-provider call budgets
    context.py          # AppContext handed to features
  interfaces/           # Protocols only, no implementations
    price_provider.py, fx_provider.py, news_provider.py,
    importer.py, report.py, roundup_hook.py, tax_rules.py
  features/             # depends only on interfaces/ + AppContext
    providers/          # twelvedata, finnhub, tiingo, ...
    importers/          # per-broker CSV profiles
    reports/            # taxable income, CGT, diversity, ...
    roundup/
  api/                  # FastAPI routers, thin
  wiring.py             # the only module that knows both core and features
```

## Core vs feature

A component is **core** if losing it breaks everything *and* you would never
want two of it active at once. Everything else is a **feature**.

- **Core:** auth, ledger, the position/cost-basis engine, the valuation series,
  performance maths, the instrument registry, storage, the scheduler, the quota
  manager, and the API shell.
- **Feature:** price and FX providers, news sources, broker importers, reports,
  analysers, roundups, notification channels, exporters, and tax rule packs.

Tax rules are the deliberate exception to that test. Only one jurisdiction is
ever active, but its rules are a feature, because jurisdiction-specific policy
must not leak into the engine. The cost-basis **engine** is core. The
**matching rules** it consumes, including HMRC same-day, 30-day, and Section
104 matching, are a feature that implements `interfaces/tax_rules.py`.
`wiring.py` injects that implementation into the engine.

## AppContext

Features receive their dependencies through `AppContext`: the DB session
factory, the shared rate-limited HTTP client, the quota manager, settings, and
typed capabilities exposed by core (for example, read access to positions).

Keep it from turning into a service locator:

- Capabilities are typed attributes whose types are Protocols. They are not
  string-keyed lookups or a `get(name)` registry.
- Shared infrastructure belongs on the context. A dependency only one feature
  needs is passed to that feature's constructor in `wiring.py`.
- A feature declares what it uses. Tests build a fake context containing only
  those attributes.

## Source data vs derived data

| Kind | Tables | Rule |
|---|---|---|
| Source | ledger entries, `prices`, `fx_rates`, suggestions | Append or insert only. The ledger is never updated or deleted. Market data is kept permanently. |
| Derived | positions, cost basis, `portfolio_valuations`, return figures | Deterministic function of source data. Safe to drop and rebuild. An incremental recompute equals a full rebuild. |

Market data is source data inside this system, even though it originates
outside it. Re-fetching it costs quota, so it is never treated as disposable.

## Valuation series

Portfolio value over time is the headline feature. Holdings on any date are
derived from the ledger, then multiplied by that date's cached close and FX
rate. The result is materialised into a daily `portfolio_valuations` table.
When any input changes (transaction, price, FX rate, or corporate action), the
series is invalidated and recomputed from the first affected date onward.
Requests read the materialised series. They never recompute the whole series,
and the frontend never computes it.

Where a date has no price, the valuation records that the figure is stale or
incomplete. It never writes a fabricated number. When several sources hold a
price for the same instrument and date, the choice between them must be
deterministic (a configured precedence), otherwise rebuild equivalence breaks.

## Deployment

The API and scheduler run on Fly.io or Railway. The frontend runs on Vercel.
Vercel cannot host the scheduled worker.
