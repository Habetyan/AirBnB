from dash import html, dcc
import dash_bootstrap_components as dbc
import dash
from dash.dependencies import Input, Output, State


def create_layout():
    """Create the main layout for the application."""
    navbar = dbc.Navbar(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Img(src="/assets/texas.png", height="40px"), 
                        width="auto",
                        className="me-2 ms-2"
                    ),
                    dbc.Col(
                        dbc.NavbarBrand("Texas Airbnb Dashboard", className="ms-2"),
                        width="auto"
                    ),
                ],
                align="center",
                className="g-0",
            ),
            dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
            dbc.Collapse(
                dbc.Nav(
                    [
                        dbc.NavItem(dbc.NavLink("Home", href="/")),
                        dbc.NavItem(dbc.NavLink("Geo data Analysis", href="/geo_visualizations")),
                        dbc.NavItem(dbc.NavLink("Technical Details", href="/technical")),
                    ],
                    className="ms-auto",
                    navbar=True
                ),
                id="navbar-collapse",
                navbar=True,
                is_open=False,
            ),
        ],
        color="primary",
        dark=True,
        className="mb-4",
        sticky="top",
    )

    content = dbc.Container(
        [
            dash.page_container
        ],
        fluid=True,
        className="mt-3"
    )

    return html.Div([
        html.Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        dcc.Location(id="url"),
        navbar,
        content
    ])

# Add callback for mobile navbar toggle
@dash.callback(
    Output("navbar-collapse", "is_open"),
    [Input("navbar-toggler", "n_clicks")],
    [State("navbar-collapse", "is_open")],
)
def toggle_navbar_collapse(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open