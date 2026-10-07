# HMRC rules: law, implementation, and open assumptions

Sources were last checked on **2026-10-07**. Tax guidance changes, so recheck
any source before relying on a rule for a new behaviour, and update the date
here when you do.

## Primary sources

- **HS284, "Shares and Capital Gains Tax"** (current version 2025–26, updated
  6 April 2026). It has worked examples of same-day, bed-and-breakfast, and
  Section 104 matching.
  https://www.gov.uk/government/publications/shares-and-capital-gains-tax-hs284-self-assessment-helpsheet
- **HMRC Capital Gains Manual, CG51560**, on the same-day and
  bed-and-breakfast identification rules from 6 April 2008.
  https://www.gov.uk/hmrc-internal-manuals/capital-gains-manual/cg51560
  Neighbouring pages (CG51500 onwards) cover the Section 104 holding.
- **TCGA 1992**, at https://www.legislation.gov.uk/ukpga/1992/12:
  - s28: time of disposal;
  - s38: allowable expenditure;
  - s104: the pool;
  - s105: same day;
  - s106A: identification, including 30 days;
  - s122: capital distributions;
  - s126 to s131: reorganisations.
- **Annual exempt amount:**
  https://www.gov.uk/capital-gains-tax/allowances

## Rules

| # | Law / guidance | Project implementation | Open assumptions |
|---|---|---|---|
| 1 | Same-day acquisitions and disposals are each aggregated, and a disposal is identified first with same-day acquisitions (s105(1)(b); CG51560). This has priority over every other rule. | Steps 1–2 of the SKILL procedure. | None. |
| 2 | A disposal is next matched with acquisitions in the 30 days **after** it, earliest first, for the same class of shares and the same person in the same capacity (s106A; CG51560). | Step 3. The instrument stands in for "same class". | "Same capacity" is assumed to hold for every holding. That breaks once ISA or SIPP wrappers exist. |
| 3 | The remainder comes from the Section 104 holding at average pooled cost (s104). | Step 4. The pool is kept in GBP. | None. |
| 4 | Acquisitions matched under rules 1–2 do not enter the pool. | Step 5. | None. |
| 5 | Time of disposal is the contract date (s28). | The engine uses trade date. | None. |
| 6 | Allowable cost includes incidental costs of acquisition and disposal, such as commission and stamp duty (s38). | Fees are stored separately (PT-009), added to cost and deducted from proceeds (PT-011, PT-037). | Whether broker FX-conversion fees (PT-025) are allowable incidental costs is **unconfirmed**. |
| 7 | Foreign-currency cost and proceeds are converted to sterling at the respective transaction dates. | The rate stored on each transaction is used. | Using the broker's trade-time rate rather than a published daily rate is assumed acceptable, provided it is consistent. **Confirm.** |
| 8 | A share reorganisation (split or consolidation) is not a disposal. The new holding stands in the old one's shoes (s126 onwards). | Pool quantity × ratio, cost unchanged (PT-028). | None. |
| 9 | Cash received on a reorganisation (fractions) is a capital distribution, which is a part disposal unless it is "small", in which case it may reduce cost instead (s122). | **Not implemented.** | The small threshold and its election need confirming from the CG manual before PT-028's fractional residue is coded. |
| 10 | Dividends are taxable when paid. Reinvested (DRP) dividends are still income. | Income by pay date (PT-027). DRP counted as income (PT-029). | The pay-date recognition rule is **to confirm** against HMRC's savings and investment guidance. |
| 11 | UK vs foreign income depends on the payer's residence. | Not yet representable: there is no domicile field (PT-008). | **Ask** how domicile is sourced. |

## Year-specific figures

These are volatile. They live in `Settings`, never in code.

| Figure | Value | Applies from | Source / checked |
|---|---|---|---|
| CGT annual exempt amount | £3,000 | 2024–25, unchanged for 2025–26 and 2026–27 | gov.uk allowances page; 2026–27 confirmed via secondary sources on 2026-10-07 |

Earlier values were £6,000 for 2023–24 and £12,300 for 2022–23. Historical
reports need the figure for the year being reported, so a single "current"
value isn't enough once PT-037 shows past years. Raise this when implementing.
