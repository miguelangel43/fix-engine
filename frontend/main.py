from app import app
from layout import create_layout
from callbacks import register_callbacks

# 1. Assign Layout
app.layout = create_layout()

# 2. Register Callbacks
register_callbacks()

# 3. Run Server
if __name__ == '__main__':
    # host='0.0.0.0' is REQUIRED for Docker
    app.run(debug=True, port=8050, host='0.0.0.0')