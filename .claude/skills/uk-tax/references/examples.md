# Worked UK tax examples (hand-checked)

All amounts are in GBP unless stated. The tax year starts on 6 April. These are
project test cases. For legally authoritative golden cases, also encode the
worked examples from HS284, citing the example number.

---

## A. Same-day match

Starting pool: 1,000 shares, cost 5,000, built in 2023.

On 2025-06-02: buy 100 @ 10.00 (cost 1,000) and sell 100 @ 11.00 (proceeds
1,100).

- **Same-day:** 1,100 − 1,000 = **gain 100**. The pool is unchanged at
  1,000 shares / 5,000.
- **Wrong (pool cost used):** 1,100 − 500 = 600.

**Variant: sell 150 instead of 100** (proceeds 1,650), with no acquisitions in
the next 30 days.

- Same-day, 100 shares: proceeds 1,100, cost 1,000, gain 100.
- Pool, 50 shares: proceeds 550, cost 5,000 × 50/1,000 = 250, gain 300.
- Total gain **400**. The pool becomes 950 shares / 4,750.

---

## B. Bed and breakfast (30-day)

Starting pool: 1,000 shares, cost 5,000.

| Date | Event |
|---|---|
| 2025-03-03 | sell 1,000 @ 4.00 = 4,000 |
| 2025-03-20 | buy 1,000 @ 4.10 = 4,100 |

- **Correct:** the disposal is matched with the 20 March acquisition.
  4,000 − 4,100 = **loss 100**. The pool keeps 1,000 shares / 5,000.
- **Wrong:** a loss of 1,000 against the pool, and a pool of 1,000 / 4,100.

Provisional window: the window is 2025-03-04 to 2025-04-02. Viewed on
2025-03-10, the disposal would show a 1,000 loss from the pool. It becomes
final only after 2025-04-02, and the 20 March purchase must trigger a
recompute of the 3 March disposal.

**Cross-year variant.** Sell 1,000 on 2025-04-01 (tax year 2024–25) and buy
1,000 on 2025-04-20 (tax year 2025–26). The disposal belongs to 2024–25 but is
matched to the 2025–26 acquisition. The 2024–25 report changes after that
year has ended.

---

## C. Partial 30-day match plus pool remainder

Starting pool: 1,000 shares, cost 5,000.

| Date | Event |
|---|---|
| 2025-05-01 | sell 600 @ 6.00 = 3,600 |
| 2025-05-15 | buy 200 @ 5.50 = 1,100 (D+14, inside the window) |
| 2025-06-10 | buy 300 @ 5.80 = 1,740 (D+40, outside the window) |

- **30-day, 200 shares:** proceeds 1,200, cost 1,100, gain 100.
- **Pool, 400 shares:** proceeds 2,400, cost 5,000 × 400/1,000 = 2,000,
  gain 400.
- **Total gain: 500.**

The pool after the disposal is 600 / 3,000. The 15 May purchase never enters
it. The 10 June purchase enters, making the pool 900 / 4,740. Check: physical
holdings are 1,000 − 600 + 200 + 300 = 900, which equals the pool quantity.

---

## D. Foreign-currency disposal

Rates are written as USD per GBP.

| Event | USD | Rate | GBP |
|---|---|---|---|
| buy 100 @ $50 | 5,000 | 1.25 | 4,000.00 |
| sell 100 @ $60 | 6,000 | 1.20 | 5,000.00 |

- **Chargeable gain:** 5,000 − 4,000 = **1,000**.
- **Informational split:** the USD gain of $1,000 at the disposal rate is
  833.33, which leaves 166.67 attributable to currency movement. This split is
  not a separate chargeable gain.

---

## E. Incidental costs

- **Buy** 100 UK shares @ 10.00, with commission 5 and SDRT 0.5% = 5. Cost is
  1,010.
- **Sell** 100 @ 12.00, with commission 5. Proceeds are 1,195.
- **Gain: 185.**

SDRT applies to UK shares but generally not to ETFs. That depends on the
instrument, so don't assume it.

---

## F. Split inside the pool

Pool: 100 shares / 1,000. A 2-for-1 split makes it 200 / 1,000. There is no
disposal and no gain, and the per-share cost goes from 10 to 5.

If a disposal of 100 before the split is followed within 30 days by a
reacquisition of 200 post-split shares, compare on the same basis: the 100
pre-split shares correspond to 200 post-split shares.
