---
name: uk-tax
description: UK tax logic for this portfolio tracker. Use when implementing, testing, or reviewing HMRC share identification (same-day, 30-day bed-and-breakfast, Section 104 pool), the TaxRules interface, tax-year boundaries, allowable costs, foreign-currency disposals, corporate actions in the pool, dividend/interest income classification, or the taxable income, realised CGT, and unrealised CGT reports (PT-012, PT-036, PT-037, PT-038).
---

# UK tax

How this project computes UK capital gains and taxable income. It is a
calculation and reporting aid for one UK-resident individual. It does not
compute tax liability and does not give advice.

## Implementation state

Nothing tax-related exists yet. Only `Settings.tax_year_start_month` and
`Settings.tax_year_start_day` are real; they default to 6 April and are
validated in `core/settings.py`.

| Piece | Planned location | Issue |
|---|---|---|
| `TaxRules` Protocol | `interfaces/tax_rules.py` | PT-005 |
| HMRC matching implementation | a feature package implementing `TaxRules` | PT-012 |
| Taxable income report | `features/reports/`, via the `Report` interface | PT-036 |
| Realised CGT report | `features/reports/` | PT-037 |
| Unrealised CGT report | `features/reports/` | PT-038 |

## The boundary

- The core cost-basis engine (`core/positions.py`, PT-011) calls `TaxRules`
  to allocate cost to disposals. It contains no HMRC logic: no "30 days", no
  "same day", no pool arithmetic.
- `wiring.py` injects the HMRC implementation. Core never imports it.
- Reports consume the engine's output and the `TaxRules` breakdown. They never
  re-implement matching.
- Never fall back to FIFO or average cost, not even temporarily.

## Three layers: keep them apart

Every rule in `references/hmrc-rules.md` is stated as:

1. **the law or HMRC guidance**, with a source;
2. **this project's implementation**;
3. **open assumptions** that still need confirmation.

When you add or change tax behaviour, keep the same split, in code comments
and in the PR. Don't present an assumption as law. Don't encode a year-specific
figure (exempt amount, rates) as a constant: it lives in `Settings`, with a
dated comment.

## Matching procedure (project implementation)

Run it per instrument. The instrument stands in for "same class of shares in
the same company".

1. **Aggregate by day.** All acquisitions on a day are one acquisition, and
   all disposals on a day are one disposal (TCGA 1992 s105).
2. **Same-day.** Match each day's disposal against that day's acquisitions.
   This has absolute priority, including over an earlier disposal's 30-day
   claim on the same acquisition (CG51560).
3. **30-day.** Match the remaining disposal quantity against acquisitions in
   the window D+1 to D+30, earliest first, using only acquisition quantity not
   already matched (s106A).
4. **Section 104.** Take the remainder from the pool as it stands at D.
   Allocated cost is `pool_cost × q / pool_qty`.
5. **Pool membership.** Acquisitions, or the parts of them, matched under
   steps 2 or 3 never enter the pool. Everything else enters the pool on its
   acquisition date.
6. **Output.** Each disposal produces a breakdown listing, per rule, the
   quantity, the cost, and which acquisitions were used. The breakdown is
   user-facing and must be checkable by hand (PT-012, PT-037).

Consequences you must handle:

- **Gains are provisional for 30 days.** A disposal's gain can change until D+30
  passes. The realised report must mark disposals inside that window as
  provisional, and recomputation must be triggered by later acquisitions.
- **Cross-year matching.** A disposal on 1 April can match an acquisition on 20
  April. The gain belongs to the disposal's tax year, but depends on the next
  year's data.
- **Hypothetical disposals** (PT-038, "what if I sold today"): no future
  acquisitions are known, so model them with same-day and pool matching only,
  and say so on the estimate.

## Values and conversions

- **Cost.** Allowable acquisition cost is the price plus incidental costs:
  commission and stamp duty/SDRT. Disposal costs reduce proceeds (s38,
  PT-037). Fees are stored separately on each transaction (PT-009), so use
  them; never infer fees from price.
- **Foreign currency.** Cost is converted to GBP at the acquisition date's
  rate, and proceeds at the disposal date's rate. Use the rate stored on each
  transaction (PT-009). The chargeable gain is the GBP difference. PT-037's
  "currency gain shown separately" is an **informational** split; it is not a
  separate chargeable gain.
- **Pool currency.** The Section 104 pool is kept in GBP. The engine's
  trade-currency cost basis (PT-011) serves performance attribution, not tax.
  Never mix the two.

## Corporate actions in the pool

- **Splits and consolidations** change pool quantity, leave pool cost
  unchanged, and create no disposal (PT-012, PT-028). If a split falls between
  a disposal and a 30-day acquisition, compare quantities on the same basis.
- **DRP:** the reinvested dividend is taxable income, and the shares bought
  are a normal acquisition entering the pool (PT-029). Inside a 30-day window,
  a DRP acquisition **does** match an earlier disposal.
- **Cash in lieu of fractions** on a consolidation is a part disposal, unless
  the small-distribution treatment applies (s122). This is an open item, see
  the reference.

## Income (PT-036)

- Dividends, distributions, and interest go into the selected period, by pay
  date. The default period is the current tax year.
- **UK vs foreign follows the issuer's or fund's residence**, not the listing
  exchange or the trade currency. An Irish-domiciled ETF on the LSE, priced in
  GBP, is foreign. The instrument registry (PT-008) has no domicile field,
  only an ISIN "where known". ISIN country prefixes are a hint, not proof. Ask
  before inferring domicile.
- Foreign income shows gross, withholding tax, and GBP at the pay-date rate.

## Tax year

- Tax year N–(N+1) runs from 6 April N to 5 April N+1, by default. Always
  derive the boundary from `Settings`, never from a literal date.
- Use a single helper, for example `tax_year_for(date)`, everywhere.
- Test 5 April vs 6 April, plus a non-default configured start.

## Not modelled yet (ask before depending on any)

- ISA and SIPP wrappers. Gains inside them are exempt, and holdings in them
  must not join the taxable pool.
- Accumulation units and notional distributions, which add to cost.
- Equalisation.
- Offshore non-reporting funds, whose gains are taxed as income.
- Bond-fund interest distributions.
- Gilts and qualifying corporate bonds, which are CGT-exempt.
- Negligible-value claims.
- Losses brought forward.
- Tax liability and rates (out of scope; only the exempt-amount comparison is
  in PT-037).

## Testing

- **Golden cases** come from HMRC worked examples (HS284, CG manual), each
  with a comment citing the document and example. `references/examples.md`
  has hand-checked project cases.
- **Property tests (`hypothesis`):**
  - total matched quantity equals total disposed quantity (PT-012);
  - once every 30-day window has closed, pool quantity equals the physical
    holding quantity;
  - pool cost is never negative;
  - splits leave pool cost unchanged;
  - reordering same-day transactions doesn't change any result.
- **Required edge cases:**
  - same-day buy and sell;
  - a 30-day match crossing a tax-year boundary;
  - a partial 30-day match plus a pool remainder;
  - a disposal still inside its provisional window;
  - a split between disposal and reacquisition;
  - a DRP inside a 30-day window;
  - a foreign disposal with different acquisition and disposal rates;
  - 5 and 6 April boundaries.

For a final pass, run the `financial-correctness-review` skill.
