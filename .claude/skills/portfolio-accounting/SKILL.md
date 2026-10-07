---
name: portfolio-accounting
description: Ledger and accounting model for this portfolio tracker. Use when implementing or changing transactions, the append-only ledger, corrections/reversals, positions, cost basis, realised/unrealised gains, dividends, DRP/DRIP, splits/consolidations, opening balances, cash accounts, deposits/withdrawals, multi-currency or FX handling of transactions, or the valuation series (PT-008 to PT-013, PT-022, PT-027 to PT-030).
---

# Portfolio accounting

How this project turns an append-only transaction log into positions, cost
basis, gains, and cash. Root `CLAUDE.md` holds the invariants (Decimal, UTC,
append-only, rebuildable derived state). This skill explains how to apply them.

## Implementation state: check before relying on anything

Only `core/settings.py` and `core/db.py` exist today. Everything below is
planned and specified by issues. Before referencing a module, check it exists.
If it doesn't, the issue is the spec.

| Concept | Planned location | Issue |
|---|---|---|
| Instruments, aliases, resolution | `core/instruments.py` | PT-008 |
| `transactions` table, insert-only guard, `reverses_id` | `core/ledger.py` | PT-009 |
| Transaction API, reverse endpoint, over-sell validation | `api/` + ledger | PT-010 |
| `positions_as_of(date)`, cost basis, realised gain | `core/positions.py` | PT-011 |
| HMRC matching consumed by the engine | `interfaces/tax_rules.py` + feature | PT-012 (see `uk-tax` skill) |
| `opening_balance` | ledger + engine | PT-013 |
| `portfolio_valuations` | `core/valuation.py` | PT-022 |
| Dividends, splits/consolidations, DRP, cash accounts | ledger + engine | PT-027 to PT-030 |

Already real and to be reused: `Money` (`NUMERIC(20,8)`) and `Quantity`
(`NUMERIC(24,10)`) annotations, and `Base` with naming conventions, in
`core/db.py`. Base currency comes from `Settings.base_currency`.

## The model in one paragraph

The `transactions` table is the only source of truth for holdings. Each row is
an event on an instrument with a trade date. The engine replays rows in a
deterministic order and produces, for any date, per-instrument quantity, cost
basis (in trade currency and in base currency), and realised gain. Cash is an
instrument of type `cash`, one per currency. Valuations multiply derived
quantity by cached prices and FX rates. Every table derived from these
(positions, cost basis, `portfolio_valuations`) can be dropped and rebuilt.
Source tables (`transactions`, `prices`, `fx_rates`, suggestions) cannot.

## Transaction semantics

The PT-009 types are buy, sell, dividend, split, drp, deposit, withdrawal, fee,
and interest. PT-013 adds `opening_balance`. Each row stores fees and tax
withheld **separately**, never netted into price.

| Type | Quantity | Cost basis | Cash (if tracked) | Income | Realised | External flow |
|---|---|---|---|---|---|---|
| buy | +q | + (q·price + fees) | − (q·price + fees) | – | – | no |
| sell | −q | − cost allocated by TaxRules | + (q·price − fees) | – | proceeds − allocated cost | no |
| dividend | – | – | + (gross − withheld) | + gross | – | no |
| drp | + shares bought | + reinvested amount | + residual only | + gross | – | no |
| split / consolidation | × ratio | unchanged | cash in lieu, if any | – | see `uk-tax` | no |
| opening_balance | +q | + asserted cost | – | – | – | yes (contribution at as-at date) |
| deposit / withdrawal | – | – | ± amount | – | – | **yes** |
| fee | – | – | − amount | – | – | no |
| interest | – | – | + amount | + amount | – | no |

Rules that are easy to get wrong:

- **Store totals, not per-share figures.** Cost basis is a running total.
  Average cost is `total cost / quantity`, derived only for display. Rebuilding
  a total from a rounded per-share figure drifts.
- **Cost allocation on a sell is not decided by the engine.** PT-011 delegates
  it to `TaxRules`, so a sell's allocated cost follows same-day, 30-day, then
  Section 104 matching. The engine must never hard-code FIFO or average cost.
  Consequence: a sell's realised gain can change when an acquisition lands
  within the following 30 days (see the `uk-tax` skill).
- **Dividend income is the gross amount.** Withholding is recorded separately.
  Cash received is net of withholding.
- **DRP is one event with two effects** (PT-029): income of the full gross
  dividend plus an acquisition at the reinvestment price. Count the income
  once. It is still income even though no cash arrived. Residual cash from
  partial shares goes to the cash account. Linked rows are displayed together.
- **Splits change quantity, never total cost**, and create no disposal
  (PT-028). Consolidation is the inverse case. Fractional residue is usually
  paid as cash in lieu, and its tax treatment belongs to `uk-tax`.
- **Opening balances** (PT-013) are acquisitions with user-asserted cost. Only
  one is allowed per instrument. The valuation series does not extend before
  it. Gains derived from one are flagged in reports.
- **Fees** are capitalised into cost on buys and deducted from proceeds on
  sells (PT-011). A standalone `fee` row reduces cash and never touches cost
  basis.

### Corrections

- A correction is a new row with `reverses_id` pointing at the original
  (PT-009). Nothing is ever updated or deleted. `PUT` and `DELETE` return 405
  (PT-010).
- The derived effect is as if the original never existed from its own trade
  date onward. Invalidation therefore starts at the original's trade date, not
  at the reversal's created timestamp. `created_at` is the audit trail only.
- Import batches are reversed by generating a reversing row for every
  transaction they created (PT-024).
- **Not yet specified, so ask before choosing:** how a reversing row encodes
  its values (a mirrored row, or a flag the engine nets out), and whether a
  reversal can itself be reversed.

### Ordering

Replay order must be total and deterministic: trade date first, then a stable
tie-break, never DB return order. Without that, a rebuild can differ from an
incremental recompute. The intra-day tie-break between types (for example, does
a split dated D apply before trades on D?) is not yet decided. Ask, then encode
it in one place. For tax, same-day trades are aggregated, so intra-day order
mostly matters for over-sell validation and positions.

### Dates

- Positions and gains run on **trade date**. Settlement date is stored but does
  not drive holdings. UK CGT disposal time is the contract date (TCGA 1992 s28).
- Whether cash moves on trade date or settlement date (PT-030 says "trade
  settlement moves the cash balance") is undecided. Ask before implementing.
  Sharesight-style default is trade date.
- Dividends carry both ex-date and pay date (PT-027). Income is recognised on
  pay date.

## Multi-currency

- Instrument currency is a property of the instrument, not the transaction
  (PT-008). Each transaction stores its trade currency and the FX rate used at
  trade time (PT-009, PT-020).
- Cost basis is kept in **both** trade currency and base currency, with base
  currency computed at the transaction's own rate (PT-011). Valuation uses the
  **daily** rate for the valuation date (PT-020). The gap between the two is
  where currency gain comes from (see the `quant` skill for attribution).
- **Always state the rate's direction.** "1.25" is meaningless without one.
  Write rates as `quote per base`, for example `USD per GBP = 1.25`, and
  convert with `gbp = usd / usd_per_gbp`. PT-009 doesn't fix the direction, so
  pin it in the schema name or docstring, and test with a rate far from 1 so
  that a multiply/divide swap fails.
- **Pence vs pounds.** LSE prices and some broker exports quote in GBX/GBp
  (pence). Treating a price of 1234 GBX as £1,234 is a 100× error. How GBX is
  normalised (at the provider and importer boundary, or as its own currency)
  is undecided. Ask before the first LSE price or Trading 212 row lands.
- Foreign cash is revalued daily and contributes currency gain (PT-030).
- Same-currency lookups short-circuit to a rate of exactly 1 (PT-020).

## Quantities and precision

- Quantities are `Decimal`. Fractional shares come straight from brokers at
  full precision (PT-025).
- Postgres `NUMERIC(24,10)` / `NUMERIC(20,8)` silently rounds extra digits on
  insert. Quantize explicitly in Python to the column scale at the persistence
  boundary, in one helper used by both the incremental path and the
  full-rebuild path. Otherwise in-memory results won't equal DB round-trips.
- Quantity 0 means the position is closed. Keep it, with its realised gain, in
  history (PT-011). Never divide by quantity without guarding the zero case.
- A sell exceeding holdings on its trade date is rejected (PT-010). A negative
  cash balance is allowed but flagged (PT-030).

## Valuation linkage

The design lives in `docs/architecture.md`. Two accounting-specific rules:

- **Quantity and price must use the same split basis.** Before a split's
  effective date, value with the pre-split quantity × the raw close, or the
  post-split quantity × the split-adjusted close. Never mix them (see example
  3). Dividend-adjusted closes double-count dividends that the ledger already
  records as income. The PT-028 convention must be documented in the PR.
- Any new or reversed transaction, price, FX rate, or corporate action
  invalidates valuations for that instrument from its effective date
  (PT-010, PT-022).

## Not modelled yet (ask, don't invent)

- **Transfers:** shares moved in or out from another broker. There is no
  transfer type and no account dimension.
- **Accounts or wrappers:** ISA, SIPP, or multiple brokers as separate pools.
- **Currency conversions** inside a broker account, as distinct from
  conversion fees (PT-025 maps the fees only).
- **Fund-specific events:** accumulation units, equalisation, return of
  capital.

## Testing this area

- **Worked examples:** `references/examples.md` holds hand-checked cases. Use
  them, or new ones derived the same way, as golden tests. Compute expected
  values independently (by hand, a spreadsheet, or `fractions.Fraction`),
  never by running the code under test and pasting its output.
- **Property tests (`hypothesis`) over random valid ledgers:**
  - one-pass replay equals incremental replay (PT-011);
  - quantity = Σ acquisitions − Σ disposals, adjusted by split ratios;
  - cost basis never goes negative;
  - realised + unrealised + income reconciles to total value − net
    contributions;
  - a transaction followed by its reversal leaves every derived figure
    unchanged.
- **Edge cases to cover:**
  - a sell to exactly zero;
  - a sell on the same day as a buy;
  - a split followed by a sell;
  - DRP with a fractional and with a whole-share residual;
  - foreign buy with an FX rate far from 1;
  - an opening balance followed by a sell;
  - a reversal of a mid-history transaction;
  - an over-sell rejection.

For a final pass on any change here, run the `financial-correctness-review`
skill.
