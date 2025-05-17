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
        showlegend=False,
        autosize=True,  
        margin=dict(l=20, r=20, t=50, b=20)  
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
        yaxis_title='Average Rate per Night ($)',
        autosize=True,  # Make plot automatically resize
        margin=dict(l=20, r=20, t=50, b=20)  # Smaller margins 
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
    
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 150px; height: 90px; 
                background-color: white; border:2px solid grey; z-index:9999; padding: 10px;
                font-size: 14px;">
        <div>
            <span style="background-color: #FFCC00; display: inline-block; width: 15px; height: 15px; 
                  border-radius: 50%; margin-right: 5px;"></span>
            Number of Listings
        </div>
        <div style="margin-top: 8px;">
            <span style="background-color: #FF8C00; display: inline-block; width: 15px; height: 15px; 
                  border-radius: 50%; margin-right: 5px;"></span>
            Average Price
        </div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    price_values = city_avg_price["average_rate_per_night"].values
    min_price = price_values.min()
    max_price = price_values.max()
    
    def get_price_color(price):
        normalized = (price - min_price) / (max_price - min_price) if max_price > min_price else 0.5
        return f'rgba({int(255)}, {int(140 + normalized * 60)}, 0, 0.8)'

    for _, row in city_avg_price.iterrows():
        city_data = df_cleaned[df_cleaned["city"] == row["city"]]
        lat_mean = city_data["latitude"].mean()
        lon_mean = city_data["longitude"].mean()
        listing_count = len(city_data)


        if not np.isnan(lat_mean) and not np.isnan(lon_mean):
            folium.CircleMarker(
                location=[lat_mean, lon_mean],
                radius=np.sqrt(listing_count) * 0.8,  
                color="#FFCC00",
                fill=True,
                fill_color="#FFCC00",
                fill_opacity=0.3,
                popup=f"{row['city']}: {listing_count} listings",
            ).add_to(m)
            
            price_color = get_price_color(row["average_rate_per_night"])
            folium.CircleMarker(
                location=[lat_mean + 0.02, lon_mean + 0.02],  
                radius=np.sqrt(row["average_rate_per_night"]) * 0.3,
                color="#FF8C00",
                fill=True,
                fill_color=price_color,
                fill_opacity=0.6,
                popup=f"{row['city']}: ${row['average_rate_per_night']:.2f} per night",
            ).add_to(m)


    map_html = m._repr_html_()

    return map_html

def create_3d_sentiment_visualization():
    """Create a 3D geographic visualization of listings showing their GPS location, price as z-axis, and sentiment as color."""
    df_cleaned['sentiment_label'] = df_cleaned['sentiment_label'].fillna('Neutral')
    filtered_df = df_cleaned.dropna(subset=['latitude', 'longitude', 'average_rate_per_night'])
    filtered_df = filtered_df[(filtered_df['latitude'] > 25) & (filtered_df['latitude'] < 35) & 
                             (filtered_df['longitude'] > -110) & (filtered_df['longitude'] < -90)]
    if len(filtered_df) > 3000:
        filtered_df = filtered_df.sample(3000, random_state=42)
    
    colors = {'Positive': '#2ca02c', 'Neutral': '#d3d3d3', 'Negative': '#d62728'}
    
    fig = go.Figure()
    for sentiment in ['Positive', 'Neutral', 'Negative']:
        df_sentiment = filtered_df[filtered_df['sentiment_label'] == sentiment]
        if len(df_sentiment) == 0:
            continue
        
        fig.add_trace(
            go.Scatter3d(
                x=df_sentiment['longitude'],
                y=df_sentiment['latitude'],
                z=df_sentiment['average_rate_per_night'],
                mode='markers',
                marker=dict(
                    size=5,
                    color=colors[sentiment],
                    opacity=0.7,
                    line=dict(width=0.5, color='white')
                ),
                text=df_sentiment['title'],
                customdata=np.stack((
                    df_sentiment['city'], 
                    df_sentiment['bedrooms_count'],
                    df_sentiment['sentiment_label']
                ), axis=-1),
                hovertemplate=(
                    "<b>%{text}</b><br>" +
                    "City: %{customdata[0]}<br>" +
                    "Price: $%{z:.2f}<br>" +
                    "Bedrooms: %{customdata[1]}<br>" +
                    "Sentiment: %{customdata[2]}<br>" +
                    "Lat: %{y:.4f}, Long: %{x:.4f}<extra></extra>"
                ),
                name=sentiment
            )
        )
    fig.update_layout(
        height=750,
        template="plotly_white",
        title={
            'text': "3D Geographic Sentiment Analysis: Property Locations, Prices, and Sentiment",
            'x': 0.5,
            'y': 0.98,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 20}
        },
        margin=dict(t=120, b=20, l=40, r=40),
        scene=dict(
            xaxis=dict(
                title="Longitude",
                range=[-106, -94],
                backgroundcolor='rgba(230, 230, 230, 0.8)',
                gridcolor='white',
                showbackground=True
            ),
            yaxis=dict(
                title="Latitude",
                range=[26, 34],
                backgroundcolor='rgba(230, 230, 230, 0.8)',
                gridcolor='white',
                showbackground=True
            ),
            zaxis=dict(
                title="Price ($)",
                backgroundcolor='rgba(230, 230, 230, 0.8)',
                gridcolor='white',
                showbackground=True
            ),
            aspectmode='manual',
            aspectratio=dict(x=1.5, y=1, z=0.8),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2),
                center=dict(x=0, y=0, z=-0.1)
            )
        ),
        legend=dict(
            title="Sentiment Categories",
            orientation="h",
            y=1.0,
            yanchor="bottom",
            x=0.5,
            xanchor="center"
        )
    )
    return fig

#  layout for geo-visualization
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Geographic Analysis of Texas Airbnb Listings", className="text-center text-md-start"),
            html.P("Visualizing the spatial distribution and price patterns of Airbnb properties across Texas", 
                   className="text-center text-md-start"),
            html.Hr(),
        ])
    ]),

    # Section: Listing Density
    dbc.Row([
        dbc.Col([
            html.H3("Listing Density Across Texas", className="mb-2 mt-4"),
            dbc.Card([
                dbc.CardHeader("Listing Density Analysis"),
                dbc.CardBody([
                    dcc.Graph(
                        id="geo-visualization",
                        figure=create_geo_visualization(),
                        responsive=True,
                        style={"height": "60vh", "min-height": "300px"}
                    )
                ])
            ])
        ], xs=12)
    ]),

    html.Hr(),

    # Section: Price vs Distance
    dbc.Row([
        dbc.Col([
            html.H3("Price vs. Distance from City Center", className="mb-2 mt-4"),
            html.P("Explore how property prices vary with distance from major city centers in Texas."),
            dbc.Card([
                dbc.CardHeader([
                    html.Div([
                        html.Span("Select City Center: ", className="me-2"),
                        dcc.Dropdown(
                            id="city-center-dropdown",
                            options=[{"label": city, "value": city} for city in CITY_CENTERS.keys()],
                            value="Houston",
                            clearable=False,
                            style={"display": "inline-block", "min-width": "150px", "max-width": "250px"}
                        )
                    ], className="d-flex align-items-center flex-wrap")
                ]),
                dbc.CardBody([
                    dcc.Graph(
                        id="distance-price-visualization",
                        figure=create_distance_price_visualization(),
                        responsive=True,
                        style={"height": "50vh", "min-height": "300px"}
                    )
                ])
            ])
        ], xs=12)
    ]),

    html.Hr(),

    # Section: Map Visualization Toggle
    dbc.Row([
        dbc.Col([
            html.H3("Interactive Map Visualizations", className="mb-2 mt-4"),
            html.P("Choose between different map visualizations to explore the data."),
            dbc.Card([
                dbc.CardHeader([
                    html.Div([
                        html.Span("Select Visualization: ", className="me-2"),
                        dcc.RadioItems(
                            id="map-visualization-toggle",
                            options=[
                                {"label": "Average Price Map by City", "value": "price_map"},
                                {"label": "3D Geographic Tone Analysis", "value": "sentiment_3d"}
                            ],
                            value="price_map",
                            inline=True,
                            className="ms-2"
                        )
                    ], className="d-flex align-items-center flex-wrap")
                ]),
                dbc.CardBody([
                    html.Div(id="map-visualization-container")
                ])
            ])
        ], xs=12)
    ])
], fluid=True, className="pb-4")


# Callback to update Distance vs. Price visualization based on selected city
@dash.callback(
    Output("distance-price-visualization", "figure"),
    Input("city-center-dropdown", "value")
)
def update_distance_price(selected_city):
    return create_distance_price_visualization(selected_city)

# Callback to update the map visualization based on the selected option
@dash.callback(
    Output("map-visualization-container", "children"),
    Input("map-visualization-toggle", "value")
)
def update_map_visualization(selected_visualization):
    if selected_visualization == "price_map":
        return html.Iframe(
            id="folium-map",
            srcDoc=create_folium_map_html(),
            style={"width": "100%", "height": "50vh", "min-height": "300px", "border": "none"}
        )
    else:  # sentiment_3d
        return dcc.Graph(
            id="sentiment-3d-viz",
            figure=create_3d_sentiment_visualization(),
            responsive=True,
            style={"height": "70vh", "min-height": "400px"}
        )