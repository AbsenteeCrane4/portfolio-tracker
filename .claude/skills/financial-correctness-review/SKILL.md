---
name: financial-correctness-review
description: Structured review for financial correctness in this portfolio tracker. Use before considering any change complete that touches money, quantities, the ledger, positions, cost basis, valuations, returns, tax matching, income, market data, FX, or LLM-facing figures, and when reviewing such a PR or diff. Produces a findings list, not a style review.
---

# Financial correctness review

The question to answer for every figure the change touches:

> **Can I prove this result is derived from the correct source data under the
> correct economic definition?**

"The code looks reasonable" is not a pass. A finding needs a concrete failure:
these inputs give this wrong output.

Definitions live in the domain skills, so don't restate them here:

- `portfolio-accounting` covers transaction semantics, cost basis, and
  multi-currency;
- `quant` covers returns, IRR, attribution, and statistics;
- `uk-tax` covers matching, tax years, and income classification;
- `market-data` covers the cache, quota, staleness, and provenance.

## Procedure

1. **Inventory.** List every figure the change creates, alters, or exposes:
   stored columns, API fields, report columns, signals. For each, write its
   definition in one line, including its unit and currency.
2. **Trace provenance.** For each figure, trace back to source records
   (`transactions`, `prices`, `fx_rates`). If a value comes from anywhere else,
   it is a finding: a mutable column, a model output, a constant, a
   frontend-side calculation, or a provider response not yet cached.
3. **Run the checklist below.** Check only the sections relevant to the
   change, but read the whole diff for each one.
4. **Audit the tests.** Is every invariant the change relies on tested? Were
   the expected values derived independently of the implementation?
5. **Construct a counter-example** for anything doubtful: a minimal ledger or
   price series that would expose the bug. Prefer turning it into a test over
   arguing.
6. **Report** in the format at the end.

## Checklist

### Data

- [ ] Money, quantities, prices, rates, and returns are `Decimal`. There is no
      `float()`, `round()` on floats, `/` on ints producing float, numpy
      without agreement, `pytest.approx` on money, or `response.json()` on a
      provider body.
- [ ] New columns use `Money` / `Quantity` from `core/db.py`. The precision is
      enough, and values are quantized in Python before persisting so that
      Postgres doesn't round silently.
- [ ] Rounding happens only at the presentation edge. Totals are computed from
      unrounded parts.
- [ ] Every amount has a known currency. Conversions name their direction
      (`quote per base`), and GBX vs GBP is handled.
- [ ] Datetimes are UTC-aware. Market, trade, settlement, pay, and ex dates
      are `date`. No market date is derived from a UTC timestamp.
- [ ] Trade date drives positions and tax. Using settlement date anywhere is
      intentional and justified.
- [ ] Missing data stays missing. There is no `or 0`, no `.get(x, 0)` on
      prices, and no `fillna`. Carry-forward happens only at read time and is
      flagged.

### Ledger

- [ ] No `UPDATE` or `DELETE` path to `transactions`, including ORM attribute
      assignment followed by a flush, and bulk operations.
- [ ] Corrections use `reverses_id`, and invalidation starts at the
      **original** trade date.
- [ ] Re-import is idempotent through `(source, external_id)` or the PT-024
      fingerprint.
- [ ] No derived figure is stored as source of truth. Any new materialised
      table is droppable and rebuildable.
- [ ] Replay order is total and deterministic, with a stable tie-break.

### Positions and cost basis

- [ ] Cost allocation on disposal goes through `TaxRules`. There is no FIFO or
      average cost in core.
- [ ] Partial sells allocate cost proportionally from the right pool. Closed
      positions keep their realised gain.
- [ ] Fees are capitalised on buys and deducted from proceeds on sells, and
      never netted into price.
- [ ] Splits and consolidations change quantity only. Quantity and price use
      the same split basis on dates before the split.
- [ ] A DRP counts as income once and adds one acquisition. Residual cash is
      booked.
- [ ] Multi-currency cost is kept in trade and base currency at the
      transaction's rate. Valuation uses the daily rate.
- [ ] Transfers, wrappers, and fund events are not silently assumed (they are
      not modelled).

### Performance

- [ ] Every return carries its method as data. No bare percentages in the API
      or the UI.
- [ ] The perimeter is explicit. IRR flows are external flows only, with no
      buys or dividends when cash is tracked.
- [ ] Day count is Actual/365. Periods under 365 days are unannualised, with a
      reason.
- [ ] The IRR solver handles no sign change, total loss, multiple roots, and
      non-convergence by returning a typed result. It never returns a
      plausible wrong number.
- [ ] Attribution components sum exactly, with the currency convention named.
- [ ] The benchmark uses the same method and the same flow timing.
      Statistics use only observed data, with the observation count reported.

### Tax

- [ ] Matching order is same-day, then 30-day (D+1 to D+30, earliest first),
      then Section 104. Matched acquisitions stay out of the pool.
- [ ] Disposals in the last 30 days are provisional, and later acquisitions
      trigger recompute.
- [ ] Tax-year boundaries come from `Settings`, with 5 and 6 April tested.
- [ ] Each foreign leg is converted at its own transaction-date rate. The pool
      is in GBP.
- [ ] Instrument applicability is handled, or explicitly out of scope: exempt
      instruments, wrappers, fund types.
- [ ] UK vs foreign income is classified by issuer, not exchange or currency.
- [ ] Year-specific figures live in `Settings`, with a dated source.

### Market data

- [ ] Each call has a quota `reserve()` first, goes through the shared client,
      and has bounded retries that each consume quota.
- [ ] Exhaustion stops cleanly. Partial batches are saved, and malformed
      responses write nothing.
- [ ] Rows carry `source` and `fetched_at`. Source choice under conflict is
      deterministic.
- [ ] Price-dependent API values carry the price date and staleness. Unpriced
      holdings are excluded and reported, never zero.
- [ ] Price revisions and new FX rates invalidate valuations.

### AI

- [ ] No model calculates, rounds, converts, or originates a figure. Shown
      numbers come from the computed inputs.
- [ ] Model output is validated by a Pydantic schema. Invalid output is
      discarded, retried once, then falls back to raw signals (PT-044). There
      is no regex or coercion repair.
- [ ] Observations that reference unknown signal or article ids are rejected.
- [ ] Suggestion rows store the signal snapshot, the prompt, the model name,
      and the output (PT-044, PT-045). Copy describes, never instructs.

### Testing

- [ ] Golden cases come with cited sources (HMRC example, spreadsheet, or hand
      working). Expected values were not produced by the code under test.
- [ ] `hypothesis` properties cover the invariants touched: conservation,
      reversal neutrality, incremental equals full rebuild.
- [ ] Boundary and failure cases are tested, not just the happy path.
- [ ] Valuation changes include or keep the rebuild-equivalence test exact.
- [ ] No network. Fixtures are scrubbed.

## Report format

```
Financial correctness review: <change / PR>

Figures in scope: <list with one-line definitions>

Findings (most severe first):
1. [blocker|major|minor] <file:line> — <defect>
   Counter-example: <inputs> → <wrong output> (expected <right output>)
   Fix: <specific change or missing test>

Unverified: <anything you could not prove, and what would prove it>
Verdict: pass | pass with follow-ups | fail
```

A **blocker** breaks a root `CLAUDE.md` invariant or produces a wrong
user-visible figure. Don't call a change complete while a blocker is open.
