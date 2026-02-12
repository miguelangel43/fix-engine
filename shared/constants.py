# Redis Keys
REDIS_KEY_ORDER_QUEUE = "outgoing_orders"      # List: Frontend pushes, Backend pops
REDIS_KEY_MARKET_DATA = "market_data_stream"   # PubSub: Backend publishes, Frontend subscribes
REDIS_KEY_LATEST_PRICES = "market_data_snapshot"
REDIS_KEY_SYSTEM_LOGS = "system_logs"          # Stream/List: Common logging

# Message Types
MSG_TYPE_NEW_ORDER = "NewOrderSingle"
MSG_TYPE_CANCEL = "OrderCancelRequest"