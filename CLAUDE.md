# CLAUDE.md

Project context for Claude Code. Read this before making changes.

## What this is

A self-hosted portfolio tracker modelled on **Sharesight**, extended with a
pluggable market-analysis layer.

Sharesight is the functional reference. When a design question comes up about
portfolio behaviour, reporting, or terminology, the default answer is "do what
Sharesight does" unless there's a stated reason not to. Where this project
diverges: single-user, self-hosted, UK-only tax rules, free-tier price data, and
an added roundup/suggestion engine Sharesight has no equivalent of.

Single-developer project. Optimise for clarity and shipping speed over generality.

## Stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2
- **DB:** Postgres (Supabase-hosted). Access via SQLAlchemy, not the Supabase client
- **Frontend:** Next.js, talks to the API over HTTP only
- **Tooling:** `uv` for dependencies, `ruff` for lint + format, `pytest` + `pytest-asyncio`
- **Deploy:** API and scheduler on Fly.io or Railway; frontend on Vercel.
  Vercel cannot host the scheduled worker — do not propose putting it there.

## UI source of truth

The wireframe at `docs/design/Portfolio Tracker UI.html` is the single source of
truth for the UI and all frontend work. Open it before starting any frontend
issue. Layout, screens, navigation, component structure, and information
hierarchy follow the wireframe.

- If the wireframe and an issue disagree, stop and ask — don't pick one silently.
- If the wireframe and this file disagree on behaviour (e.g. it shows a bare
  percentage), the hard rules below win; flag the discrepancy rather than
  copying it.
- Don't invent screens, controls, or flows the wireframe doesn't show. If
  something is missing, ask; the wireframe gets updated first, then the code.
- The wireframe is a layout reference, not a styling spec or a data contract.
  Figures come from the API, never hard-coded from wireframe sample data.
- Frontend scope is still limited to what a GitHub issue covers (see
  "Working with me").

## Issue workflow

Work through the open GitHub issues one at a time, from the lowest issue number
to the highest. Do not skip ahead, work on two issues at once, or start work not
covered by an issue. Repeat this loop for each issue:

1. **Read the ticket** (`gh issue view <n>`), including its acceptance criteria.
2. **Sync and branch:** `git fetch`, checkout `main`, `git pull`, then create the
   branch off `main` named after the story ID (e.g. `PT-002`) and linked to the
   issue, e.g. `gh issue develop <n> --name PT-002 --base main --checkout`, so it
   shows under the issue's Development section on GitHub.
3. **Publish the branch** (`git push -u origin <branch>`) before doing any work
   on it, so it exists both locally and on the remote.
4. **Implement,** committing regularly: small commits, one concern each, pushed
   as you go. Run `ruff check`, `ruff format --check`, and `pytest` before each
   commit that proposes a finished piece of work.
5. **Open a PR** into `main` once the acceptance criteria are met. Reference the
   issue (`Closes #<n>`) in the description.
6. **Merge** only after the PR checks have passed and the PR is approved. If
   checks fail, fix them on the branch; never bypass or disable checks, and never
   force-merge.
7. **Prune:** after the merge, checkout `main`, `git pull`, delete the branch
   locally and on the remote, and run `git fetch --prune`. Only delete branches
   that are fully merged into `main`; never delete an unmerged branch.
8. **Move on** to the next-lowest open issue and repeat from step 1.

Stop and ask if an issue is ambiguous, blocked, depends on a later issue, or
would require breaking a rule in this file.

## Product scope

### v1 — the Sharesight core

- **Import:** broker CSV import with a per-broker mapping profile. Also support
  Sharesight's own export format and a generic trade CSV. Manual entry and
  opening-balance entry for holdings without full history.
- **Holdings view:** per-holding quantity, average cost, market value, unrealised
  gain, and return; portfolio totals.
- **Value over time graph:** daily portfolio value series, filterable by date
  range, with grouping by market, sector, or custom group.
- **Performance breakdown:** total return split into capital gain, dividend
  income, and currency gain. Annualised (money-weighted / IRR) return, not just
  simple percentage change.
- **Dividends:** recorded per holding, contributing to return. Manual confirmation
  of payments is acceptable; auto-detection is a later nicety.
- **Corporate actions:** share splits, consolidations, and DRP/DRIP reinvestments
  applied to the ledger as derived transactions.
- **Multi-currency:** base currency GBP, per-transaction trade currency, FX rate
  captured at transaction time and revalued daily.
- **Cash accounts:** tracked as instruments so deposits, withdrawals, and
  uninvested cash appear in portfolio value.

### v2 — reporting and analysis

- **Taxable income report:** dividends, distributions, and interest over a period,
  split UK vs foreign.
- **Sold securities / realised CGT report:** using HMRC matching rules.
- **Unrealised CGT report:** what would be realised if sold today.
- **Diversity report:** allocation by market, sector, industry, currency, custom group.
- **Benchmarking:** portfolio performance against a chosen instrument or index.
- **Future income:** projected dividends from declared and historical payments.
- **Market roundup:** scheduled analysis combining price action, news, and quant
  signals into suggestions the user accepts or dismisses.

### Explicitly not in scope

Order execution, broker API sync (import files instead), property or unlisted
asset tracking, multi-user or accountant sharing, non-UK tax regimes.

## Price data

**No real-time requirement.** End-of-day is the baseline; 15-minute delayed
intraday is a bonus where a free tier allows it. Never design anything that
assumes live ticks or websockets.

Free tiers are the binding constraint and they are stingy and change often, so
the provider must be swappable and the quota must be treated as a first-class
resource. Rough current picture (verify before committing):

| Provider | Free tier | Notes |
|---|---|---|
| Twelve Data | ~800 credits/day, 8 req/min | Good breadth, global coverage |
| Finnhub | 60 req/min, ~1yr history | Generous news endpoint |
| Alpha Vantage | ~25 req/day | Deep history, punishing limit |
| Tiingo | ~500 symbols/month | Strong EOD history, US-centric |
| FMP | ~250 calls/day EOD | Fundamentals included |
| EODHD | ~20 calls/day, 1yr history | Too tight for polling; backfill only |

Yahoo Finance's unofficial endpoints are not a dependency. They break without
warning and there's no contract behind them.

### Polling design

- One scheduled job per provider, not per holding. Batch symbols into the fewest
  possible requests.
- **Quota ledger:** every outbound call is recorded against a per-provider daily
  budget. When the budget is exhausted the job stops cleanly and resumes next
  window. Never burn the day's quota on a retry storm.
- **Prices are cached in Postgres, permanently.** A `prices` table keyed by
  (instrument, date, source) is the system of record. Providers are only ever
  asked for gaps.
- **Backfill is a separate, resumable job** from daily polling, with its own
  lower-priority quota allocation.
- Failed fetches leave gaps, they do not write nulls or carry forward silently.
  The UI shows a stale-price indicator rather than a wrong number.
- FX rates follow the identical pattern in an `fx_rates` table.

### Valuation series

Portfolio value over time is the headline feature, so it gets a dedicated design:
holdings on any date are derived from the ledger, multiplied by that date's
cached close and FX rate. Materialise the result into a daily
`portfolio_valuations` table, invalidated and recomputed from the first affected
date whenever a transaction or price is added. Do not recompute the whole series
per request, and do not compute it in the frontend.

## Architecture

**Modular monolith with plugin-shaped seams.** One process. Features are internal
packages wired by dependency injection at startup, not entry-point plugins yet.

The seams are designed so a later migration to `importlib.metadata` entry points
is mechanical. Do not build the plugin registry, entry-point loading, or dynamic
discovery until we have two real implementations of the same interface competing.

```
src/portfolio/
  core/                 # stable, no imports from features/
    ledger.py           # append-only transaction log
    positions.py        # position + cost basis engine
    valuation.py        # daily value series
    performance.py      # IRR, return attribution
    instruments.py      # symbol/instrument registry
    scheduling.py       # job runner
    quota.py            # per-provider call budgets
    context.py          # AppContext handed to features
  interfaces/           # Protocols only, no implementations
    price_provider.py
    fx_provider.py
    news_provider.py
    importer.py
    report.py
    roundup_hook.py
    tax_rules.py
  features/             # self-contained, depends only on interfaces/ + context
    providers/          # twelvedata, finnhub, tiingo, ...
    importers/          # per-broker CSV profiles
    reports/            # taxable income, CGT, diversity, ...
    roundup/
  api/                  # FastAPI routers, thin — no business logic
  wiring.py             # constructs concrete implementations at startup
```

### The boundary rule

Features receive everything through `AppContext` (db session, HTTP client, quota
manager, config, other capabilities). A feature must never import from `core.*`
internals directly.

If you find yourself writing `from portfolio.core.positions import recompute`
inside `features/`, stop — either add it to the context or add an interface.

Core must never import from `features/`. `wiring.py` is the only place that knows
about both.

### Core vs feature

Something is core if losing it breaks everything AND you'd never want two active
at once. Everything else is a feature.

- **Core:** auth, ledger, position/cost-basis engine, valuation series,
  performance maths, instrument registry, storage, scheduler, quota manager, API shell
- **Feature:** price and FX providers, news sources, broker importers, reports,
  analysers, roundups, notification channels, exporters, tax rule packs

The cost-basis *engine* is core; the *matching rules* it consumes are a feature.

## Hard rules

**Money is `Decimal`, never `float`.** Quantities too — fractional shares are
real. Store as `NUMERIC` in Postgres.

**All datetimes are timezone-aware UTC.** Convert at the edges only. Market dates
are separate from timestamps; use `date` for EOD prices and settlement.

**The ledger is append-only.** Corrections are new reversing entries, never
updates or deletes. Positions, cost basis, valuations, and P&L are always derived
from the full transaction history, never stored as mutable state. Materialised
tables are caches and must be safely rebuildable from scratch.

**Return figures state their method.** Never show a bare percentage. Annualised
money-weighted return, simple return, and capital-only return are different
numbers and must be labelled as such in both the API and the UI.

**LLMs never produce numbers.** Any figure shown to the user comes from
deterministic Python. Models receive a computed table plus text, and return
structured JSON (narrative, ranking, categorisation) validated against a Pydantic
schema. A model output that fails validation is discarded, not repaired by regex.

**Prefer APIs over scraping.** If a scraper is genuinely necessary it goes behind
the same provider interface and runs in an isolated subprocess so its failures
degrade gracefully.

**Every external call goes through the shared rate-limited client and the quota
ledger.** No feature creates its own `httpx.AsyncClient`.

**Suggestions are persisted with their inputs.** A suggestion row stores the
computed signal snapshot, the model output, and a state
(`new` / `accepted` / `dismissed`). This is the dataset for evaluating decision
quality later — never discard the inputs.

## Tax and reporting

UK jurisdiction. Capital gains use HMRC share identification rules in order:
same-day, then the 30-day bed-and-breakfast rule, then the Section 104 pool.
These live in a tax rules feature, not in the engine. Do not simplify to FIFO or
average cost "for now" — the whole point of the append-only ledger is to make
these computable. Tax year runs 6 April to 5 April and must be configurable.

## Conventions

- Async throughout. No sync DB calls in request or job paths.
- Pydantic models for every external boundary: API request/response, provider
  responses, model outputs, feature config.
- Interfaces are `typing.Protocol`, not ABCs.
- Alembic migration for every schema change, in the same commit.
- Config via environment variables loaded into a typed settings object. No
  secrets in code, no secrets in test fixtures.
- Fail loudly at startup. A misconfigured feature raises rather than silently
  disabling itself. Log the resolved feature and provider list on boot.

## Testing

- Every feature gets tests against a fake `AppContext`. No network in unit tests.
- Provider integrations use recorded fixtures, not live calls.
- Cost basis, IRR, and tax logic need property-based tests (`hypothesis`) plus
  worked examples as golden cases — HMRC guidance for CGT, hand-checked
  spreadsheets for return attribution.
- Valuation series needs a rebuild-equivalence test: incremental recompute must
  match a from-scratch rebuild exactly.
- Run `ruff check`, `ruff format --check`, and `pytest` before proposing a commit.

## Working with me

I'm a Python developer comfortable with packaging, build tooling, and CI/CD.
Skip explanations of standard library behaviour or basic async.

- Ask before adding a dependency.
- Ask before introducing a new architectural layer, a message queue, or splitting anything into a separate service.
- Push back if a change violates the boundary rule, the append-only ledger, or the quota discipline, even if I asked for it.
- Prefer editing existing files over creating new ones.
- Small, reviewable changes. One concern per commit.
- Work is tracked in GitHub issues; each is prefixed with a story ID and states its own acceptance criteria. Do not start work not covered by an issue

## Not in scope

This is a decision-support tool for personal use, not a regulated advice product
and not an execution platform. Nothing in this codebase places orders. Suggestion
copy should describe signals and observations, not instruct.