---
paths:
  - "src/portfolio/features/providers/**"
  - "src/portfolio/interfaces/price_provider.py"
  - "src/portfolio/interfaces/fx_provider.py"
  - "src/portfolio/interfaces/news_provider.py"
  - "src/portfolio/core/quota.py"
  - "src/portfolio/core/scheduling.py"
  - "src/portfolio/core/valuation.py"
  - "tests/**/*provider*"
  - "tests/**/*quota*"
---

# Market data rules

Background and the provider snapshot are in `docs/market-data.md`. The rules:

- **Spend quota deliberately.** Each outbound call goes through the shared
  client and is recorded in the quota ledger. When the budget is exhausted,
  stop cleanly and leave the remaining work for the next window. Retries are
  bounded and still count against the budget, so they can never become a
  retry storm.
- **Ask only for gaps.** Check the `prices` / `fx_rates` cache first, and
  never re-fetch what is already stored. Batch symbols into the fewest
  requests the provider allows. There is one job per provider, not one per
  holding.
- **Keep daily polling and backfill apart.** Backfill is a separate, resumable
  job on a lower-priority quota allocation, and it must never starve the daily
  poll.
- **Failures leave gaps.** Never write a null, zero, or carried-forward value
  in place of a missing one.
- **Responses are validated.** Every provider response is parsed into a
  Pydantic model, with prices going straight to `Decimal`. A response that
  fails validation counts as a failed fetch. It is never patched up.
- **Provider code stays behind the interface.** Provider-specific behaviour
  stays inside its feature package, and core sees only the Protocol. Quota
  figures come from `Settings`, never from constants in provider code.
- **Source selection is deterministic.** When several sources cover the same
  `(instrument, date)`, valuation picks one by configured precedence, never by
  arrival order. Rebuild equivalence depends on this.
- **No Yahoo Finance unofficial endpoints**, and no websockets or live-tick
  designs. Scraping is a last resort, behind the provider interface and in an
  isolated subprocess.
- **Tests replay recorded fixtures**, with credentials and account identifiers
  scrubbed. Never call a live endpoint from a test.
