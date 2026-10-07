# CLAUDE.md

A self-hosted, single-user portfolio tracker modelled on **Sharesight**, plus a
market-roundup/suggestion engine Sharesight has no equivalent of. UK tax rules,
GBP base currency, free-tier end-of-day price data. Single-developer project:
optimise for clarity and shipping speed over generality.

Sharesight is the functional reference. For questions about portfolio
behaviour, reporting, or terminology, do what Sharesight does unless this file
or `docs/` says otherwise.

This is a decision-support tool for personal use. It is not a regulated advice
product and not an execution platform: nothing in this codebase places orders.

## Where to look

| Need | Source |
|---|---|
| Backlog, scope of the current task, acceptance criteria | GitHub issues (authoritative; `USER_STORIES.md` cited in issue footers is not in the repo) |
| v1/v2 product scope, out-of-scope list | [docs/product.md](docs/product.md) |
| Package layout, core vs feature, `AppContext`, valuation design | [docs/architecture.md](docs/architecture.md) |
| Provider free tiers (volatile snapshot) | [docs/market-data.md](docs/market-data.md) |
| UI layout | `docs/design/Portfolio Tracker UI.html` |
| Local setup, migrations, DB-backed tests | [README.md](README.md) |

Area-specific rules in `.claude/rules/` load automatically when you work on
matching files: frontend, market data, tax, roundup/LLM, and tests.

Domain skills in `.claude/skills/` hold the specialist procedures and worked
examples. Use them for financial work:

- `portfolio-accounting`: ledger, positions, cost basis, corporate actions,
  cash, FX on transactions;
- `quant`: returns, IRR, attribution, benchmarks, signals;
- `uk-tax`: HMRC matching, tax years, income classification, CGT and income
  reports;
- `market-data`: providers, quota, cache, backfill, staleness;
- `financial-correctness-review`: run before calling any financial change
  done.

## Stack

Python 3.12, FastAPI, SQLAlchemy 2.0 async (asyncpg), Alembic, Pydantic v2 /
pydantic-settings. Postgres on Supabase, accessed only through SQLAlchemy,
never the Supabase client. Next.js frontend that talks to the API over HTTP
only. Tooling: `uv`, `ruff`, `mypy --strict`, `pytest` + `pytest-asyncio`.
Deploy: API and scheduler on Fly.io or Railway, frontend on Vercel. Vercel
cannot host the scheduled worker.

## Invariants

These are non-negotiable. Push back if a change would break one, even if I
asked for it, and propose an alternative. Never weaken one "for now".

1. **Decimal for money and quantities, never `float`.** Fractional shares are
   real. Use the `Money` / `Quantity` annotations from `core/db.py` (`NUMERIC`
   in Postgres). Never let a value pass through `float` on the way in. Parse
   provider and CSV input straight to `Decimal`.
2. **Timezone-aware UTC datetimes.** Convert at the edges only. Market,
   settlement, and EOD dates are `date`, not `datetime`.
3. **The ledger is append-only.** Never update or delete ledger rows.
   Corrections are new reversing entries. Corporate actions and DRP
   reinvestments are recorded as ledger entries, and their effect on positions
   is derived.
4. **Derived state is a rebuildable cache.** Positions, cost basis,
   valuations, returns, and P&L are computed deterministically from the ledger
   plus cached market data. They are never mutable state of record. Every
   materialised table must be rebuildable from scratch, and an incremental
   recompute must equal a full rebuild exactly. Source records are the ledger,
   `prices`, `fx_rates`, and suggestions. Everything else is derived.
5. **The valuation series is materialised, not recomputed per request.**
   `portfolio_valuations` is invalidated from the first affected date whenever
   any input changes: transaction, price, FX rate, or corporate action. It is
   never computed in the frontend.
6. **Missing data is never fabricated.** A failed fetch leaves a gap. No null
   written as zero, and no silent carry-forward. Any figure that relies on a
   price or FX rate from an earlier date is marked stale all the way from the
   database through the API to the UI. Unpriced holdings are shown explicitly
   and visibly excluded from totals, never valued at zero.
7. **Return figures state their method.** No bare percentages in the API or
   the UI. Annualised money-weighted (IRR), simple, and capital-only returns
   are different numbers. API responses carry the method as data, and the UI
   labels it.
8. **Deterministic code is the only source of figures.** An LLM never
   calculates, estimates, converts, rounds, or originates a user-visible
   number. Models receive values that are already computed, plus text, and
   return structured output (narrative, ranking, categorisation) validated
   against a Pydantic schema. Output that fails validation is discarded, never
   repaired.
9. **Every external call goes through the shared rate-limited client and the
   quota ledger.** This includes price, FX, news, and LLM APIs. No feature
   creates its own `httpx.AsyncClient`. Providers are never the system of
   record: market data is cached in Postgres permanently, and providers are
   asked only for gaps.
10. **Config comes only from `core/settings.py`.** Nothing else reads the
    environment, and `tests/test_layout.py` enforces this. Secrets are
    `SecretStr` and never appear in code, fixtures, logs, or error messages. A
    new key goes into `Settings` and `.env.example` in the same change.
    Misconfiguration fails loudly at startup. A feature never silently
    disables itself.
11. **Suggestions are persisted with their inputs.** Each one stores the
    signal snapshot, the model output, and its state (`new` / `accepted` /
    `dismissed`, plus `stale` when superseded, per PT-045). Rows are never
    deleted. Copy describes signals and observations. It never instructs.

## Architecture boundaries

The project is a modular monolith in one process. Details and rationale are in
[docs/architecture.md](docs/architecture.md). `tests/test_layout.py` enforces
the import rules.

- `core/` never imports `features/`. Core uses feature behaviour (price
  providers, tax matching rules) only through Protocols in `interfaces/`, which
  `wiring.py` injects.
- `features/` never imports `core.*` internals. If you are about to write
  `from portfolio.core.x import y` in a feature, expose it as an `AppContext`
  capability or an interface instead.
- `interfaces/` holds `typing.Protocol` definitions only. No ABCs, and no
  imports from `core`, `features`, or `api`.
- `wiring.py` is the only module that imports both `core` and `features`.
  Wiring is explicit constructor injection.
- `api/` routers stay thin: validate, delegate, serialise. No business logic.
- `AppContext` carries shared infrastructure (session factory, HTTP client,
  quota manager, settings) and typed capabilities. It is not a service locator.
  Give features typed attributes, not string-keyed lookups. A dependency only
  one feature needs is passed to that feature's constructor.
- Don't build a plugin registry, entry-point loading, or dynamic discovery
  until two real implementations of one interface compete.

## Conventions

- Async throughout. No sync DB or HTTP calls in request or job paths.
- Pydantic models sit at every external boundary: API requests and responses,
  provider responses, imported rows, LLM output, and feature config.
- Every schema change ships with an Alembic migration in the same commit, and
  the migration must both upgrade and downgrade. CI runs both directions.
- ORM models use `Base` from `core/db.py`.
- Imports are absolute. Fix lint and type errors rather than suppressing them.
  A suppression needs a specific code (`# type: ignore[code]`, `# noqa: XXX`)
  and a reason.
- Prefer editing existing files over creating new ones. Keep changes small,
  with one concern per commit.

## Testing

Mechanics are in `.claude/rules/testing.md`. The obligations:

- New behaviour ships with tests. Feature tests run against a fake
  `AppContext`. Tests never touch the network, and provider tests use
  recorded fixtures.
- Cost basis, IRR and return attribution, and tax matching each need
  `hypothesis` property tests plus golden cases: HMRC worked examples for CGT,
  hand-checked spreadsheets for return attribution.
- The valuation series needs a rebuild-equivalence test.
- Before every commit, run what CI runs: `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run mypy`, and `uv run pytest`. When you
  touch DB code, also run the DB-backed tests locally (see README).

## Issue workflow

Work is issue-driven. Each issue has a story ID (`PT-NNN`), acceptance
criteria, and a "Depends on" list.

- **Pick** one issue at a time. Take the lowest-numbered open issue whose
  "Depends on" issues are all closed, unless I name a different one. Priority
  labels don't reorder the queue unless I say so.
- **Scope:** the acceptance criteria define done. Work outside them goes into
  the PR description as a proposed follow-up, not into the branch. Don't start
  feature work that no issue covers. Something I ask for directly in the
  session (such as docs or instruction changes) needs no issue, but ask before
  committing it.

The loop for each issue:

1. `gh issue view <n>`. Read the acceptance criteria and check the
   dependencies are closed.
2. `git fetch`, `git checkout main`, `git pull`, then
   `gh issue develop <n> --name PT-NNN --base main --checkout`. This creates the
   branch and links it to the issue.
3. `git push -u origin PT-NNN` before any work.
4. Implement. Commit small and push regularly, and run the checks before each
   commit.
5. Open a PR into `main` titled `PT-NNN: <issue title>`. Its body contains
   `Closes #<n>`, how each acceptance criterion is met, and any notable
   decisions you made.
6. Merge with `gh pr merge --merge` once CI is green and I have approved.
   GitHub won't let me approve my own PR, so approval means my explicit
   go-ahead in the session or in a PR comment. Never merge with failing
   checks, never use `--admin`, and never disable a check.
7. Prune: `git checkout main`, `git pull`, `git branch -d PT-NNN` (`-d`, never
   `-D`), delete the remote branch, then `git fetch --prune`.
8. Go back to step 1 for the next issue.

When running in GitHub Actions (`.github/workflows/claude.yml`), that
workflow's appended prompt governs branching and commits. Its permissions are
read-only, so don't attempt to open or merge PRs there.

## Decide vs ask

**Decide yourself**, without asking: implementation details, naming, where a
file goes within the existing layout, how tests are organised, small refactors
in code you are already touching, and choosing between approaches that all
satisfy the acceptance criteria and the invariants. Record notable choices in
the PR description.

**Stop and ask** when:

- An issue is ambiguous in a way where the readings would produce different
  behaviour or data.
- A change would break an invariant, or the boundary rules.
- Product scope would change: a screen, report, or behaviour that no issue
  or `docs/product.md` covers.
- Authoritative sources conflict (issue vs this file vs docs vs wireframe) and
  the resolution isn't obvious. The invariants always win over the other
  sources. Flag the conflict rather than silently picking one.
- You want to add a dependency. `hypothesis` is the exception: the testing
  obligations already require it.
- An architectural change comes up: a new top-level package or layer, a
  separate service, a queue, an event bus, an extra worker, plugin
  infrastructure, or changing the shape of `AppContext` beyond what an issue
  specifies.
- An action is destructive or irreversible: a migration that alters or drops
  existing data, a force-push or history rewrite, deleting an unmerged branch,
  or anything touching the real Supabase database.
- The next issue is blocked or its dependencies are still open.

Don't ask about anything this file, `docs/`, or the code already answers. I'm
an experienced Python developer, so skip explanations of the standard library,
async basics, and tooling.
