---
name: quant
description: Quantitative analytics implementation for this portfolio tracker. Use when implementing, testing, or reviewing any computed metric: simple/capital-only/total return, money-weighted return (IRR/XIRR), annualisation, return attribution (capital, income, currency), benchmark comparison, dividend yield, portfolio weights, drawdown, volatility, momentum, correlation, or roundup quant signals (PT-027, PT-031, PT-032, PT-039, PT-040, PT-043).
---

# Quant

How this project defines, computes, and tests numbers derived from the ledger
and from prices. This is an implementation discipline, not a trading persona.
Nothing here recommends a trade.

## Implementation state

Nothing here exists yet. `core/performance.py` is planned (PT-031 attribution,
PT-032 IRR), along with benchmark comparison (PT-040) and roundup signals as
`RoundupHook`s (PT-043). The issues are the spec. Inputs come from the
`portfolio-accounting` model (positions, flows) and from `market-data` (cached
prices and FX with staleness).

## Who computes what

- **Production figures** come only from deterministic Python in the
  application. No figure shown to the user is computed by a model (root
  `CLAUDE.md`, invariant 8).
- **You, Claude**, reason about definitions and derive expected values for
  tests. Derive them independently of the code under test: exact arithmetic
  with `fractions.Fraction`, closed forms, or hand working shown in a comment.
  Never run the implementation and paste its output in as the expected value.
- **LLM narration** (PT-044) receives finished signals by id and may only
  refer to them. It never re-derives, rounds, or combines them.

## Project conventions

| Topic | Rule |
|---|---|
| Number type | `Decimal` for every return, ratio, and amount. Use `Decimal.ln()`, `.exp()`, `.sqrt()`, and `**` with a local `decimal.localcontext()` at raised precision (for example 40 digits). Quantize only at the API/persistence edge. |
| Float / numpy | Not in production maths unless you ask first. PT-032 mentions `numpy-financial`, but it is float-based and conflicts with the Decimal invariant, so prefer the Decimal bisection solver it also allows. Statistics such as volatility and correlation are not money, but no float exemption has been agreed for them either: ask. |
| Method labels | Every return carries its method as data (PT-032). A bare number is a bug. Suggested identifiers: `money_weighted_annualised`, `money_weighted_period`, `simple`, `capital_only`. Agree the final names in PT-032. |
| Day count | Actual/365 for IRR exponents and annualisation (Excel XIRR / Sharesight convention). |
| Annualisation | `(1 + R)^(365/days) − 1`, applied only when the period is at least 365 days. Shorter periods are reported unannualised, with the reason stated (PT-032). |
| Sign convention for IRR | Investor's view: money in (deposits, opening value) is negative, money out (withdrawals, closing value) is positive. |
| Rounding | Full precision internally. Totals are computed from unrounded parts. Displayed parts may not sum to a displayed total, and that is correct. |
| Missing data | Never fill with zero or a fabricated value. Unpriced holdings are excluded from weights and totals, with the exclusion reported. A metric without enough observations returns an explicit insufficient-data result (PT-043). |
| Metadata | Every signal returns its value, window, and observation count (PT-043). Every return returns its method, period, and whether it is annualised. |

## The perimeter decides what a cash flow is

Before computing any return, decide what is inside the portfolio. With cash
accounts tracked (PT-030):

- **External flows** are deposits, withdrawals, and opening balances (treated
  as contributions at their as-at date). Nothing else is a flow.
- Buys, sells, dividends, interest, and fees are **internal**. They move value
  between instruments, or into value, and must not appear as IRR flows.
- At **holding level** (no cash perimeter), buys are contributions and sells
  and dividends are distributions.

Mixing the two perimeters, for example treating a dividend as a flow while
also counting it in the cash balance, double-counts income. State the
perimeter in code and tests.

## Metrics

Each metric's meaning, inputs, assumptions, common mistakes, tests, and worked
examples are in `references/metrics.md`:

- simple return
- capital-only return
- total return and attribution
- money-weighted return / XIRR
- annualisation
- time-weighted return (not planned)
- benchmark
- dividend yield
- weights
- drawdown
- volatility
- momentum
- correlation

Read the relevant section before implementing or reviewing one.

## IRR solver requirements (PT-032)

- Solve `NPV(r) = Σ CFᵢ · (1+r)^(−tᵢ/365) = 0` for `r > −1`, where `tᵢ` is the
  number of days since the first flow.
- Use bisection over a bounded bracket in Decimal, with a tolerance and an
  iteration cap. On non-convergence, return an explicit failure, never the
  last iterate.
- Handle these cases explicitly:
  - **no sign change** (all flows one sign): no IRR exists, so return a typed
    "undefined" result;
  - **total loss** (closing value 0 and no positive flows): r = −100%, set
    directly, because NPV is unbounded near −1;
  - **multiple sign changes**: there may be several roots. Check by scanning
    the bracket for multiple sign changes of NPV. If more than one root
    exists, report non-unique rather than returning one silently;
  - **flows on the final day**: their exponent is 0, which is valid;
  - **a single flow plus a closing value**: the closed form
    `(V/C)^(365/days) − 1` must match the solver.

## Testing

- **Golden cases:** hand-checked cases from `references/metrics.md`, plus the
  PT-031 multi-currency worked example built in a spreadsheet. Cite the source
  in a comment.
- **Property tests (`hypothesis`):**
  - attribution components sum to the total exactly, when currency is
    defined as the residual;
  - IRR at the returned rate gives |NPV| ≤ tolerance;
  - scaling every flow by k > 0 leaves IRR unchanged;
  - shifting every date by a constant leaves IRR unchanged;
  - weights of priced holdings sum to 1 within quantization;
  - a constant price series has zero volatility and zero drawdown.
- **Boundary cases (required by PT-032):** no flows, a single flow, flows on
  the final day, a total loss, and periods of 364, 365, and 366 days.

For a final pass, run the `financial-correctness-review` skill.
