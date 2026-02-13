import json
import time
import uuid
from dash import html, Input, Output, State, MATCH, ALL, ctx, no_update
from app import app
from shared.redis_client import get_redis_connection
from shared.constants import (
    REDIS_KEY_ORDER_QUEUE, REDIS_KEY_LATEST_PRICES,
    INSTRUMENTS, QUOTE_STYLES, TICK_SIZES,
)

# Initialize Redis connection once
r = get_redis_connection()


# -----------------------------------------------------------
# Price Formatting Helpers
# -----------------------------------------------------------

def _fmt(price: float, style: str) -> str:
    """Convert a decimal price to the market-standard display string."""
    if style == "decimal3":
        return f"{price:.3f}"

    handle = int(price)
    frac   = price - handle

    if style == "32nds_whole":
        n = round(frac * 32)
        if n == 32:
            handle, n = handle + 1, 0
        return f"{handle}-{n:02d}"

    if style == "32nds_half":
        # Round to nearest half-32nd (1/64)
        n2 = round(frac * 64)
        w, h = n2 // 2, n2 % 2
        if w == 32:
            handle, w, h = handle + 1, 0, 0
        return f"{handle}-{w:02d}+" if h else f"{handle}-{w:02d}"

    if style == "32nds_eighth":
        # Round to nearest eighth-of-32nd (1/256); suffix 4 → '+'
        n8 = round(frac * 256)
        w, e = n8 // 8, n8 % 8
        if w == 32:
            handle, w, e = handle + 1, 0, 0
        sfx = {0: '', 1: '1', 2: '2', 3: '3', 4: '+', 5: '5', 6: '6', 7: '7'}[e]
        return f"{handle}-{w:02d}{sfx}"

    return f"{price:.3f}"  # fallback


def register_callbacks():

    # -----------------------------------------------------------
    # CALLBACK 1: Handle Quantity Buttons (+5, +10, +25, Clear)
    # -----------------------------------------------------------
    @app.callback(
        Output({'type': 'qty-input', 'index': MATCH}, 'value'),
        [Input({'type': 'btn-add', 'index': MATCH, 'val': ALL}, 'n_clicks'),
         Input({'type': 'btn-clear', 'index': MATCH}, 'n_clicks')],
        [State({'type': 'qty-input', 'index': MATCH}, 'value')]
    )
    def update_qty(add_clicks, clear_click, current_val):
        triggered_id = ctx.triggered_id
        if not triggered_id: return no_update

        if triggered_id.get('type') == 'btn-clear':
            return 0

        increment = triggered_id.get('val')
        current_val = current_val if current_val else 0
        return current_val + increment

    # -----------------------------------------------------------
    # CALLBACK 2A: Row Actions (Redis Push + Row UI)
    # -----------------------------------------------------------
    @app.callback(
        Output({'type': 'btn-cancel', 'index': MATCH}, 'style'),
        [Input({'type': 'btn-buy',    'index': MATCH}, 'n_clicks'),
         Input({'type': 'btn-sell',   'index': MATCH}, 'n_clicks'),
         Input({'type': 'btn-cancel', 'index': MATCH}, 'n_clicks'),
         Input({'type': 'btn-buy-1t', 'index': MATCH}, 'n_clicks')],
        [State({'type': 'qty-input',  'index': MATCH}, 'value'),
         State({'type': 'qty-input',  'index': MATCH}, 'id')]
    )
    def handle_row_logic(buy_click, sell_click, cancel_click, buy1t_click, qty, id_dict):
        triggered_id = ctx.triggered_id
        if not triggered_id: return no_update

        inst   = id_dict['index']
        action = triggered_id['type']

        # BUY / SELL market order
        if action in ('btn-buy', 'btn-sell') and qty and qty > 0:
            side = "BUY" if action == 'btn-buy' else "SELL"
            if r:
                r.lpush(REDIS_KEY_ORDER_QUEUE, json.dumps({
                    'clOrdID':  str(uuid.uuid4()),
                    'symbol':   inst,
                    'side':     side,
                    'qty':      qty,
                    'ordType':  'MARKET',
                    'timestamp': time.time(),
                }))
            return {'display': 'block'}

        # BUY 1 ↓ — limit buy 1 tick below best bid
        if action == 'btn-buy-1t' and r:
            raw_prices = r.get(REDIS_KEY_LATEST_PRICES)
            inst_data  = json.loads(raw_prices).get(inst, {}) if raw_prices else {}
            bid        = inst_data.get('bid', 0)
            tick       = TICK_SIZES.get(inst, 1/32)
            limit_px   = round(bid - tick, 6)
            r.lpush(REDIS_KEY_ORDER_QUEUE, json.dumps({
                'clOrdID':   str(uuid.uuid4()),
                'symbol':    inst,
                'side':      'BUY',
                'qty':       1,
                'ordType':   'LIMIT',
                'price':     limit_px,
                'timestamp': time.time(),
            }))
            return {'display': 'block'}

        # CANCEL
        if action == 'btn-cancel':
            return {'display': 'none'}

        return no_update

    # -----------------------------------------------------------
    # CALLBACK 2B: Global Logging
    # -----------------------------------------------------------
    @app.callback(
        [Output('status-bar',    'children'),
         Output('display-raw',   'children'),
         Output('display-parsed','children')],
        [Input({'type': 'btn-buy',    'index': ALL}, 'n_clicks'),
         Input({'type': 'btn-sell',   'index': ALL}, 'n_clicks'),
         Input({'type': 'btn-cancel', 'index': ALL}, 'n_clicks'),
         Input({'type': 'btn-buy-1t', 'index': ALL}, 'n_clicks')],
        [State({'type': 'qty-input',  'index': ALL}, 'value'),
         State({'type': 'qty-input',  'index': ALL}, 'id')]
    )
    def update_global_log(buys, sells, cancels, buy1ts, all_qtys, all_ids):
        if not ctx.triggered: return no_update, no_update, no_update

        trigger = ctx.triggered_id
        action  = trigger['type']
        inst    = trigger['index']

        qty = 0
        for i, id_dict in enumerate(all_ids):
            if id_dict['index'] == inst:
                qty = all_qtys[i]
                break

        if action == 'btn-cancel':
            return f"ORDER CANCELLED FOR {inst}", "", f"Action: Cancel\nSymbol: {inst}"

        if action == 'btn-buy-1t':
            raw_prices = r.get(REDIS_KEY_LATEST_PRICES) if r else None
            inst_data  = json.loads(raw_prices).get(inst, {}) if raw_prices else {}
            bid        = inst_data.get('bid', 0)
            tick       = TICK_SIZES.get(inst, 1/32)
            limit_px   = round(bid - tick, 6)
            style      = QUOTE_STYLES.get(inst, 'decimal3')
            px_str     = _fmt(limit_px, style)
            status     = f"STAGED: BUY 1 {inst} @ {px_str} (1 tick below bid)"
            raw        = f"8=FIX.4.4|35=D|55={inst}|38=1|40=2|44={limit_px}..."
            parsed     = f"MsgType = NewOrderSingle\nSymbol = {inst}\nQty = 1\nOrdType = LIMIT\nPrice = {px_str}"
            return status, raw, parsed

        if action in ('btn-buy', 'btn-sell') and qty and qty > 0:
            side   = "BUY" if action == 'btn-buy' else "SELL"
            status = f"SENT: {side} {qty} {inst}"
            raw    = f"8=FIX.4.4|35=D|55={inst}|38={qty}|40=1..."
            parsed = f"MsgType = NewOrderSingle\nSymbol = {inst}\nQty = {qty}\nOrdType = MARKET"
            return status, raw, parsed

        return no_update, no_update, no_update

    # -----------------------------------------------------------
    # CALLBACK 3: Global Cancel All
    # -----------------------------------------------------------
    @app.callback(
        Output('status-bar', 'children', allow_duplicate=True),
        Input('btn-cancel-all', 'n_clicks'),
        prevent_initial_call=True
    )
    def cancel_all(n):
        return "*** SYSTEM HALT: ALL ORDERS CANCELLED ***"

    # -----------------------------------------------------------
    # CALLBACK 4: Live Price Updates (polls Redis every second)
    # Returns price displays in DOM order = INSTRUMENTS order.
    # -----------------------------------------------------------
    @app.callback(
        Output({'type': 'price-display', 'index': ALL}, 'children'),
        Input('price-interval', 'n_intervals')
    )
    def update_prices(n_intervals):
        empty = ["-"] * len(INSTRUMENTS)
        if not r:
            return empty

        raw = r.get(REDIS_KEY_LATEST_PRICES)
        if not raw:
            return empty

        prices = json.loads(raw)
        result = []
        for inst_id, *_ in INSTRUMENTS:
            data  = prices.get(inst_id)
            style = QUOTE_STYLES.get(inst_id, "decimal3")
            if not data:
                result.append(html.Span("-", style={"color": "#555"}))
                continue

            change    = data.get("change", 0)
            chg_class = "price-change-up" if change >= 0 else "price-change-down"
            chg_sign  = "+" if change >= 0 else ""

            result.append(html.Div([
                html.Span(_fmt(data['bid'],  style), className="price-bid"),
                html.Span(" / ",             style={"color": "#555"}),
                html.Span(_fmt(data['ask'],  style), className="price-ask"),
                html.Br(),
                html.Span(_fmt(data['mid'],  style), className="price-mid"),
                html.Br(),
                html.Span(f"{chg_sign}{change:.3f}", className=chg_class),
                html.Span("  V:",            className="price-mid"),
                html.Span(_fmt(data['vwap'], style), className="price-vwap"),
            ]))
        return result
