# Market data

End-of-day prices are the baseline. 15-minute delayed intraday data is a bonus
where a free tier allows it. Nothing is designed around live ticks or
websockets.

Free tiers are the binding constraint. They are stingy and change often, so
providers must be swappable and quota is treated as a first-class resource.

## Provider landscape

This is a snapshot, written around September 2026. Treat every number as
unverified and check the provider's current terms before relying on it. The
defaults in `core/settings.py` / `.env.example` started from this table, and
the configured value is what the quota ledger enforces.

| Provider | Free tier | Notes |
|---|---|---|
| Twelve Data | ~800 credits/day, 8 req/min | Good breadth, global coverage |
| Finnhub | 60 req/min, ~1yr history | Generous news endpoint |
| Alpha Vantage | ~25 req/day | Deep history, punishing limit |
| Tiingo | ~500 symbols/month | Strong EOD history, US-centric |
| FMP | ~250 calls/day EOD | Fundamentals included |
| EODHD | ~20 calls/day, 1yr history | Too tight for polling; backfill only |

Some limits are per minute or per month rather than per day (Finnhub, Tiingo).
The current settings model only a daily budget, so the configured daily quota
is an approximation for those providers.

Yahoo Finance's unofficial endpoints are not a dependency. They break without
warning and nothing contractual stands behind them.

## Polling design

- **One scheduled job per provider**, not one per holding. Symbols are batched
  into the fewest possible requests.
- **Quota ledger:** every outbound call is recorded against that provider's
  daily budget. When the budget runs out, the job stops cleanly and resumes in
  the next window. It never spends the day's quota on a retry storm.
- **The cache is permanent.** The `prices` table, keyed by
  `(instrument, date, source)`, is the system of record. Providers are only
  asked to fill gaps.
- **Backfill is a separate, resumable job** with its own lower-priority quota
  allocation, so it can't starve daily polling.
- **Failures leave gaps.** No nulls written, and no silent carry-forward. The
  UI shows a stale-price indicator rather than a wrong number.
- **FX rates** follow the same pattern in an `fx_rates` table.
- **Scraping** is a last resort. A scraper sits behind the same provider
  interface and runs in an isolated subprocess, so that its failures degrade
  gracefully.
