import json
import os
import re
import time
from threading import Thread
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from telethon import TelegramClient, events

load_dotenv()

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
CHANNEL = os.environ.get("CHANNEL", "FXTradingVision")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

if not API_ID or not API_HASH:
    raise SystemExit("Missing API_ID/API_HASH. Create bridge/.env from bridge/.env.example")

state: Dict[str, Any] = {
    "msg_id": None,
    "ts": None,
    "raw": None,
    "signal": None,
}

app = FastAPI()


def parse_signal(text: str) -> Optional[Dict[str, Any]]:
    """Parse FXTradingVision style messages.

    Example:
      NEW TRADE IDEA XAUUSD BUY 5229 TP 1 5231 TP 2 5232 TP 3 5233 TP 4 5260 SL @ 5200
    """

    t = " ".join((text or "").strip().split())
    if not t:
        return None

    # Cut common disclaimer (keep signal part)
    t = re.split(r"\bProfits\s+are\b", t, maxsplit=1)[0].strip()

    m = re.search(r"\b([A-Z]{3,12})\s+(BUY|SELL)\s+(\d+(?:\.\d+)?)\b", t)
    if not m:
        return None

    symbol = m.group(1)
    side = m.group(2)
    entry = float(m.group(3))

    slm = re.search(r"\bSL\s*(?:@)?\s*(\d+(?:\.\d+)?)\b", t)
    sl = float(slm.group(1)) if slm else None

    tps = [float(x) for x in re.findall(r"\bTP\s*\d*\s*(\d+(?:\.\d+)?)\b", t)]

    return {
        "source": CHANNEL,
        "type": "idea",
        "symbol": symbol,
        "side": side,
        "entry": entry,
        "sl": sl,
        "tp": tps,
    }


@app.get("/latest")
def latest():
    return state


async def tg_loop():
    client = TelegramClient("fxcopier", API_ID, API_HASH)
    await client.start()  # first run: phone + code (+ optional 2FA)

    @client.on(events.NewMessage(chats=CHANNEL))
    async def handler(event):
        txt = event.raw_text or ""
        sig = parse_signal(txt)
        if not sig:
            return

        state["msg_id"] = event.message.id
        state["ts"] = int(time.time())
        state["raw"] = txt
        state["signal"] = sig

        print("NEW SIGNAL:")
        print(json.dumps(state, ensure_ascii=False))

    print(f"Listening to @{CHANNEL} …")
    print(f"HTTP: http://{HOST}:{PORT}/latest")

    await client.run_until_disconnected()


def run_api():
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    Thread(target=run_api, daemon=True).start()

    import asyncio

    asyncio.run(tg_loop())
