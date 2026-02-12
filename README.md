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