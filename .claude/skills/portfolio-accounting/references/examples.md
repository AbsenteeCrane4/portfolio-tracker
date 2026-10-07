# Worked accounting examples

All of these were hand-checked. The examples use Section 104 average-cost
allocation on sells and assume **no acquisition of the same instrument within
30 days after any sell**, so the same-day and 30-day rules don't fire. Where
those rules would change the answer, the example says so. See
`uk-tax/references/examples.md` for the matching cases.

FX rates are written as `USD per GBP`.

---

## 1. Buy, partial sell, dividend, DRP (GBP)

| Date | Event | Quantity | Cost basis | Cash | Income | Realised |
|---|---|---|---|---|---|---|
| 2025-01-10 | buy 100 @ £10.00, fee £5 | 100 | 1005.00 | −1005.00 | | |
| 2025-03-03 | sell 40 @ £12.00, fee £5 | 60 | 603.00 | +475.00 | | +73.00 |
| 2025-06-16 | dividend £0.30 × 60 | 60 | 603.00 | +18.00 | 18.00 | |
| 2025-09-15 | DRP £0.30 × 60 = £18.00 @ £11.70, whole shares | 61 | 614.70 | +6.30 | 18.00 | |

How each row is computed:

- **Sell:** proceeds are 40 × 12 − 5 = 475. Allocated cost is
  1005 × 40/100 = 402. Gain is 73.
- **DRP:** ⌊18 / 11.70⌋ = 1 share, costing 11.70. The residual 6.30 goes to
  cash. Income is the full 18.00, even though only 6.30 arrived as cash.
- **Fractional DRP variant:** the quantity is 18 / 11.70 =
  1.538461538461…, stored as `1.5384615385`. The cost added is exactly 18.00.
  Store the total, not quantity × price, because
  1.5384615385 × 11.70 = 18.00000000045.

Reconciliation at a close of £12.00, assuming £1,005 was deposited at the
start:

- holding value: 61 × 12 = 732.00;
- cash: 1005 − 1005 + 475 + 18 + 6.30 = 499.30;
- total value: 1231.30;
- gain: 1231.30 − 1005 = 226.30.

That gain equals realised 73 + unrealised (732 − 614.70 = 117.30) +
income 36 = 226.30.

Traps:

- Counting DRP income twice: once as the dividend and again via the
  acquisition.
- Not counting DRP income at all, because no cash arrived.
- Netting the sell fee into cost instead of proceeds. The gain is the same,
  but the reported proceeds and costs are both wrong.

30-day trap: if the DRP had landed on 2025-03-20, within 30 days of the
2025-03-03 sell, HMRC matching would pair it with part of that disposal. The
sell's gain would change, and the DRP shares would not enter the pool.

---

## 2. Foreign buy, later valued in GBP

| | Trade currency | Rate | Base (GBP) |
|---|---|---|---|
| Buy 10 @ $200, fee $1 | cost $2,001 | 1.25 | 2001 / 1.25 = **1600.80** |
| Value at close $220 | MV $2,200 | 1.30 | 2200 / 1.30 = **1692.3076923077** |

- Total gain in base currency: 1692.3076923077 − 1600.80 = 91.5076923077.
- Gain in trade currency: 2200 − 2001 = $199.

The split of that £91.51 into capital and currency depends on the rate used to
convert the $199. PT-031 must choose one and label it:

| Convention | Capital (GBP) | Currency (GBP) |
|---|---|---|
| A: convert at the current rate | 199 / 1.30 = 153.0769230769 | −61.5692307692 |
| B: convert at the acquisition rate | 199 / 1.25 = 159.20 | −67.6923076923 |

Both conventions sum to 91.5076923077 exactly, because currency is the
residual.

Traps:

- Multiplying instead of dividing: 2001 × 1.25 = 2501.25.
- Valuing at the trade-time rate instead of the daily rate, which hides the
  currency effect entirely.

---

## 3. Split, then sell

| Date | Event | Quantity | Cost basis |
|---|---|---|---|
| 2025-01-06 | buy 50 @ £40 | 50 | 2000.00 |
| 2025-04-01 | 5-for-1 split | 250 | 2000.00 (per share 8.00) |
| 2025-05-01 | sell 100 @ £9 | 150 | 1200.00 |

- **Sell:** proceeds 900, allocated cost 2000 × 100/250 = 800, gain 100.
- **The split** creates no disposal and no gain.

Valuation on 2025-03-31, with a raw close of £40 and a split-adjusted close of
£8:

- correct: 50 × £40 = 2000, or 250 × £8 = 2000;
- wrong: 50 × £8 = 400, a fake 80% loss;
- wrong: 250 × £40 = 10,000.

---

## 4. Deposit, purchase, withdrawal (cash account)

| Event | Cash GBP | Holding | External flow |
|---|---|---|---|
| deposit £5,000 | 5000 | – | +5000 in |
| buy 100 @ £30, fee £10 | 1990 | 100, cost 3010 | none |
| withdraw £1,000 | 990 | 100, cost 3010 | −1000 out |

At a close of £32:

- value: 990 + 3200 = 4190;
- net contributions: 4000;
- gain: 190, which matches 3200 − 3010.

Traps:

- Calculating (4190 − 5000) / 5000 = −16.2% and calling it a loss.
  Withdrawals are not losses.
- Booking the deposit as income or gain.
- Treating the buy as an external flow. Once cash is tracked, a buy only moves
  value between instruments inside the portfolio.

If the cash were USD, its daily revaluation would add currency gain with no
transaction at all.

---

## 5. Several purchases, then a partial disposal

| Date | Event | Pool quantity | Pool cost |
|---|---|---|---|
| 2024-05-01 | buy 100 @ £5 | 100 | 500 |
| 2024-08-01 | buy 100 @ £7 | 200 | 1200 |
| 2025-02-03 | sell 150 @ £8 | 50 | 300 |

- **Correct (Section 104):** proceeds 1200, cost 1200 × 150/200 = 900,
  gain **300**.
- **Wrong, FIFO:** cost 500 + 50 × 7 = 850, gain 350.
- **Wrong, LIFO:** cost 700 + 50 × 5 = 950, gain 250.

The remaining 50 shares carry a cost of 300, so the average cost stays at 6.00.
