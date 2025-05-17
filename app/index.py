from dash import html, dcc
import dash_bootstrap_components as dbc
import dash
from dash.dependencies import Input, Output, State


def create_layout():
    """Create the main layout for the application."""
    return dbc.Container([
        # Add viewport meta tag for proper responsive behavior
        html.Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        
        dcc.Location(id="url"),

        # Navigation bar
        dbc.Navbar(
            [
                # Brand with logo on the left
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
                
                # Toggle button for mobile view
                dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
                
                # Navigation links that collapse on mobile
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
        ),

        html.Br(),

        dash.page_container,

    ], fluid=True)

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