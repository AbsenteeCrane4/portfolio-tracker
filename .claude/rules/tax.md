---
paths:
  - "src/portfolio/**/*tax*"
  - "src/portfolio/**/tax*/**"
  - "src/portfolio/features/reports/**"
  - "src/portfolio/core/positions.py"
  - "tests/**/*tax*"
  - "tests/**/*cgt*"
---

# Tax rules

The jurisdiction is the UK. Capital gains use HMRC share identification rules,
applied in this order:

1. same-day acquisitions,
2. acquisitions in the following 30 days (bed and breakfast),
3. the Section 104 pool.

- **Location:** this logic lives in a tax-rules feature that implements
  `interfaces/tax_rules.py`. The core cost-basis engine consumes it through
  that Protocol and contains no HMRC-specific logic itself.
- **No shortcuts:** never simplify to FIFO or average cost, not even "for
  now". The append-only ledger exists so that these rules can be computed.
- **Tax year:** 6 April to 5 April by default, configurable through
  `TAX_YEAR_START_MONTH` / `TAX_YEAR_START_DAY` in `Settings`. Never hard-code
  the boundary.
- **Corporate actions:** splits, consolidations, and reinvestments adjust the
  pool. They do not create disposals.
- **Breakdowns are user-facing.** Each disposal records which rule matched
  which quantity, at what cost, so the arithmetic can be checked by hand.
- **Applicability is a tax-rule decision.** The engine must not assume every
  disposal of every instrument is chargeable. Which instruments and holdings
  fall in scope (cash accounts, for example) is decided behind the tax-rules
  boundary. Where an issue leaves this unspecified, ask rather than guess.
- **Income reports** split dividends, distributions, and interest into UK and
  foreign.
- **Tests:** golden cases come from HMRC worked examples, each with a comment
  citing its source. Property tests cover conservation, for example that the
  total matched quantity equals the total disposed quantity.
