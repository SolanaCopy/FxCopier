# MT5 EA

The MT5 Expert Advisor (EA) polls the bridge endpoint and places trades.

## Setup
1) Copy `FxCopier.mq5` into:
- `MQL5/Experts/`

2) In MT5:
- Tools -> Options -> Expert Advisors
- Enable: "Allow WebRequest for listed URL"
- Add:
  - `http://127.0.0.1:8000`

3) Attach EA to a chart (any symbol) and enable AutoTrading.

## Current behavior (MVP)
- Polls `GET /latest`
- If `msg_id` is new and a `signal` is present:
  - Places a market order (BUY/SELL) for the parsed symbol
  - Sets SL
  - Sets TP1 (first TP only) as initial TakeProfit

## Notes
- Risk management in this MVP is fixed lot (configurable in inputs).
- You can extend to partial take profits (TP1..TP4) by splitting volume into multiple positions.
