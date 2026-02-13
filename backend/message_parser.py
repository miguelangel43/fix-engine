"""Bidirectional FIX 4.4 <-> JSON conversion for order messages."""

import time
from datetime import datetime, timezone

import quickfix as fix

# Try to import FIX 4.4 message classes; fall back to manual construction
try:
    import quickfix44 as fix44
    HAS_FIX44 = True
except ImportError:
    HAS_FIX44 = False

# --- Lookup tables ---

SIDE_MAP = {"BUY": fix.Side_BUY, "SELL": fix.Side_SELL}
SIDE_REVERSE = {fix.Side_BUY: "BUY", fix.Side_SELL: "SELL"}

ORD_TYPE_MAP = {"MARKET": fix.OrdType_MARKET, "LIMIT": fix.OrdType_LIMIT}


# --- JSON → FIX ---

def order_to_fix(order_dict: dict, session_id: fix.SessionID) -> fix.Message:
    """Build a FIX 4.4 NewOrderSingle (35=D) from a JSON order dict.

    Expected keys: clOrdID, symbol, side, qty, ordType, price (optional), timestamp
    """
    if HAS_FIX44:
        msg = fix44.NewOrderSingle()
    else:
        msg = fix.Message()
        msg.getHeader().setField(fix.BeginString("FIX.4.4"))
        msg.getHeader().setField(fix.MsgType("D"))

    msg.setField(fix.ClOrdID(order_dict["clOrdID"]))
    msg.setField(fix.Symbol(order_dict["symbol"]))
    msg.setField(fix.Side(SIDE_MAP[order_dict["side"]]))
    msg.setField(fix.OrderQty(order_dict["qty"]))
    msg.setField(fix.OrdType(ORD_TYPE_MAP.get(order_dict.get("ordType", "MARKET"), fix.OrdType_MARKET)))
    msg.setField(fix.HandlInst(fix.HandlInst_AUTOMATED_EXECUTION_ORDER_PRIVATE))

    if order_dict.get("ordType") == "LIMIT" and "price" in order_dict:
        msg.setField(fix.Price(order_dict["price"]))

    ts = order_dict.get("timestamp", time.time())
    utc_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y%m%d-%H:%M:%S")
    msg.setField(fix.StringField(60, utc_str))  # TransactTime

    return msg


def cancel_to_fix(cancel_dict: dict, session_id: fix.SessionID) -> fix.Message:
    """Build a FIX 4.4 OrderCancelRequest (35=F) from a cancel dict.

    Expected keys: origClOrdID, clOrdID, symbol, side
    """
    if HAS_FIX44:
        msg = fix44.OrderCancelRequest()
    else:
        msg = fix.Message()
        msg.getHeader().setField(fix.BeginString("FIX.4.4"))
        msg.getHeader().setField(fix.MsgType("F"))

    msg.setField(fix.OrigClOrdID(cancel_dict["origClOrdID"]))
    msg.setField(fix.ClOrdID(cancel_dict["clOrdID"]))
    msg.setField(fix.Symbol(cancel_dict["symbol"]))
    msg.setField(fix.Side(SIDE_MAP[cancel_dict["side"]]))

    utc_str = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H:%M:%S")
    msg.setField(fix.StringField(60, utc_str))  # TransactTime

    return msg


# --- FIX → JSON ---

# Tags we care about when parsing incoming messages (tag, json_key, converter)
_PARSE_FIELDS = [
    (35,  "msgType",   str),
    (11,  "clOrdID",   str),
    (37,  "orderID",   str),
    (17,  "execID",    str),
    (150, "execType",  str),
    (39,  "ordStatus", str),
    (55,  "symbol",    str),
    (54,  "side",      str),
    (38,  "qty",       float),
    (44,  "price",     float),
    (31,  "lastPx",    float),
    (32,  "lastQty",   float),
    (14,  "cumQty",    float),
    (151, "leavesQty", float),
    (58,  "text",      str),
]


def fix_to_dict(fix_msg: fix.Message) -> dict:
    """Convert any FIX message to a flat dict of parsed fields."""
    result = {}

    for tag, name, converter in _PARSE_FIELDS:
        field = fix.StringField(tag)
        try:
            fix_msg.getField(field)
            result[name] = converter(field.getString())
        except fix.FieldNotFound:
            pass

    # Humanize side value
    if "side" in result:
        result["side"] = SIDE_REVERSE.get(result["side"], result["side"])

    return result
