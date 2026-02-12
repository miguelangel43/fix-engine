from dash import html, dcc
import dash_bootstrap_components as dbc

# Helper function to generate instrument rows
def render_instrument_row(inst_id, label, description, price, sec_type="TNOTE"):
    return dbc.Row([
        # Col 1: Instrument Info
        dbc.Col([
            html.Div(label, className="inst-header"),
            html.Div(description, className="inst-desc")
        ], width=2),

        # Col 2: Quantity Inputs & Quick Buttons
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
                dbc.Col(dbc.Button("5", id={'type': 'btn-add', 'index': inst_id, 'val': 5}, className="btn-tertiary w-100 btn-sm")),
                dbc.Col(dbc.Button("10", id={'type': 'btn-add', 'index': inst_id, 'val': 10}, className="btn-tertiary w-100 btn-sm")),
                dbc.Col(dbc.Button("25", id={'type': 'btn-add', 'index': inst_id, 'val': 25}, className="btn-tertiary w-100 btn-sm")),
                dbc.Col(dbc.Button("↺", id={'type': 'btn-clear', 'index': inst_id}, className="btn-tertiary w-100 btn-sm")),
            ], className="mt-1 g-1"),
        ], width=4),

        # Col 3: Buy/Sell Buttons
        dbc.Col([
            dbc.Row([
                dbc.Col(dbc.Button("BUY", id={'type': 'btn-buy', 'index': inst_id}, className="btn-buy w-100")),
                dbc.Col(dbc.Button("SELL", id={'type': 'btn-sell', 'index': inst_id}, className="btn-sell w-100")),
            ], className="g-1")
        ], width=3),

        # Col 4: Cancel Button (Hidden by default)
        dbc.Col([
            dbc.Button("CANCEL", id={'type': 'btn-cancel', 'index': inst_id}, className="btn-cancel w-100", style={'display': 'none'})
        ], width=2)
    ], className="mb-4 align-items-center border-bottom border-secondary pb-3")

def create_layout():
    return dbc.Container([
        dcc.Store(id='store-active-orders', data={}),
        dcc.Store(id='store-last-msg', data={}),

        # Top Bar
        dbc.Row([
            dbc.Col(html.Div("🟢 CONNECTED to GATEWAY", style={'color': '#00FF00', 'fontWeight': 'bold'}), width=10),
            dbc.Col(dbc.Button("CANCEL ALL", id="btn-cancel-all", color="danger", className="w-100"), width=2)
        ], className="py-3"),

        # Tabs
        dbc.Tabs([
            dbc.Tab(label="TREAS", tab_style={'borderRadius': '0px'}, children=[
                html.Br(),
                render_instrument_row("2Y", "2Y", "T 3 ½ 01/31/28", 99.875),
                render_instrument_row("3Y", "3Y", "T 4 ¼ 02/15/27", 99.10),
                render_instrument_row("5Y", "5Y", "T 4 ⅛ 01/31/30", 98.50),
                render_instrument_row("10Y", "10Y", "T 3 ⅞ 12/15/33", 96.25),
                render_instrument_row("30Y", "30Y", "T 4 ¼ 05/15/54", 95.80),
            ]),
            dbc.Tab(label="TREAS FUTURES", children=[
                html.Br(),
                render_instrument_row("TUH6", "TU", "2Y NOTE FUT MAR26", 102.12, "FUT"),
                render_instrument_row("TYH6", "TY", "10Y NOTE MAR26", 110.15, "FUT"),
                render_instrument_row("USH6", "US", "30Y BOND MAR26", 119.05, "FUT"),
            ]),
            dbc.Tab(label="SOFR FUTURES", children=[
                html.Br(),
                render_instrument_row("SR3H6", "SFR H6", "3M SOFR MAR26", 96.50, "FUT"),
                render_instrument_row("SR3Z6", "SFR Z6", "3M SOFR DEC26", 96.35, "FUT"),
            ])
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