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

# Market data guardrails

Load the `market-data` skill before changing anything in this area. It holds
the pipeline, failure handling, and the test list. These are the lines you
must never cross:

- No outbound call without a successful quota `reserve()` and the shared
  client from `AppContext`. Retries are bounded and each one reserves quota.
- Never write a null, zero, or carried-forward value into `prices` or
  `fx_rates`. Gaps stay gaps.
- Don't call `response.json()` on provider bodies, because it parses numbers
  as float. See the skill for safe Decimal parsing.
- No Yahoo Finance unofficial endpoints, and no websocket or live-tick
  designs.
- Tests replay scrubbed, recorded fixtures. They never hit the network.
