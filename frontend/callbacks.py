import json
import time
import uuid
from dash import Input, Output, State, MATCH, ALL, ctx, no_update
from app import app
from shared.redis_client import get_redis_connection
from shared.constants import REDIS_KEY_ORDER_QUEUE

# Initialize Redis connection once
r = get_redis_connection()

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
        
        # Handle Clear
        if triggered_id.get('type') == 'btn-clear':
            return 0
        
        # Handle Add
        increment = triggered_id.get('val')
        current_val = current_val if current_val else 0
        return current_val + increment

    # -----------------------------------------------------------
    # CALLBACK 2A: Row Actions (Redis Push + Row UI)
    # Uses MATCH to stay isolated to the specific row.
    # -----------------------------------------------------------
    @app.callback(
        Output({'type': 'btn-cancel', 'index': MATCH}, 'style'),
        [Input({'type': 'btn-buy', 'index': MATCH}, 'n_clicks'),
         Input({'type': 'btn-sell', 'index': MATCH}, 'n_clicks'),
         Input({'type': 'btn-cancel', 'index': MATCH}, 'n_clicks')],
        [State({'type': 'qty-input', 'index': MATCH}, 'value'),
         State({'type': 'qty-input', 'index': MATCH}, 'id')]
    )
    def handle_row_logic(buy_click, sell_click, cancel_click, qty, id_dict):

        triggered_id = ctx.triggered_id
        if not triggered_id: return no_update

        inst = id_dict['index']
        action = triggered_id['type']
        
        # Logic: If Buy/Sell clicked -> Push to Redis & Show Cancel Button
        if (action == 'btn-buy' or action == 'btn-sell') and qty > 0:
            side = "BUY" if action == 'btn-buy' else "SELL"

            # --- REDIS PUSH ---
            if r:
                clOrdID = str(uuid.uuid4())
                order_payload = {
                    'clOrdID': clOrdID,
                    'symbol': inst,
                    'side': side,
                    'qty': qty,
                    'timestamp': time.time()
                }
                # Push to the 'outgoing_orders' list
                r.lpush(REDIS_KEY_ORDER_QUEUE, json.dumps(order_payload))

            return {'display': 'block'} # Show Cancel Button

        # Logic: If Cancel clicked -> Hide Cancel Button
        elif action == 'btn-cancel':
            # In a real app, you would push a CancelRequest to Redis here
            return {'display': 'none'} # Hide Cancel Button

        return no_update

    # -----------------------------------------------------------
    # CALLBACK 2B: Global Logging
    # Uses ALL to listen to ANY button click and update the global footer.
    # -----------------------------------------------------------
    @app.callback(
        [Output('status-bar', 'children'),
         Output('display-raw', 'children'),
         Output('display-parsed', 'children')],
        [Input({'type': 'btn-buy', 'index': ALL}, 'n_clicks'),
         Input({'type': 'btn-sell', 'index': ALL}, 'n_clicks'),
         Input({'type': 'btn-cancel', 'index': ALL}, 'n_clicks')],
        [State({'type': 'qty-input', 'index': ALL}, 'value'),
         State({'type': 'qty-input', 'index': ALL}, 'id')]
    )
    def update_global_log(buys, sells, cancels, all_qtys, all_ids):
        if not ctx.triggered: return no_update, no_update, no_update
        
        trigger = ctx.triggered_id
        action = trigger['type']
        inst = trigger['index']
        
        # Find the quantity for the specific row that was clicked
        qty = 0
        for i, id_dict in enumerate(all_ids):
            if id_dict['index'] == inst:
                qty = all_qtys[i]
                break

        status = ""
        raw = ""
        parsed = ""

        if action == 'btn-cancel':
            status = f"ORDER CANCELLED FOR {inst}"
            parsed = f"Action: Cancel\nSymbol: {inst}"
            
        elif (action == 'btn-buy' or action == 'btn-sell') and qty > 0:
            side = "BUY" if action == 'btn-buy' else "SELL"
            status = f"SENT TO REDIS: {side} {qty} {inst}"
            raw = f"8=FIX.4.4|35=D|55={inst}|38={qty}..."
            parsed = f"MsgType = NewOrderSingle\nSymbol = {inst}\nQty = {qty}\n(Sent to Backend)"

        return status, raw, parsed

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