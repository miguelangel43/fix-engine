# Redis Keys
REDIS_KEY_ORDER_QUEUE = "outgoing_orders"      # List: Frontend pushes, Backend pops
REDIS_KEY_MARKET_DATA = "market_data_stream"   # PubSub: Backend publishes, Frontend subscribes
REDIS_KEY_LATEST_PRICES = "market_data_snapshot"
REDIS_KEY_SYSTEM_LOGS = "system_logs"          # Stream/List: Common logging

# Message Types
MSG_TYPE_NEW_ORDER = "NewOrderSingle"
MSG_TYPE_CANCEL = "OrderCancelRequest"

# Instruments: (id, label, description, base_price, type)
INSTRUMENTS = [
    ("2Y",    "2Y",     "T 3 \u00bd 01/31/28",     99.875, "TREAS"),
    ("3Y",    "3Y",     "T 4 \u00bc 02/15/27",      99.10,  "TREAS"),
    ("5Y",    "5Y",     "T 4 \u215b 01/31/30",      98.50,  "TREAS"),
    ("10Y",   "10Y",    "T 3 \u215e 12/15/33",      96.25,  "TREAS"),
    ("30Y",   "30Y",    "T 4 \u00bc 05/15/54",      95.80,  "TREAS"),
    ("TUH6",  "TU",     "2Y NOTE FUT MAR26",        102.12, "FUT"),
    ("TYH6",  "TY",     "10Y NOTE MAR26",           110.15, "FUT"),
    ("USH6",  "US",     "30Y BOND MAR26",           119.05, "FUT"),
    ("SR3H6", "SFR H6", "3M SOFR MAR26",             96.50, "FUT"),
    ("SR3Z6", "SFR Z6", "3M SOFR DEC26",             96.35, "FUT"),
]

# Quote style per instrument (controls display formatting)
QUOTE_STYLES = {
    "2Y":    "32nds_half",     # cash bonds: 1/64 min tick, e.g. 99-28+
    "3Y":    "32nds_half",
    "5Y":    "32nds_half",
    "10Y":   "32nds_half",
    "30Y":   "32nds_half",
    "TUH6":  "32nds_eighth",   # 2Y futures: 1/256 min tick, e.g. 102-052
    "TYH6":  "32nds_half",     # 10Y futures: 1/64 min tick, e.g. 110-05+
    "USH6":  "32nds_whole",    # 30Y bond futures: 1/32 min tick, e.g. 119-02
    "SR3H6": "decimal3",       # SOFR: 0.005 min tick, e.g. 96.252
    "SR3Z6": "decimal3",
}

# Decimal tick size per instrument
TICK_SIZES = {
    "2Y":    1/64,
    "3Y":    1/64,
    "5Y":    1/64,
    "10Y":   1/64,
    "30Y":   1/64,
    "TUH6":  1/256,
    "TYH6":  1/64,
    "USH6":  1/32,
    "SR3H6": 0.005,
    "SR3Z6": 0.005,
}