# Bridge (Telegram -> HTTP)

This service listens to the public Telegram channel `@FXTradingVision`, parses trade ideas, and exposes the latest parsed signal via HTTP for the MT5 EA.

## Requirements
- Python 3.10+
- A Telegram account (you will login once on first run)

## Setup
1) Create Telegram API credentials:
- Go to https://my.telegram.org
- Create an app, copy `API_ID` and `API_HASH`

2) Create your `.env` file:
```bash
cp .env.example .env
```
Edit `.env` and fill in values.

3) Install deps:
```bash
pip install -r requirements.txt
```

## Run
```bash
python telegram_bridge.py
```

It will start:
- Listener (Telethon)
- HTTP API at: http://127.0.0.1:8000/latest

## Notes
- Do not commit `.env` or `*.session` files.
- If your Telegram account has 2FA, Telethon will ask for your password on first login.
