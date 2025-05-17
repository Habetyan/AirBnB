import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from app.utils.data_loader import load_data
import folium
import folium.plugins
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

# Predefined color sequence for year-based visualizations
YEAR_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
]

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
    city_stats = df_cleaned.groupby("city").agg({
        "average_rate_per_night": ["mean", "std", "count"],
        "latitude": "mean",
        "longitude": "mean"
    }).reset_index()
    
    city_stats.columns = ["city", "avg_price", "price_std", "listing_count", "latitude", "longitude"]
    price_quartiles = np.percentile(city_stats["avg_price"], [25, 50, 75])
    
    def get_price_color(price):
        if price <= price_quartiles[0]: return "#2ecc71"
        elif price <= price_quartiles[1]: return "#f1c40f"
        elif price <= price_quartiles[2]: return "#e67e22"
        else: return "#e74c3c"

    m = folium.Map(location=[31.0, -100.0], zoom_start=6, tiles="CartoDB positron")
    marker_cluster = folium.plugins.MarkerCluster(name="City Clusters", overlay=True, control=True).add_to(m)

    for _, row in city_stats.iterrows():
        if not (np.isnan(row["latitude"]) or np.isnan(row["longitude"])):
            popup_content = f"""
                <div style="font-family: Arial; min-width: 180px;">
                    <h4 style="margin-bottom: 10px;">{row['city']}</h4>
                    <b>Average Price:</b> ${row['avg_price']:.2f}<br>
                    <b>Price Range:</b> ${row['avg_price']-row['price_std']:.0f} - ${row['avg_price']+row['price_std']:.0f}<br>
                    <b>Number of Listings:</b> {row['listing_count']}<br>
                </div>
            """
            
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=min(np.sqrt(row["listing_count"]) * 0.8, 20),
                color=get_price_color(row["avg_price"]),
                fill=True,
                fill_opacity=0.7,
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"{row['city']}: ${row['avg_price']:.0f}/night"
            ).add_to(marker_cluster)
    
    legend_html = f"""
    <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                padding: 10px; font-size: 14px; border-radius: 6px;">
        <h4 style="margin-top: 0;">Average Price Ranges</h4>
        <div><span style="background-color: #2ecc71; display: inline-block; width: 15px; height: 15px; 
                  border-radius: 50%; margin-right: 5px;"></span>Below ${price_quartiles[0]:.0f}</div>
        <div style="margin-top: 5px;"><span style="background-color: #f1c40f; display: inline-block; width: 15px; height: 15px; 
                  border-radius: 50%; margin-right: 5px;"></span>${price_quartiles[0]:.0f} - ${price_quartiles[1]:.0f}</div>
        <div style="margin-top: 5px;"><span style="background-color: #e67e22; display: inline-block; width: 15px; height: 15px; 
                  border-radius: 50%; margin-right: 5px;"></span>${price_quartiles[1]:.0f} - ${price_quartiles[2]:.0f}</div>
        <div style="margin-top: 5px;"><span style="background-color: #e74c3c; display: inline-block; width: 15px; height: 15px; 
                  border-radius: 50%; margin-right: 5px;"></span>Above ${price_quartiles[2]:.0f}</div>
        <div style="margin-top: 10px; font-style: italic; font-size: 12px;">Circle size indicates number of listings</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    return m._repr_html_()

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

def create_yearly_rate_trend():
    avg_rate_per_year = df_cleaned.groupby('year')['average_rate_per_night'].mean().reset_index()
    years = avg_rate_per_year['year'].tolist()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.15,
        subplot_titles=('Average Rate Per Night by Year (Bar)', 'Average Rate Per Night Over Time (Line)')
    )

    for i, (year, rate) in enumerate(zip(avg_rate_per_year['year'], avg_rate_per_year['average_rate_per_night'])):
        fig.add_trace(go.Bar(
            x=[year],
            y=[rate],
            marker_color=colors[i % len(colors)],
            name=str(year),
            showlegend=False
        ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=avg_rate_per_year['year'],
        y=avg_rate_per_year['average_rate_per_night'],
        mode='lines+markers',
        line=dict(color='red'),
        marker=dict(size=8),
        name='Avg Rate'
    ), row=2, col=1)

    fig.update_layout(
        height=500,
        template='plotly_white',
        xaxis=dict(title='Year'),
        xaxis2=dict(title='Year', dtick=1),
        yaxis=dict(title='Average Rate ($)'),
        yaxis2=dict(title='Average Rate ($)'),
        title_text="Average Rate Per Night: Bar and Line View",
        hovermode='x unified'
    )
    return fig

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
                            className="ms-2",
                            inputStyle={"marginRight": "6px", "marginLeft": "12px"}
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