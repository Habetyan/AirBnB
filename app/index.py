from dash import html, dcc
import dash_bootstrap_components as dbc
import dash


def create_layout():
    """Create the main layout for the application."""
    return dbc.Container([
        dcc.Location(id="url"),

        # Navigation bar
        dbc.NavbarSimple(
            brand="Texas Airbnb Dashboard",
            brand_href="/",
            color="primary",
            dark=True,
            children=[
                dbc.NavItem(dbc.NavLink("Home", href="/")),
                dbc.NavItem(dbc.NavLink("Geo data Analysis", href="/geo_visualizations")),
            ],
        ),

        html.Br(),

        dash.page_container,

    ], fluid=True)