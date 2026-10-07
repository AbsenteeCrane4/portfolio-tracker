# Metric reference

Each section covers the metric's meaning, inputs, assumptions, common
mistakes, tests, and worked examples. Notation:

- `V₀` and `V₁` are the values at the start and end of the period, in base
  currency;
- `F` is the net external flows (contributions positive, from the
  portfolio's view);
- `I` is income (dividends and interest, gross);
- `C` is cost basis.

All arithmetic is in `Decimal`.

---

## Simple return

- **Meaning:** total gain relative to the money committed, ignoring timing.
- **Holding level:** `(MV₁ + proceeds + I − C_total) / C_total`, where
  `C_total` is the total cost of all acquisitions in the period.
- **Portfolio level:** the gain is `V₁ − V₀ − F`. The denominator is
  **undecided**. Candidates are `V₀ + contributions` or average capital
  employed. PT-032 must pick one and put it in the method metadata.
- **Assumptions:** none about timing, which is exactly why it differs from
  money-weighted return when flows are uneven.
- **Mistakes:**
  - `(V₁ − V₀) / V₀`, which counts deposits as gains;
  - dividing by the current cost after partial sells, which shrinks the
    denominator.
- **Tests:** with no flows and no income it equals `V₁/V₀ − 1`. Check the
  quadratic example below, where simple and money-weighted diverge.

## Capital-only return

- **Meaning:** price and currency movement only, excluding income.
- **Formula:** the simple-return formula with `I` removed.
- **Mistakes:**
  - treating DRP-acquired shares' cost as income, or leaving it out of cost;
  - a split changing the result (it must not).
- **Tests:** an instrument with dividends but a flat price has capital-only
  return 0, while total return is above 0.

## Total return and attribution (PT-031)

- **Meaning:** total gain split into capital, income, and currency, each in
  base currency. Realised and unrealised are reported separately.
- **Inputs:** cost in trade and base currency (at the transaction's rate),
  market value in trade currency, daily FX, income, and realised proceeds.
- **Definitions:**
  - `total_base = MV_base + proceeds_base + income_base − cost_base`
  - `capital_trade = MV_trade + proceeds_trade − cost_trade`
  - `capital_base` = `capital_trade` converted using **convention A** (the
    current rate) or **convention B** (the acquisition rate). Undecided, so
    pick one in PT-031 and label it.
  - `currency = total_base − capital_base − income_base`. As a residual it
    makes the sum exact.
- **Mistakes:**
  - computing currency independently and then needing a tolerance. The
    PT-031 criterion allows a tolerance, but a residual definition is exact;
  - converting income at the valuation-date rate instead of the pay-date
    rate;
  - closed positions contributing unrealised amounts (they contribute
    realised only).
- **Tests:**
  - components sum exactly;
  - a GBP-only portfolio has currency gain exactly 0;
  - a flat price with a moving FX rate gives capital exactly 0;
  - the worked example: `portfolio-accounting/references/examples.md` §2,
    where A gives capital 153.0769…, currency −61.5692…, and B gives capital
    159.20, currency −67.6923…

## Money-weighted return / XIRR (PT-032)

- **Meaning:** the single constant rate that makes the dated flows and the
  closing value net to zero. It rewards or penalises the timing of the
  investor's own deposits.
- **Inputs:** `V₀` at the start as a negative flow, every external flow with
  its date, and `V₁` at the end as a positive flow.
- **Equation:** `Σ CFᵢ · (1+r)^(−tᵢ/365) = 0`, with `tᵢ` in days from the
  first flow (Actual/365).
- **Assumptions:** the perimeter is defined (see SKILL.md), flows are
  external only, and a solution exists and is unique.
- **Mistakes:**
  - including internal flows such as buys or dividends;
  - using `/12` monthly periods;
  - returning the last bisection iterate on failure;
  - silently picking one of two roots;
  - using a float solver.

### Worked examples (exact)

**One year, single flow.** Pay in −1000 on 2025-01-01, value 1100 on
2026-01-01 (365 days). Then `1100/1000 − 1`, so r = **10%**.

**Two years, two contributions.** Pay in −1000 on 2025-01-01 and −1000 on
2026-01-01, value 2310 on 2027-01-01 (365 and 730 days).

- In forward-value form with `x = 1+r`: `1000x² + 1000x − 2310 = 0`.
- So `x = (−1 + √10.24)/2 = 1.1`, and r = **10%** annualised.
- Simple return over contributions is (2310 − 2000)/2000 = **15.5%**,
  unannualised. Same money, different method: label both.

**Multiple roots.** Flows −1000 at year 0, +2300 at year 1, −1320 at year 2.

- This gives `−1000x² + 2300x − 1320 = 0`, so x = 1.1 or 1.2.
- Both **10% and 20%** solve it. The solver must report non-unique.

**Total loss.** Pay in −1000, value 0 at the end. r = −100%, a special case.

**No solution.** Every flow is the same sign, so return "undefined".

## Annualisation

- **Formula:** `(1+R)^(365/days) − 1`, applied only for `days ≥ 365`.
  Otherwise report the period figure, labelled unannualised, with a reason
  (PT-032).
- **Mistakes:**
  - annualising a 10-day return into an absurd number;
  - `R × 365/days` (simple scaling);
  - leap-year special-casing that conflicts with Actual/365.
- **Tests:** at 365 days the annualised value equals the period value. Check
  364 days (unannualised) and 366 days (annualised).

## Time-weighted return

This is **not planned**. Sharesight and this project use money-weighted
returns. It would chain sub-period returns between flows:
`Π(1 + Rₖ) − 1`. Don't add it without an issue.

## Benchmark (PT-040)

- **Meaning:** what the same money, at the same times, would have earned in
  the benchmark.
- **Method:** replay the portfolio's external flows as purchases and sales of
  benchmark units at that day's benchmark close. Then compute the
  benchmark's return **with the same method** as the portfolio's.
- **Chart:** index both series to 100 at the period start.
- **Mistakes:**
  - comparing the portfolio IRR against the benchmark's simple price change;
  - silently shortening the period when benchmark prices are missing. Report
    the gap instead (PT-040).
- **Tests:**
  - benchmark equal to a single held instrument, with all flows going into
    it, gives an identical return;
  - with no flows, the result reduces to the benchmark's own price return.

## Dividend yield (PT-027)

- **Yield on cost:** trailing-12-month dividends ÷ current cost basis.
- **Yield on value:** trailing-12-month dividends ÷ current market value.
- They must be labelled distinctly. If there is no price, yield on value is
  unpriced, not 0. If there is no dividend history, the result is absent, not
  0%.

## Weights (PT-039)

- **Formula:** `wᵢ = MVᵢ_base / Σ MV_base` over priced holdings, including
  cash as its own bucket.
- **Mistakes:**
  - including unpriced holdings at 0;
  - mixing currencies before conversion;
  - forcing Decimal rounding residue to make the sum exactly 100% by
    adjusting one bucket.
- **Tests:** the sum is 1 within the quantization step. Excluded holdings are
  listed.

## Drawdown (PT-043)

- **Formula:** `DD_t = P_t / max_{s≤t} P_s − 1`. Maximum drawdown is the
  minimum of `DD_t`, reported with its peak date and trough date.
- **Input:** a price series, or a flow-adjusted index. Never raw portfolio
  value, because a withdrawal looks like a drawdown.
- **Tests:**
  - a monotonic rising series has drawdown 0;
  - the series 100 → 50 → 100 has a drawdown of −50%.

## Volatility (PT-043)

- **Formula:** the sample standard deviation (n−1) of daily simple returns,
  `rᵢ = Pᵢ/Pᵢ₋₁ − 1`, between **consecutive observed closes**. Annualised
  with `√252`. That convention must be stated in the signal metadata.
- **Mistakes:**
  - computing returns across carried-forward days, which inserts fake zero
    returns and understates volatility;
  - using population (n) instead of sample (n−1);
  - too few observations. Return insufficient-data below the configured
    minimum.
- **Tests:**
  - a constant series has volatility 0;
  - a hand-computed 5-point series;
  - the observation count excludes gaps.

## Momentum (PT-043)

- **Formula:** `P_end / P_start − 1` over the window, using observed closes
  at or before each boundary, with the actual dates reported.
- If the start of the window predates the price history, the result is
  insufficient-data. Never shorten the window silently.

## Correlation (PT-043)

- **Formula:** Pearson correlation of daily returns on the **intersection** of
  dates where both series are observed. The observation count is reported.
- **Mistakes:** aligning by position instead of by date; filling one series'
  gaps.
- **Tests:**
  - a series with itself gives 1;
  - a series with its negation gives −1;
  - a series with a constant series is undefined, not 0.
