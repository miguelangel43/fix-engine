import time
import json
import redis
import os
import threading
import random

# --- SHARED IMPORTS ---
from shared.redis_client import get_redis_connection
from shared.constants import REDIS_KEY_ORDER_QUEUE, REDIS_KEY_MARKET_DATA, REDIS_KEY_LATEST_PRICES, INSTRUMENTS

r = get_redis_connection()

# Per-instrument walk step and half-spread (walk_step, half_spread)
SPREAD_CONFIG = {
    "2Y":    (0.010, 0.005),
    "3Y":    (0.010, 0.005),
    "5Y":    (0.015, 0.008),
    "10Y":   (0.015, 0.010),
    "30Y":   (0.020, 0.015),
    "TUH6":  (0.020, 0.008),
    "TYH6":  (0.025, 0.010),
    "USH6":  (0.030, 0.015),
    "SR3H6": (0.010, 0.005),
    "SR3Z6": (0.010, 0.005),
}

def run_market_data_simulator():
    print(f"Market Data Simulator Started.", flush=True)

    # Build fair_values from the shared INSTRUMENTS list
    fair_values  = {inst_id: base_price for inst_id, _, _, base_price, _ in INSTRUMENTS}
    session_open = dict(fair_values)           # frozen at session start
    twap_sum     = dict(fair_values)           # running sum for TWAP
    twap_count   = {inst_id: 1 for inst_id in fair_values}

    while True:
        timestamp = time.time()
        market_snapshot = {}

        for inst_id, _, _, _, _ in INSTRUMENTS:
            walk_step, half_spread = SPREAD_CONFIG[inst_id]

            # 1. Move the "Fair Value" (Random Walk)
            fair_values[inst_id] += random.uniform(-walk_step, walk_step)

            # 2. Derive Bid/Ask around the fair value
            mid = fair_values[inst_id]
            bid = round(mid - half_spread, 5)
            ask = round(mid + half_spread, 5)
            final_mid = round((bid + ask) / 2, 5)

            # 3. Update running TWAP
            twap_sum[inst_id]   += final_mid
            twap_count[inst_id] += 1
            vwap = round(twap_sum[inst_id] / twap_count[inst_id], 5)

            market_snapshot[inst_id] = {
                "bid":    bid,
                "ask":    ask,
                "mid":    final_mid,
                "change": round(final_mid - session_open[inst_id], 5),
                "vwap":   vwap,
                "ts":     timestamp,
            }

        # Save to Redis
        if r:
            json_data = json.dumps(market_snapshot)
            r.set(REDIS_KEY_LATEST_PRICES, json_data)
            r.publish(REDIS_KEY_MARKET_DATA, json_data)

        time.sleep(1)

def start_fix_engine():
    """
    Main Process: Listens for incoming orders.
    """
    print(f"FIX Engine Started. Listening on Queue: {REDIS_KEY_ORDER_QUEUE}", flush=True)

    # --- START THE MARKET DATA THREAD ---
    # daemon=True means this thread will die automatically if the main program crashes
    md_thread = threading.Thread(target=run_market_data_simulator, daemon=True)
    md_thread.start()
    # ------------------------------------

    while True:
        # Blocking Pop: Waits here until an order arrives
        if r:
            result = r.brpop(REDIS_KEY_ORDER_QUEUE, timeout=1)

            if result:
                _, data = result
                try:
                    order = json.loads(data)
                    print(f"Backend processing: {order['side']} {order['qty']} {order['symbol']} (ID: {order['clOrdID']})", flush=True)
                    # Here you would normally send to QuickFIX
                except json.JSONDecodeError:
                    print(f"Error decoding JSON: {data}", flush=True)
            
        time.sleep(0.01)

if __name__ == "__main__":
    start_fix_engine()