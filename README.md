fix-engine/
│
├── backend/                   # --- THE FIX ENGINE ---
│   ├── __init__.py
│   ├── engine.py              # Main loop: Starts QuickFIX
│   ├── fix_app.py             # Logic: QuickFIX Application class
│   ├── message_parser.py      # Logic: Parses FIX messages -> JSON
│   └── config/
│       └── quickfix.cfg       # FIX connection settings (IP, Port, SenderCompID)
│
├── frontend/                  # --- THE DASHBOARD ---
│   ├── __init__.py
│   ├── app.py                 # Main entry point for Dash (app.run_server)
│   ├── layout.py              # UI: HTML structure, graphs, dropdowns
│   ├── callbacks.py           # Logic: Button clicks, graph updates
│   └── assets/                # Dash automatically serves files here
│       ├── style.css
│       └── logo.png
│
├── shared/                    # --- SHARED RESOURCES ---
│   ├── __init__.py
│   ├── redis_client.py        # Central place to connect to Redis
│   └── constants.py           # Shared keys (e.g., REDIS_CHANNEL_NAME = "market_data")
│
├── requirements.txt           # List of libraries (dash, redis, quickfix, pandas)
├── .env                       # Secrets (API Keys, Passwords)
└── run.py                     # Script to launch both processes at once



Plan: Restructure Backend into Standalone FIX Engine
Context
The backend currently has a single file (backend/fix_engine.py) containing a market data simulator and an order listener that just prints orders. The goal is to restructure it into a proper standalone FIX engine that:

Matches the target structure from README.md (engine.py, fix_app.py, message_parser.py, config/quickfix.cfg)
Works both with the Dash frontend (via Redis) AND as a standalone CLI tool
Has a fully wired QuickFIX Initiator (gracefully degrades when no counterparty is available)
Target Structure

backend/
├── __init__.py              # Package marker
├── engine.py                # CLI entry point + orchestration (replaces fix_engine.py)
├── fix_app.py               # QuickFIX Application class (Initiator)
├── message_parser.py        # FIX ↔ JSON conversion
├── fix_engine.py            # Thin redirect for backward compat
└── config/
    └── quickfix.cfg         # FIX 4.4 Initiator session config
Files to Create/Modify
File	Action	Description
backend/__init__.py	CREATE	Empty, makes backend a package
backend/config/quickfix.cfg	CREATE	FIX 4.4 Initiator config (TRADEDESK → EXCHANGE, port 9876)
backend/message_parser.py	CREATE	order_to_fix(), cancel_to_fix(), fix_to_dict()
backend/fix_app.py	CREATE	FixApplication(quickfix.Application) with all 6 callbacks
backend/engine.py	CREATE	CLI with start/order/prices subcommands + market data sim + order listener
backend/fix_engine.py	MODIFY	Convert to thin redirect to engine.py
shared/constants.py	MODIFY	Add REDIS_KEY_EXECUTION_REPORTS, REDIS_KEY_FIX_STATUS
docker-compose.yml	MODIFY	Update backend CMD, add FIX store/log volumes, add PYTHONUNBUFFERED=1
run.py	MODIFY	Update import from backend.engine
backend/Dockerfile	MODIFY	Update CMD to python backend/engine.py start
Step 1 — backend/__init__.py
Empty file.

Step 2 — shared/constants.py
Add at bottom:


REDIS_KEY_EXECUTION_REPORTS = "execution_reports"
REDIS_KEY_FIX_STATUS = "fix_session_status"
Step 3 — backend/config/quickfix.cfg

[DEFAULT]
ConnectionType=initiator
ReconnectInterval=5
FileStorePath=/tmp/fix_store
FileLogPath=/tmp/fix_log
StartTime=00:00:00
EndTime=00:00:00
UseDataDictionary=Y
DataDictionary=FIX44.xml
ValidateUserDefinedFields=N
ValidateIncomingMessage=N
ResetOnLogon=Y
ResetOnLogout=Y
ResetOnDisconnect=Y

[SESSION]
BeginString=FIX.4.4
SenderCompID=TRADEDESK
TargetCompID=EXCHANGE
SocketConnectHost=127.0.0.1
SocketConnectPort=9876
HeartBtInt=30
Step 4 — backend/message_parser.py
Three functions:

order_to_fix(order_dict, session_id) — Builds FIX 4.4 NewOrderSingle (35=D)

Maps: clOrdID→11, symbol→55, side→54 (BUY="1", SELL="2"), qty→38, ordType→40 (MARKET="1", LIMIT="2"), price→44, timestamp→60
Sets HandlInst(21)="1" (automated)
Uses try: import quickfix44 with fallback to manual fix.Message() construction
cancel_to_fix(cancel_dict, session_id) — Builds OrderCancelRequest (35=F)

Maps: origClOrdID→41, clOrdID→11, symbol→55, side→54
fix_to_dict(fix_msg) — Converts any FIX message to a flat dict

Extracts tags: 35, 11, 37, 17, 150, 39, 55, 54, 38, 44, 31, 32, 14, 151, 58
Humanizes side ("1"→"BUY", "2"→"SELL")
Step 5 — backend/fix_app.py
FixApplication(quickfix.Application) with:

Callback	Behavior
onCreate(session_id)	Store session_id, log
onLogon(session_id)	Set is_logged_on=True, write LOGGED_ON to Redis
onLogout(session_id)	Set is_logged_on=False, write LOGGED_OFF to Redis
toAdmin(msg, sid)	Log; optionally inject username/password for Logon messages
fromAdmin(msg, sid)	Log
toApp(msg, sid)	Log outgoing application message
fromApp(msg, sid)	If MsgType=8 (ExecutionReport): parse via fix_to_dict(), push to Redis execution_reports list
Public method: send_order(fix_message) — calls fix.Session.sendToTarget(), returns True/False

Step 6 — backend/engine.py
CLI subcommands (argparse)
start — Run the full engine

Flags: --redis-host, --fix-config (default: backend/config/quickfix.cfg), --no-market-data, --verbose
Initializes: QuickFIX SocketInitiator (starts non-blocking), market data simulator thread, order listener on main thread
Order routing: if fix_app.is_logged_on → send via QuickFIX; else → log in SIM mode
Signal handlers for clean shutdown (SIGINT/SIGTERM stop the initiator)
order — Submit an order from CLI directly to Redis

Flags: --side BUY/SELL, --qty N, --symbol SYM, --price P (optional → LIMIT), --type MARKET/LIMIT
Pushes JSON to Redis outgoing_orders queue, prints confirmation
No QuickFIX needed — lightweight
prices — Stream live prices to terminal

Flags: --symbol (filter), --format table/json
Reads market_data_snapshot from Redis every 1s
Table mode: clears screen, prints aligned columns (Symbol, Bid, Ask, Mid, Change, VWAP)
JSON mode: prints raw JSON
Market data simulator
Moved from fix_engine.py verbatim (same SPREAD_CONFIG, same random walk + TWAP logic). Takes redis_conn as a parameter instead of module-global.

Order listener
Same brpop loop as current code, but adds FIX routing gate:


if fix_app.is_logged_on → order_to_fix() → fix_app.send_order()
else → log "SIM MODE: ..."
Step 7 — backend/fix_engine.py (backward compat redirect)

"""Backward-compatible entry point. Delegates to backend.engine."""
from backend.engine import cmd_start
import argparse

if __name__ == "__main__":
    args = argparse.Namespace(
        redis_host=None, fix_config='backend/config/quickfix.cfg',
        no_market_data=False, verbose=False,
    )
    cmd_start(args)
Step 8 — backend/Dockerfile
Change CMD:


CMD ["python", "backend/engine.py", "start"]
Step 9 — docker-compose.yml
Update backend CMD (handled by Dockerfile)
Add PYTHONUNBUFFERED=1 to backend environment
Add named volumes for FIX store/log persistence:

volumes:
  - fix-store:/tmp/fix_store
  - fix-log:/tmp/fix_log
Step 10 — run.py
Update import to from backend.engine import cmd_start and call it with an argparse.Namespace.

Verification
Standalone CLI (no Docker)

# Terminal 1: Start engine (QuickFIX retries every 5s — expected, no counterparty)
python backend/engine.py start --verbose

# Terminal 2: Submit order from CLI
python backend/engine.py order --side BUY --qty 10 --symbol 10Y

# Terminal 3: Stream prices
python backend/engine.py prices --format table
Docker

docker compose down && docker compose up --build
Backend logs: "Market Data Simulator Started", "Order listener started", QuickFIX connection retries (expected)
Frontend at http://localhost:8050 still works — prices update, BUY/SELL still submits orders
Backend logs show "SIM MODE" for orders (no counterparty connected)
QuickFIX pitfalls to handle
import quickfix44 may fail → use try/except fallback to manual fix.Message() construction
DataDictionary=FIX44.xml path → bundle copy in backend/config/ or use absolute path to installed location
QuickFIX thread safety: sendToTarget() is thread-safe, safe to call from order listener thread