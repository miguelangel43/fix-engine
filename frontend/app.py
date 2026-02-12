import dash
import dash_bootstrap_components as dbc

# Initialize the app with the CYBORG theme (dark mode base)
# suppress_callback_exceptions=True is useful for dynamic layouts
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], suppress_callback_exceptions=True)
server = app.server