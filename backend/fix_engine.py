import time
import json
import redis
import os
import threading
import random

# --- SHARED IMPORTS ---
from shared.redis_client import get_redis_connection
from shared.constants import REDIS_KEY_ORDER_QUEUE, REDIS_KEY_MARKET_DATA, REDIS_KEY_LATEST_PRICES

r = get_redis_connection()

# Initial Prices for our simulation
market_prices = {
    "2Y": 100.00,
    "5Y": 100.00,
    "10Y": 100.00,
    "30Y": 100.00
}

def run_market_data_simulator():
    print(f"Market Data Simulator Started.", flush=True)
    
    # Base "Fair Value" to start with
    fair_values = {
        "2Y": 100.00,
        "5Y": 100.00,
        "10Y": 100.00,
        "30Y": 100.00
    }

    while True:
        timestamp = time.time()
        market_snapshot = {}

        for sym in fair_values:
            # 1. Move the "Fair Value" (Random Walk)
            move = random.uniform(-0.02, 0.02)
            fair_values[sym] += move
            
            # 2. Calculate Spread (Random tightness)
            # e.g., Spread between 1 cent and 3 cents
            spread = random.uniform(0.01, 0.03)
            
            # 3. Derive Bid/Ask
            mid = fair_values[sym]
            bid = round(mid - (spread / 2), 3)
            ask = round(mid + (spread / 2), 3)
            
            # Re-calculate Mid to be exact center of rounded bid/ask
            final_mid = round((bid + ask) / 2, 3)

            market_snapshot[sym] = {
                "bid": bid,
                "ask": ask,
                "mid": final_mid,
                "ts": timestamp
            }

        # 4. Save to Redis
        if r:
            json_data = json.dumps(market_snapshot)
            
            # A) Save as a static key (For Dash to poll)
            r.set(REDIS_KEY_LATEST_PRICES, json_data)
            
            # B) Publish as a stream (For future websockets)
            r.publish(REDIS_KEY_MARKET_DATA, json_data)
            
        time.sleep(1) # Update every second

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