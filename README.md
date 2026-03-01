# FxCopier

Telegram channel  MT5 auto-trader.

This repo contains:
- `bridge/`: Python service that reads signals from a Telegram channel (via your Telegram user account) and exposes the latest parsed signal over HTTP.
- `mt5/`: MT5 Expert Advisor (MQL5) that polls the bridge and places trades.

## Supported signal format (example)
```
NEW TRADE IDEA XAUUSD BUY 5229
TP 1 5231 TP 2 5232 TP 3 5233 TP 4 5260
SL @ 5200
```

## Quick start
- Bridge: see `bridge/README.md`
- MT5 EA: see `mt5/README.md`

## Security
Do NOT commit your Telegram `API_ID`, `API_HASH`, phone number, or `.session` files.
