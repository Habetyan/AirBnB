from dash import Dash
import dash_bootstrap_components as dbc
import dash

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    use_pages=True,
    suppress_callback_exceptions=True,
)

app.title = "Texas Airbnb Dashboard"

from app.index import create_layout

app.layout = create_layout()
