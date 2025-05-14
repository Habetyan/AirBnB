import dash
from dash import html, dcc, Input, Output, State, callback
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
import base64

# Register dash page
dash.register_page(
    __name__,
    path="/geo_visualizations",
    title="Geographic Analysis",
    name="Geo data Analysis"
)

df_cleaned = load_data()

price_min = int(df_cleaned['average_rate_per_night'].min())
price_max = int(df_cleaned['average_rate_per_night'].max())
bedrooms_max = int(df_cleaned['bedrooms_count'].max())

# Texas big city centre coordinates
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


# Function to filter dataframe based on inputs
def filter_dataframe(df, city_filter=None, price_range=None, bedrooms=None):
    filtered_df = df.copy()
    
    if city_filter and city_filter != "All Cities":
        filtered_df = filtered_df[filtered_df['city'] == city_filter]
    
    if price_range:
        min_price, max_price = price_range
        filtered_df = filtered_df[(filtered_df['average_rate_per_night'] >= min_price) & 
                                (filtered_df['average_rate_per_night'] <= max_price)]
    
    if bedrooms:
        filtered_df = filtered_df[filtered_df['bedrooms_count'].isin(bedrooms)]
    
    return filtered_df


# Create geo-visualization
def create_geo_visualization(filtered_df=None):
    df_geo = filtered_df.dropna(subset=["latitude", "longitude"]) if filtered_df is not None else df_cleaned.dropna(subset=["latitude", "longitude"])

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
            marker=dict(
                size=5, 
                color=df_geo['average_rate_per_night'],
                colorscale='Viridis',
                opacity=0.6,
                colorbar=dict(title="Price ($)")
            ),
            text=df_geo['title'],
            hoverinfo='text+x+y',
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
def create_distance_price_visualization(selected_city='Houston', filtered_df=None):
    center_lat, center_lon = CITY_CENTERS.get(selected_city, CITY_CENTERS['Houston'])
    
    if filtered_df is not None:
        df_with_distance = filtered_df.dropna(subset=['latitude', 'longitude', 'average_rate_per_night']).copy()
    else:
        df_with_distance = df_cleaned.dropna(subset=['latitude', 'longitude', 'average_rate_per_night']).copy()

    # Distance from city center for each listing
    df_with_distance['distance_km'] = df_with_distance.apply(
        lambda row: haversine(center_lon, center_lat, row['longitude'], row['latitude']),
        axis=1
    )

    # 95th percentile cutoff
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

    # trendline
    df_trend = df_filtered.copy()
    
    fig.update_traces(
        mode='markers',
        marker=dict(line=dict(width=0.5, color='white'))
    )

    # Add moving average trend line
    fig.add_trace(
        go.Scatter(
            x=df_trend['distance_km'],
            y=df_trend['average_rate_per_night'].rolling(window=min(50, len(df_trend))).mean(),
            mode='lines',
            name='Price Trend',
            line=dict(color='red', width=2)
        )
    )

    return fig

def create_folium_map_html(filtered_df=None):
    df_for_map = filtered_df if filtered_df is not None else df_cleaned
    
    city_avg_price = df_for_map.groupby("city")["average_rate_per_night"].mean().reset_index()
    city_count = df_for_map.groupby("city").size().reset_index(name="count")
    city_data = pd.merge(city_avg_price, city_count, on="city")

    m = folium.Map(
        location=[df_for_map["latitude"].mean(), df_for_map["longitude"].mean()],
        zoom_start=6,
        tiles="OpenStreetMap"
    )

    # Circle markers for each city
    for _, row in city_data.iterrows():
        city_listings = df_for_map[df_for_map["city"] == row["city"]]
        lat_mean = city_listings["latitude"].mean()
        lon_mean = city_listings["longitude"].mean()

        # Sanity check for correct coordinates
        if not np.isnan(lat_mean) and not np.isnan(lon_mean):
            folium.CircleMarker(
                location=[lat_mean, lon_mean],
                radius=min(20, np.sqrt(row["count"])),
                color="green",
                fill=True,
                fill_color="green",
                fill_opacity=0.6,
                popup=f"{row['city']}: ${row['average_rate_per_night']:.2f} (Listings: {row['count']})",
            ).add_to(m)

    # Create a choropleth layer for average prices by city
    for _, row in city_data.iterrows():
        city_listings = df_for_map[df_for_map["city"] == row["city"]]
        if len(city_listings) > 10:  # Only for cities with enough listings
            lat_mean = city_listings["latitude"].mean()
            lon_mean = city_listings["longitude"].mean()
            
            if not np.isnan(lat_mean) and not np.isnan(lon_mean):
                folium.Circle(
                    location=[lat_mean, lon_mean],
                    radius=row["average_rate_per_night"] * 15,  # Scale by price
                    color="blue",
                    fill=True,
                    fill_color="blue",
                    fill_opacity=0.2,
                    popup=f"Avg Price: ${row['average_rate_per_night']:.2f}",
                ).add_to(m)

    map_html = m._repr_html_()
    return map_html


# Create 3D map visualization
def create_3d_price_map(filtered_df=None):
    df_geo = filtered_df.dropna(subset=["latitude", "longitude", "average_rate_per_night"]) if filtered_df is not None else df_cleaned.dropna(subset=["latitude", "longitude", "average_rate_per_night"])
    
    fig = px.scatter_3d(
        df_geo,
        x='longitude', 
        y='latitude', 
        z='average_rate_per_night',
        color='bedrooms_count',
        color_continuous_scale='Viridis',
        size='average_rate_per_night',
        size_max=10,
        opacity=0.7,
        hover_name='city',
        hover_data=['title', 'bedrooms_count', 'average_rate_per_night'],
        labels={
            'longitude': 'Longitude',
            'latitude': 'Latitude',
            'average_rate_per_night': 'Price ($)',
            'bedrooms_count': 'Bedrooms'
        },
        title="3D Price Map of Airbnb Listings"
    )
    
    fig.update_layout(
        scene=dict(
            xaxis_title='Longitude',
            yaxis_title='Latitude',
            zaxis_title='Price ($)',
            aspectratio=dict(x=1, y=1, z=0.5)
        ),
        template='plotly_white'
    )
    
    return fig


# Create price heatmap by location
def create_price_heatmap(filtered_df=None):
    df_for_heatmap = filtered_df.dropna(subset=["latitude", "longitude", "average_rate_per_night"]) if filtered_df is not None else df_cleaned.dropna(subset=["latitude", "longitude", "average_rate_per_night"])
    
    fig = px.density_mapbox(
        df_for_heatmap, 
        lat='latitude', 
        lon='longitude', 
        z='average_rate_per_night', 
        radius=10,
        center=dict(lat=30.9, lon=-97.8), 
        zoom=5,
        hover_name='city',
        hover_data=['title', 'bedrooms_count', 'average_rate_per_night'],
        mapbox_style="open-street-map",
        title="Price Heatmap of Airbnb Listings"
    )
    
    fig.update_layout(
        height=500, 
        margin=dict(l=10, r=10, t=50, b=10)
    )
    
    return fig


# layout for geo-visualization
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Geographic Analysis of Texas Airbnb Listings"),
            html.P("Visualizing the spatial distribution and price patterns of Airbnb properties across Texas"),
            html.Hr(),
        ])
    ]),
    
    # Filters section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Filters"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("City:"),
                            dcc.Dropdown(
                                id="geo-city-filter",
                                options=[{"label": "All Cities", "value": "All Cities"}] + 
                                        [{"label": city, "value": city} for city in sorted(df_cleaned['city'].unique())],
                                value="All Cities",
                                clearable=False
                            ),
                        ], width=3),
                        dbc.Col([
                            html.Label("Price Range ($):"),
                            dcc.RangeSlider(
                                id="geo-price-range-slider",
                                min=price_min,
                                max=price_max,
                                step=10,
                                value=[price_min, price_max],
                                marks={i: f"${i}" for i in range(price_min, price_max+1, 200)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            ),
                        ], width=3),
                        dbc.Col([
                            html.Label("Bedrooms:"),
                            dcc.Dropdown(
                                id="geo-bedrooms-filter",
                                options=[{"label": str(i), "value": i} for i in range(1, bedrooms_max+1)],
                                value=[1, 2, 3],
                                multi=True
                            ),
                        ], width=3),
                        dbc.Col([
                            dbc.Button("Apply Filters", id="geo-apply-filter", color="primary", className="mt-4"),
                        ], width=3),
                    ]),
                ])
            ]),
        ])
    ], className="mb-4"),

    # Density visualizations
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
    ], className="mb-4"),

    # Distance/price plot
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Price vs. Distance from City Center"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Select City Center:"),
                            dcc.Dropdown(
                                id="city-center-dropdown",
                                options=[{"label": city, "value": city} for city in CITY_CENTERS.keys()],
                                value="Houston",
                                clearable=False
                            )
                        ], width=6)
                    ], className="mb-3"),
                    dcc.Graph(
                        id="distance-price-visualization",
                        figure=create_distance_price_visualization("Houston")
                    )
                ])
            ])
        ])
    ], className="mb-4"),
    
    # 3D Price Map
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("3D Price Visualization"),
                dbc.CardBody([
                    dcc.Graph(
                        id="3d-price-map",
                        figure=create_3d_price_map()
                    )
                ])
            ])
        ])
    ], className="mb-4"),
    
    # Interactive Map with price density
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Price Heatmap"),
                dbc.CardBody([
                    dcc.Graph(
                        id="price-heatmap",
                        figure=create_price_heatmap()
                    )
                ])
            ])
        ])
    ], className="mb-4"),

    # Folium Map
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Interactive City Price Map"),
                dbc.CardBody([
                    html.Iframe(
                        id="folium-map",
                        srcDoc=create_folium_map_html(),
                        width="100%",
                        height="500px",
                        style={"border": "none"}
                    )
                ])
            ])
        ])
    ])
], fluid=True)


# Callbacks
@callback(
    [Output("geo-visualization", "figure"),
     Output("distance-price-visualization", "figure"),
     Output("folium-map", "srcDoc"),
     Output("3d-price-map", "figure"),
     Output("price-heatmap", "figure")],
    [Input("geo-apply-filter", "n_clicks"),
     Input("city-center-dropdown", "value")],
    [State("geo-city-filter", "value"),
     State("geo-price-range-slider", "value"),
     State("geo-bedrooms-filter", "value")],
    prevent_initial_call=True
)
def update_geo_visualizations(n_clicks, selected_city, city_filter, price_range, bedrooms_filter):
    filtered_df = filter_dataframe(
        df_cleaned,
        city_filter=city_filter,
        price_range=price_range,
        bedrooms=bedrooms_filter
    )
    
    geo_viz = create_geo_visualization(filtered_df)
    distance_price_viz = create_distance_price_visualization(selected_city, filtered_df)
    folium_map_html = create_folium_map_html(filtered_df)
    price_map_3d = create_3d_price_map(filtered_df)
    price_heatmap = create_price_heatmap(filtered_df)
    
    return geo_viz, distance_price_viz, folium_map_html, price_map_3d, price_heatmap