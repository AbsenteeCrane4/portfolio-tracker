# Market data: provider landscape

This is volatile reference material. The architecture, pipeline, and failure
handling live in the `market-data` skill (`.claude/skills/market-data/`).

End-of-day prices are the baseline. 15-minute delayed intraday data is a bonus
where a free tier allows it. Free tiers are the binding constraint and change
often, so providers must be swappable and quota is a first-class resource.

## Free tiers

Snapshot from around September 2026. Treat every number as unverified, and
check the provider's current terms before relying on it. The defaults in
`core/settings.py` and `.env.example` started from this table. The configured
value is what the quota ledger enforces. When you verify a figure, update it
here and in the settings defaults, with the date (PT-016).

| Provider | Free tier | Notes |
|---|---|---|
| Twelve Data | ~800 credits/day, 8 req/min | Primary (PT-016). Good breadth, global coverage |
| Finnhub | 60 req/min, ~1yr history | Fallback (PT-017). Generous news endpoint |
| Alpha Vantage | ~25 req/day | Deep history, punishing limit |
| Tiingo | ~500 symbols/month | Strong EOD history, US-centric |
| FMP | ~250 calls/day EOD | Fundamentals included |
| EODHD | ~20 calls/day, 1yr history | Too tight for polling; backfill only |

Finnhub's limit is per minute and Tiingo's is per month. Settings currently
model only a daily budget, so the configured daily quota is an approximation
for those two until PT-015 adds per-minute rates.

## Excluded sources

Yahoo Finance's unofficial endpoints are not a dependency. They break without
warning and nothing contractual stands behind them.
