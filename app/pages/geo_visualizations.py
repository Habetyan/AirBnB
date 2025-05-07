import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from app.utils.data_loader import load_data
import matplotlib.pyplot as plt
import folium
import io
from math import radians, cos, sin, asin, sqrt

# Register  dash page
dash.register_page(
    __name__,
    path="/geo_visualizations",
    title="Geographic Analysis",
    name="Geo data Analysis"
)

df_cleaned = load_data()

#   Texas big  city centre coordinates
CITY_CENTERS = {
    'Houston': (29.7604, -95.3698),
    'San Antonio': (29.4241, -98.4936),
    'Dallas': (32.7767, -96.7970),
    'Austin': (30.2672, -97.7431),
    'Fort Worth': (32.7555, -97.3308),
    'El Paso': (31.7619, -106.4850),
    'Arlington': (32.7357, -97.1081),
    'Corpus Christi': (27.8006, -97.3964),
    'Plano': (33.0198, -96.6989),
    'Lubbock': (33.5779, -101.8552)
}


# Function to calculate distance using Haversine formula
def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r


# Create geo-visualization
def create_geo_visualization():
    df_geo = df_cleaned.dropna(subset=["latitude", "longitude"])


    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=[
            "KDE-like Density (Contour + Scatter)",
            "Density Heatmap (2D Histogram)"
        ],
        horizontal_spacing=0.1,
        specs=[[{}, {}]]
    )

    # KDE density plot (contour + scatter)
    fig.add_trace(
        go.Histogram2dContour(
            x=df_geo['longitude'],
            y=df_geo['latitude'],
            colorscale='Reds',
            contours=dict(showlabels=False),
            showscale=False,
            opacity=0.7
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df_geo['longitude'],
            y=df_geo['latitude'],
            mode='markers',
            marker=dict(size=2, color='blue', opacity=0.2),
            showlegend=False
        ),
        row=1, col=1
    )

    # Density heatmap
    fig.add_trace(
        go.Histogram2d(
            x=df_geo['longitude'],
            y=df_geo['latitude'],
            colorscale='Reds',
            showscale=True
        ),
        row=1, col=2
    )

    fig.update_layout(
        template='plotly_white',
        height=600,
        title_text='Airbnb Listings Density in Texas',
        showlegend=False
    )

    # Axis titles
    fig.update_xaxes(title_text='Longitude', row=1, col=1)
    fig.update_yaxes(title_text='Latitude', row=1, col=1)
    fig.update_xaxes(title_text='Longitude', row=1, col=2)
    fig.update_yaxes(title_text='Latitude', row=1, col=2)

    return fig


# Distance/ price visualization
def create_distance_price_visualization(selected_city='Houston'):
    center_lat, center_lon = CITY_CENTERS.get(selected_city, CITY_CENTERS['Houston'])
    df_with_distance = df_cleaned.dropna(subset=['latitude', 'longitude', 'average_rate_per_night']).copy()

    # Distance from city center for each listing
    df_with_distance['distance_km'] = df_with_distance.apply(
        lambda row: haversine(center_lon, center_lat, row['longitude'], row['latitude']),
        axis=1
    )


    #  95th percentile cutoff
    distance_cutoff = df_with_distance['distance_km'].quantile(0.95)
    df_filtered = df_with_distance[df_with_distance['distance_km'] <= distance_cutoff]

    # Scatter plot
    fig = px.scatter(
        df_filtered,
        x='distance_km',
        y='average_rate_per_night',
        color='bedrooms_count',
        size='bedrooms_count',
        hover_name='city',
        hover_data=['title', 'bedrooms_count'],
        title=f'Price vs. Distance from {selected_city} City Center',
        labels={
            'distance_km': 'Distance from City Center (km)',
            'average_rate_per_night': 'Average Rate per Night ($)',
            'bedrooms_count': 'Bedrooms'
        },
        color_continuous_scale='Viridis',
        opacity=0.7
    )

    fig.update_layout(
        height=500,
        template='plotly_white',
        xaxis_title='Distance from City Center (km)',
        yaxis_title='Average Rate per Night ($)'
    )

    #  trendline
    df_trend = df_filtered.copy()
    x = df_trend['distance_km']
    y = df_trend['average_rate_per_night']

    fig.update_traces(
        mode='markers',
        marker=dict(line=dict(width=0.5, color='white'))
    )

    fig.add_trace(
        go.Scatter(
            x=df_trend['distance_km'],
            y=df_trend['average_rate_per_night'].rolling(window=50).mean(),
            mode='lines',
            name='Price Trend',
            line=dict(color='red', width=2)
        )
    )

    return fig

def create_folium_map_html():
    city_avg_price = df_cleaned.groupby("city")["average_rate_per_night"].mean().reset_index()


    m = folium.Map(
        location=[df_cleaned["latitude"].mean(), df_cleaned["longitude"].mean()],
        zoom_start=6,
        tiles="OpenStreetMap"
    )

    # Circle markers for each city
    for _, row in city_avg_price.iterrows():
        city_data = df_cleaned[df_cleaned["city"] == row["city"]]
        lat_mean = city_data["latitude"].mean()
        lon_mean = city_data["longitude"].mean()

        # Sanity check for correct coordinates
        if not np.isnan(lat_mean) and not np.isnan(lon_mean):
            folium.CircleMarker(
                location=[lat_mean, lon_mean],
                radius=np.sqrt(row["average_rate_per_night"]) * 0.3,
                color="green",
                fill=True,
                fill_color="green",
                fill_opacity=0.3,
                popup=f"{row['city']}: ${row['average_rate_per_night']:.2f}",
            ).add_to(m)


    map_html = m._repr_html_()

    return map_html


#  layout for geo-visualization
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Geographic Analysis of Texas Airbnb Listings"),
            html.P("Visualizing the spatial distribution and price patterns of Airbnb properties across Texas"),
            html.Hr(),
        ])
    ]),

    #  Density visualizations
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Listing Density Analysis"),
                dbc.CardBody([
                    dcc.Graph(
                        id="geo-visualization",
                        figure=create_geo_visualization()
                    )
                ])
            ])
        ])
    ]),

    html.Br(),

    #  Distance/price plot
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Distance from City Center vs. Price"),
                dbc.CardBody([
                    html.P(
                        "This visualization shows how property prices vary with distance from major city centers in Texas."),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Select City Center:"),
                            dcc.Dropdown(
                                id="city-center-dropdown",
                                options=[{"label": city, "value": city} for city in CITY_CENTERS.keys()],
                                value="Houston",
                                className="mb-3"
                            ),
                        ], width=4)
                    ]),
                    dcc.Graph(
                        id="distance-price-visualization",
                        figure=create_distance_price_visualization()
                    )
                ])
            ])
        ])
    ]),

    html.Br(),

    # Folium map
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Average Price by City"),
                dbc.CardBody([
                    html.P(
                        "This map shows the average price per night for each city in Texas. The size of each circle represents the price."),
                    html.Div([
                        html.Iframe(
                            id="folium-map",
                            srcDoc=create_folium_map_html(),
                            style={
                                "width": "100%",
                                "height": "600px",
                                "border": "none"
                            }
                        )
                    ])
                ])
            ])
        ])
    ]),

    html.Br(),

    dbc.Row([
        dbc.Col([
            html.H4("Understanding the Visualizations"),
            html.P([
                "This page presents geographic visualizations of Texas Airbnb listings:",
                html.Ul([
                    html.Li([
                        html.Strong("KDE-like Density:"),
                        " Shows where listings are concentrated using contour lines and scatter points"
                    ]),
                    html.Li([
                        html.Strong("Density Heatmap:"),
                        " Displays listing density as a 2D histogram with color intensity"
                    ]),
                    html.Li([
                        html.Strong("Distance vs. Price Analysis:"),
                        " Reveals how property prices vary with distance from major city centers"
                    ]),
                    html.Li([
                        html.Strong("Average Price Map:"),
                        " Shows average price per night for each city, with circle size representing price"
                    ])
                ])
            ]),
            html.P([
                "For more information about data processing and methodology, visit the ",
                html.A("Technical Details", href="/technical"), " page."
            ]),
            html.Br(),
        ])
    ])
], fluid=True)


# Callback to update Distance vs. Price visualization based on selected city
@dash.callback(
    Output("distance-price-visualization", "figure"),
    Input("city-center-dropdown", "value")
)
def update_distance_price(selected_city):
    return create_distance_price_visualization(selected_city)