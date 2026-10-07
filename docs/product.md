# Product scope

Sharesight is the functional reference. This project diverges from it by being
single-user, self-hosted, limited to UK tax rules, built on free-tier price
data, and extended with a market roundup/suggestion engine.

Individual GitHub issues define what gets built and when. This page is the
envelope those issues sit inside.

## v1: the Sharesight core

- **Import:** broker CSV import using a per-broker mapping profile, plus
  Sharesight's own export format and a generic trade CSV. Manual entry, and
  opening-balance entry for holdings without full history.
- **Holdings view:** for each holding, quantity, average cost, market value,
  unrealised gain, and return, plus portfolio totals.
- **Value over time graph:** a daily portfolio value series that can be
  filtered by date range and grouped by market, sector, or custom group.
- **Performance breakdown:** total return split into capital gain, dividend
  income, and currency gain. Annualised money-weighted return (IRR), not just
  simple percentage change.
- **Dividends:** recorded per holding and counted in return. Manual
  confirmation of payments is acceptable; auto-detection can come later.
- **Corporate actions:** share splits, consolidations, and DRP/DRIP
  reinvestments, each recorded as a ledger entry with its effect on positions
  derived.
- **Multi-currency:** GBP base currency, a trade currency on each transaction,
  and the FX rate captured at transaction time and revalued daily.
- **Cash accounts:** tracked as instruments, so that deposits, withdrawals,
  and uninvested cash appear in portfolio value.

## v2: reporting and analysis

- **Taxable income report:** dividends, distributions, and interest over a
  period, split into UK and foreign.
- **Sold securities / realised CGT report:** using the HMRC matching rules.
- **Unrealised CGT report:** what would be realised if everything were sold
  today.
- **Diversity report:** allocation by market, sector, industry, currency, and
  custom group.
- **Benchmarking:** portfolio performance against a chosen instrument or index.
- **Future income:** projected dividends based on declared and historical
  payments.
- **Market roundup:** a scheduled analysis that combines price action, news,
  and quant signals into suggestions the user accepts or dismisses.

## Explicitly out of scope

- Order execution
- Broker API sync (files are imported instead)
- Property or unlisted asset tracking
- Multi-user or accountant sharing
- Non-UK tax regimes
- Real-time prices: end-of-day is the baseline, and 15-minute delayed data is
  a bonus where a free tier allows it. Nothing assumes live ticks or
  websockets.

This is a decision-support tool for personal use. It is not a regulated advice
product. Suggestion copy describes signals and observations rather than
instructing.
