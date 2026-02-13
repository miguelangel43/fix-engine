from dash import html, dcc
import dash_bootstrap_components as dbc
from shared.constants import INSTRUMENTS

# Group instruments by type for tab rendering
_TREAS   = [(i, l, d, p) for i, l, d, p, t in INSTRUMENTS if t == "TREAS"]
_FUTURES = [(i, l, d, p) for i, l, d, p, t in INSTRUMENTS if t == "FUT" and i.startswith(("TU", "TY", "US"))]
_SOFR    = [(i, l, d, p) for i, l, d, p, t in INSTRUMENTS if t == "FUT" and i.startswith("SR")]

def render_instrument_row(inst_id, label, description):
    return dbc.Row([
        # Col 1: Instrument Info
        dbc.Col([
            html.Div(label, className="inst-header"),
            html.Div(description, className="inst-desc")
        ], width=2),

        # Col 2: Live Price (bid / ask + mid)
        dbc.Col([
            html.Div(id={'type': 'price-display', 'index': inst_id}, className="price-display")
        ], width=2),

        # Col 3: Quantity Inputs & Quick Buttons
        dbc.Col([
            dbc.Row([
                dbc.Col(dbc.Input(
                    id={'type': 'qty-input', 'index': inst_id},
                    type="number", value=0, min=0, step=1,
                    style={'backgroundColor': '#222', 'color': 'white', 'border': '1px solid #444'}
                ), width=10),
                dbc.Col(html.Div("MM", style={'lineHeight': '38px', 'color': '#666'}), width=2),
            ]),
            dbc.Row([
                dbc.Col(dbc.Button("5",  id={'type': 'btn-add', 'index': inst_id, 'val': 5},  className="btn-tertiary w-100 btn-sm")),
                dbc.Col(dbc.Button("10", id={'type': 'btn-add', 'index': inst_id, 'val': 10}, className="btn-tertiary w-100 btn-sm")),
                dbc.Col(dbc.Button("25", id={'type': 'btn-add', 'index': inst_id, 'val': 25}, className="btn-tertiary w-100 btn-sm")),
                dbc.Col(dbc.Button("\u21ba", id={'type': 'btn-clear', 'index': inst_id},      className="btn-tertiary w-100 btn-sm")),
            ], className="mt-1 g-1"),
        ], width=3),

        # Col 4: Buy/Sell + Stage buttons
        dbc.Col([
            dbc.Row([
                dbc.Col(dbc.Button("BUY",  id={'type': 'btn-buy',  'index': inst_id}, className="btn-buy  w-100")),
                dbc.Col(dbc.Button("SELL", id={'type': 'btn-sell', 'index': inst_id}, className="btn-sell w-100")),
            ], className="g-1"),
            dbc.Row([
                dbc.Col(dbc.Button(
                    "BUY 1 \u2193",
                    id={'type': 'btn-buy-1t', 'index': inst_id},
                    className="btn-stage w-100 btn-sm mt-1",
                    title="Stage limit buy 1 tick below best bid"
                )),
            ]),
        ], width=3),

        # Col 5: Cancel Button (hidden by default)
        dbc.Col([
            dbc.Button("CANCEL", id={'type': 'btn-cancel', 'index': inst_id}, className="btn-cancel w-100", style={'display': 'none'})
        ], width=1)
    ], className="mb-4 align-items-center border-bottom border-secondary pb-3")


def create_layout():
    return dbc.Container([
        dcc.Store(id='store-active-orders', data={}),
        dcc.Store(id='store-last-msg', data={}),
        dcc.Interval(id='price-interval', interval=1000, n_intervals=0),

        # Top Bar
        dbc.Row([
            dbc.Col(html.Div("\U0001f7e2 CONNECTED to GATEWAY", style={'color': '#00FF00', 'fontWeight': 'bold'}), width=10),
            dbc.Col(dbc.Button("CANCEL ALL", id="btn-cancel-all", color="danger", className="w-100"), width=2)
        ], className="py-3"),

        # Tabs
        dbc.Tabs([
            dbc.Tab(label="TREAS", tab_style={'borderRadius': '0px'}, children=[
                html.Br(),
                *[render_instrument_row(i, l, d) for i, l, d, _ in _TREAS],
            ]),
            dbc.Tab(label="TREAS FUTURES", children=[
                html.Br(),
                *[render_instrument_row(i, l, d) for i, l, d, _ in _FUTURES],
            ]),
            dbc.Tab(label="SOFR FUTURES", children=[
                html.Br(),
                *[render_instrument_row(i, l, d) for i, l, d, _ in _SOFR],
            ]),
        ]),

        html.Hr(),

        # Wire Trace Section
        html.H4("WIRE TRACE", className="mt-3", style={'color': '#888'}),
        dbc.Row([
            dbc.Col([html.Div("Raw Wire Trace", className="text-muted small"), html.Div(id="display-raw", className="trace-box")], width=6),
            dbc.Col([html.Div("Parsed Fields", className="text-muted small"), html.Div(id="display-parsed", className="trace-box")], width=6),
        ]),

        html.Div("READY TO TRADE", id="status-bar", className="terminal-alert")
    ], fluid=True, style={'maxWidth': '98%'})
