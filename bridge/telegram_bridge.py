import json
import os
import re
import time
from dataclasses import dataclass
from threading import Thread
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from telethon import TelegramClient, events

# --- config ---
load_dotenv()

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
CHANNEL = os.environ.get("CHANNEL", "FXTradingVision")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

# Debug toggles (set in .env)
LOG_SKIPS = os.environ.get("LOG_SKIPS", "1") == "1"   # 1/0
LOG_RAW = os.environ.get("LOG_RAW", "0") == "1"       # 1/0

if not API_ID or not API_HASH:
    raise SystemExit("Missing API_ID/API_HASH. Create .env from .env.example")

# --- state ---
state: Dict[str, Any] = {
    "msg_id": None,
    "ts": None,
    "raw": None,
    "signal": None,
    "last_skip": None,
}

app = FastAPI()


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log(level: str, msg: str, **kv: Any) -> None:
    payload = (" " + json.dumps(kv, ensure_ascii=False)) if kv else ""
    print(f"[{now()}] {level}: {msg}{payload}")


@dataclass
class ParseResult:
    ok: bool
    signal: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


def parse_signal(text: str) -> ParseResult:
    """Parse FXTradingVision style messages.

    Expected (example):
      NEW TRADE IDEA XAUUSD BUY 5229 TP 1 5231 TP 2 5232 TP 3 5233 TP 4 5260 SL @ 5200
    """

    if not text:
        return ParseResult(False, reason="empty")

    t = " ".join(text.strip().split())
    if not t:
        return ParseResult(False, reason="blank")

    # Cut common disclaimer (keep signal part)
    t = re.split(r"\bProfits\s+are\b", t, maxsplit=1)[0].strip()

    # Require symbol + side + entry
    m = re.search(r"\b([A-Z]{3,12})\s+(BUY|SELL)\s+(\d+(?:\.\d+)?)\b", t)
    if not m:
        return ParseResult(False, reason="no (SYMBOL BUY/SELL PRICE) match")

    symbol = m.group(1)
    side = m.group(2)
    entry = float(m.group(3))

    # SL optional
    slm = re.search(r"\bSL\s*(?:@)?\s*(\d+(?:\.\d+)?)\b", t)
    sl = float(slm.group(1)) if slm else None

    # TP list optional
    tps = [float(x) for x in re.findall(r"\bTP\s*\d*\s*(\d+(?:\.\d+)?)\b", t)]

    sig = {
        "source": CHANNEL,
        "type": "idea",
        "symbol": symbol,
        "side": side,
        "entry": entry,
        "sl": sl,
        "tp": tps,
    }

    # sanity
    if sl is None:
        return ParseResult(False, reason="matched but missing SL")
    if not tps:
        return ParseResult(False, reason="matched but no TPs found")

    return ParseResult(True, signal=sig)


@app.get("/latest")
def latest():
    return state


@app.get("/health")
def health():
    return {
        "ok": True,
        "channel": CHANNEL,
        "ts": int(time.time()),
        "last_msg_id": state.get("msg_id"),
        "has_signal": state.get("signal") is not None,
    }


async def tg_loop():
    client = TelegramClient("fxcopier", API_ID, API_HASH)
    await client.start()  # first run: phone + code (+ optional 2FA)

    me = await client.get_me()
    user = (getattr(me, "username", None) or getattr(me, "first_name", ""))
    log("INFO", "Signed in", user=user)
    log("INFO", f"Listening to @{CHANNEL}")
    log("INFO", f"HTTP: http://{HOST}:{PORT}/latest (health: /health)")

    @client.on(events.NewMessage(chats=CHANNEL))
    async def handler(event):
        msg_id = event.message.id
        txt = event.raw_text or ""

        if LOG_RAW:
            log("DEBUG", "TG message", msg_id=msg_id, raw=txt)

        res = parse_signal(txt)
        if not res.ok:
            if LOG_SKIPS:
                state["last_skip"] = {
                    "msg_id": msg_id,
                    "ts": int(time.time()),
                    "reason": res.reason,
                }
                log("SKIP", "Message not parsed as signal", msg_id=msg_id, reason=res.reason)
            return

        state["msg_id"] = msg_id
        state["ts"] = int(time.time())
        state["raw"] = txt
        state["signal"] = res.signal

        log("SIGNAL", "Parsed signal", msg_id=msg_id, signal=res.signal)

    await client.run_until_disconnected()


def run_api():
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    Thread(target=run_api, daemon=True).start()

    import asyncio

    asyncio.run(tg_loop())
