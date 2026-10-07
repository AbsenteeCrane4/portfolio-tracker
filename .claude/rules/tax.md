---
paths:
  - "src/portfolio/**/*tax*"
  - "src/portfolio/**/tax*/**"
  - "src/portfolio/features/reports/**"
  - "src/portfolio/core/positions.py"
  - "tests/**/*tax*"
  - "tests/**/*cgt*"
---

# Tax guardrails

Load the `uk-tax` skill before changing anything in this area. It holds the
matching procedure, the HMRC sources, and worked examples. These are the lines
you must never cross:

- HMRC matching (same-day, then 30-day, then Section 104) lives only behind
  `interfaces/tax_rules.py`. The core engine contains no HMRC logic.
- Never FIFO or average cost, not even "for now".
- Tax-year boundaries and year-specific figures come from `Settings`, never
  literals.
- Applicability that isn't modelled (wrappers, exempt instruments, fund
  types): ask, don't assume.
