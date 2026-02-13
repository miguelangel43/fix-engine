"""Treasury Trading FIX Engine — CLI entry point and orchestration.

Usage:
    python backend/engine.py start [--verbose] [--no-market-data] [--fix-config PATH]
    python backend/engine.py order --side BUY --qty 10 --symbol 10Y [--price 99.5]
    python backend/engine.py prices [--symbol 10Y] [--format table|json]
"""

import argparse
import json
import logging
import os
import random
import signal
import sys
import threading
import time
import uuid

import quickfix as fix

from shared.redis_client import get_redis_connection
from shared.constants import (
    REDIS_KEY_ORDER_QUEUE,
    REDIS_KEY_MARKET_DATA,
    REDIS_KEY_LATEST_PRICES,
    INSTRUMENTS,
)
from backend.fix_app import FixApplication
from backend.message_parser import order_to_fix

logger = logging.getLogger("engine")

# ---------------------------------------------------------------------------
# Market Data Simulator (moved verbatim from fix_engine.py)
# ---------------------------------------------------------------------------

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


def run_market_data_simulator(redis_conn):
    """Generate simulated market data for all instruments and publish to Redis."""
    logger.info("Market Data Simulator Started.")

    fair_values  = {inst_id: base_price for inst_id, _, _, base_price, _ in INSTRUMENTS}
    session_open = dict(fair_values)
    twap_sum     = dict(fair_values)
    twap_count   = {inst_id: 1 for inst_id in fair_values}

    while True:
        timestamp = time.time()
        market_snapshot = {}

        for inst_id, _, _, _, _ in INSTRUMENTS:
            walk_step, half_spread = SPREAD_CONFIG[inst_id]

            fair_values[inst_id] += random.uniform(-walk_step, walk_step)

            mid = fair_values[inst_id]
            bid = round(mid - half_spread, 5)
            ask = round(mid + half_spread, 5)
            final_mid = round((bid + ask) / 2, 5)

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

        if redis_conn:
            json_data = json.dumps(market_snapshot)
            redis_conn.set(REDIS_KEY_LATEST_PRICES, json_data)
            redis_conn.publish(REDIS_KEY_MARKET_DATA, json_data)

        time.sleep(1)


# ---------------------------------------------------------------------------
# Order Listener
# ---------------------------------------------------------------------------

def run_order_listener(redis_conn, fix_app, verbose=False):
    """Pop orders from Redis and route through QuickFIX or log in SIM mode."""
    logger.info(f"Order listener started. Queue: {REDIS_KEY_ORDER_QUEUE}")

    while True:
        if not redis_conn:
            time.sleep(1)
            continue

        result = redis_conn.brpop(REDIS_KEY_ORDER_QUEUE, timeout=1)
        if not result:
            continue

        _, data = result
        try:
            order = json.loads(data)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in order queue: {data}")
            continue

        symbol  = order.get("symbol", "?")
        side    = order.get("side", "?")
        qty     = order.get("qty", 0)
        clOrdID = order.get("clOrdID", "?")

        if fix_app and fix_app.is_logged_on:
            fix_msg = order_to_fix(order, fix_app.session_id)
            sent = fix_app.send_order(fix_msg)
            if sent:
                logger.info(f"FIX SENT: {side} {qty} {symbol} (ID: {clOrdID})")
            else:
                logger.warning(f"FIX SEND FAILED: {side} {qty} {symbol} (ID: {clOrdID})")
        else:
            logger.info(f"SIM MODE: {side} {qty} {symbol} (ID: {clOrdID})")
            if verbose:
                logger.debug(f"  Full order: {order}")

        time.sleep(0.01)


# ---------------------------------------------------------------------------
# CLI: start
# ---------------------------------------------------------------------------

def cmd_start(args):
    """Start the full engine: QuickFIX initiator + market data + order listener."""
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stdout,
    )

    # Redis
    if args.redis_host:
        os.environ["REDIS_HOST"] = args.redis_host
    redis_conn = get_redis_connection()

    # QuickFIX
    fix_app = FixApplication()
    config_path = args.fix_config
    logger.info(f"Loading QuickFIX config from: {config_path}")

    settings = fix.SessionSettings(config_path)
    store_factory = fix.FileStoreFactory(settings)
    if args.verbose:
        log_factory = fix.ScreenLogFactory(settings)
    else:
        log_factory = fix.FileLogFactory(settings)

    initiator = fix.SocketInitiator(fix_app, store_factory, settings, log_factory)

    logger.info("Starting QuickFIX initiator...")
    initiator.start()

    # Market data simulator thread
    if not args.no_market_data:
        md_thread = threading.Thread(
            target=run_market_data_simulator,
            args=(redis_conn,),
            daemon=True,
        )
        md_thread.start()

    # Graceful shutdown
    def shutdown(sig, frame):
        logger.info("Shutting down...")
        initiator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Order listener runs on main thread
    run_order_listener(redis_conn, fix_app, verbose=args.verbose)


# ---------------------------------------------------------------------------
# CLI: order
# ---------------------------------------------------------------------------

def cmd_order(args):
    """Submit an order directly to the Redis queue."""
    if args.redis_host:
        os.environ["REDIS_HOST"] = args.redis_host
    redis_conn = get_redis_connection()
    if not redis_conn:
        print("ERROR: Cannot connect to Redis", file=sys.stderr)
        sys.exit(1)

    order = {
        "clOrdID":   str(uuid.uuid4()),
        "symbol":    args.symbol,
        "side":      args.side.upper(),
        "qty":       args.qty,
        "ordType":   args.type.upper(),
        "timestamp": time.time(),
    }
    if args.price is not None:
        order["price"]   = args.price
        order["ordType"] = "LIMIT"

    redis_conn.lpush(REDIS_KEY_ORDER_QUEUE, json.dumps(order))
    print(
        f"Order submitted: {order['side']} {order['qty']} {order['symbol']} "
        f"({order['ordType']}) ID={order['clOrdID']}"
    )


# ---------------------------------------------------------------------------
# CLI: prices
# ---------------------------------------------------------------------------

def cmd_prices(args):
    """Stream live prices from Redis to the terminal."""
    if args.redis_host:
        os.environ["REDIS_HOST"] = args.redis_host
    redis_conn = get_redis_connection()
    if not redis_conn:
        print("ERROR: Cannot connect to Redis", file=sys.stderr)
        sys.exit(1)

    try:
        while True:
            raw = redis_conn.get(REDIS_KEY_LATEST_PRICES)
            if not raw:
                print("Waiting for market data...", end="\r")
                time.sleep(1)
                continue

            prices = json.loads(raw)

            if args.format == "json":
                if args.symbol:
                    filtered = {k: v for k, v in prices.items() if k == args.symbol}
                    print(json.dumps(filtered, indent=2))
                else:
                    print(json.dumps(prices, indent=2))
            else:
                # Table format — clear screen and redraw
                print("\033[2J\033[H", end="")
                print(f"{'Symbol':<10} {'Bid':>12} {'Ask':>12} {'Mid':>12} {'Change':>10} {'VWAP':>12}")
                print("-" * 72)
                for inst_id, _, _, _, _ in INSTRUMENTS:
                    if args.symbol and inst_id != args.symbol:
                        continue
                    d = prices.get(inst_id)
                    if d:
                        print(
                            f"{inst_id:<10} "
                            f"{d['bid']:>12.5f} "
                            f"{d['ask']:>12.5f} "
                            f"{d['mid']:>12.5f} "
                            f"{d['change']:>+10.5f} "
                            f"{d['vwap']:>12.5f}"
                        )

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="fix-engine",
        description="Treasury Trading FIX Engine",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- start ---
    p_start = subparsers.add_parser("start", help="Run the full FIX engine")
    p_start.add_argument("--redis-host", default=None,
                         help="Redis host (overrides REDIS_HOST env)")
    p_start.add_argument("--fix-config", default="backend/config/quickfix.cfg",
                         help="Path to QuickFIX config file")
    p_start.add_argument("--no-market-data", action="store_true",
                         help="Disable the market data simulator")
    p_start.add_argument("--verbose", "-v", action="store_true",
                         help="Enable debug logging + QuickFIX screen log")
    p_start.set_defaults(func=cmd_start)

    # --- order ---
    p_order = subparsers.add_parser("order", help="Submit an order via CLI")
    p_order.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    p_order.add_argument("--qty", required=True, type=int)
    p_order.add_argument("--symbol", required=True)
    p_order.add_argument("--price", type=float, default=None,
                         help="Limit price (implies LIMIT order type)")
    p_order.add_argument("--type", default="MARKET", choices=["MARKET", "LIMIT"])
    p_order.add_argument("--redis-host", default=None)
    p_order.set_defaults(func=cmd_order)

    # --- prices ---
    p_prices = subparsers.add_parser("prices", help="Stream live prices to terminal")
    p_prices.add_argument("--symbol", default=None, help="Filter to a single symbol")
    p_prices.add_argument("--format", default="table", choices=["table", "json"])
    p_prices.add_argument("--redis-host", default=None)
    p_prices.set_defaults(func=cmd_prices)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
