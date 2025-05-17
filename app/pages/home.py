import dash
from dash import html, dcc, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from app.utils.data_loader import load_data
from wordcloud import WordCloud
import io
import base64
from dash.dependencies import Input, Output, State
from PIL import Image as PILImage

dash.register_page(__name__, path="/", name="Home")

# load
df = load_data()
df['year'] = df['date_of_listing'].dt.year
cities = sorted(df['city'].unique())
cities.insert(0, "All Cities")  # Add "All Cities" option at the beginning


def get_stats(city_filter="All Cities", bedroom_filter="All"):
    if city_filter == "All Cities":
        filtered_df = df
    else:
        filtered_df = df[df['city'] == city_filter]

    if bedroom_filter != "All":
        if bedroom_filter == "4+":
            filtered_df = filtered_df[filtered_df['bedrooms_count'] >= 4]
        else:
            filtered_df = filtered_df[filtered_df['bedrooms_count'] == int(bedroom_filter)]

    n_listings = filtered_df.shape[0]
    n_cities = 1 if city_filter != "All Cities" else filtered_df['city'].nunique()
    avg_price = filtered_df['average_rate_per_night'].mean()
    avg_beds = filtered_df['bedrooms_count'].mean()

    return n_listings, n_cities, avg_price, avg_beds

n_listings, n_cities, avg_price, avg_beds = get_stats()
keywords = ['has_luxury', 'has_family', 'has_pool', 'has_downtown', 'has_modern', 'has_quiet']
kw_df = (
    df[keywords]
    .sum()
    .rename("count")
    .reset_index()
    .rename(columns={'index': 'keyword'})
)
kw_df['pct'] = kw_df['count'] / n_listings * 100


# Yearly rate trend
def create_yearly_rate_trend():
    avg_rate_per_year = df.groupby('year')['average_rate_per_night'].mean().reset_index()
    years = avg_rate_per_year['year'].tolist()

    # forced not to use
    predefined_colors = [
        'rgba(31, 119, 180, 0.8)',   # blue
        'rgba(255, 127, 14, 0.8)',   # orange
        'rgba(44, 160, 44, 0.8)',    # green
        'rgba(214, 39, 40, 0.8)',    # red
        'rgba(148, 103, 189, 0.8)',  # purple
        'rgba(140, 86, 75, 0.8)',    # brown
        'rgba(227, 119, 194, 0.8)',  # pink
        'rgba(127, 127, 127, 0.8)',  # gray
        'rgba(188, 189, 34, 0.8)',   # yellow-green
        'rgba(23, 190, 207, 0.8)'    # cyan
    ]
    hex_colors = [predefined_colors[i % len(predefined_colors)] for i in range(len(years))]

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
            marker_color=hex_colors[i % len(hex_colors)],
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


#  moving average trend
def create_moving_average_trend():
    df_sorted = df.sort_values(by='date_of_listing')

    # Moving average
    window_size = 7
    df_sorted['SMA'] = df_sorted['average_rate_per_night'].rolling(window=window_size).mean()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_sorted['date_of_listing'],
        y=df_sorted['average_rate_per_night'],
        mode='lines',
        name='Original',
        line=dict(color='lightblue')
    ))

    fig.add_trace(go.Scatter(
        x=df_sorted['date_of_listing'],
        y=df_sorted['SMA'],
        mode='lines',
        name=f'{window_size}-Day SMA',
        line=dict(color='orange', width=2)
    ))

    fig.update_layout(
        title=f'Average Nightly Rate Over Time with {window_size}-Day Moving Average',
        xaxis_title='Listing Date',
        yaxis_title='Average Rate per Night (USD)',
        template='plotly_white',
        legend=dict(x=0.01, y=0.99),
        height=400
    )

    return fig


# Listings count
def create_listings_count():
    city_listing_count = df["city"].value_counts().reset_index()
    city_listing_count.columns = ["city", "num_listings"]

    host_listings_count = df["title"].value_counts().reset_index()
    host_listings_count.columns = ["host", "num_listings"]

    fig = make_subplots(
        rows=2, cols=1,
        vertical_spacing=0.15,
        subplot_titles=("Top 20 Cities by Number of Listings", "Top 20 Hosts by Number of Listings")
    )

    fig.add_trace(go.Bar(
        x=city_listing_count.head(20)["num_listings"],
        y=city_listing_count.head(20)["city"],
        orientation='h',
        marker=dict(color=city_listing_count.head(20)["num_listings"], colorscale="Blues"),
        name='Cities'
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=host_listings_count.head(20)["num_listings"],
        y=host_listings_count.head(20)["host"],
        orientation='h',
        marker=dict(color=host_listings_count.head(20)["num_listings"], colorscale="Purples"),
        name='Hosts'
    ), row=2, col=1)

    fig.update_layout(
        height=700,
        template='plotly_white',
        title="Top Cities and Hosts by Number of Listings",
        xaxis=dict(title="Number of Listings"),
        xaxis2=dict(title="Number of Listings"),
        yaxis=dict(title="City", autorange="reversed"),
        yaxis2=dict(title="Host", autorange="reversed"),
        showlegend=False
    )

    return fig


# Price by bedrooms box plot
def create_price_by_bedrooms():
    filtered_df = df.dropna(subset=["bedrooms_count", "average_rate_per_night"])

    fig = px.box(
        filtered_df,
        x="bedrooms_count",
        y="average_rate_per_night",
        points="outliers",
        color="bedrooms_count",
        color_discrete_sequence=px.colors.qualitative.Pastel1,
        title="Price Distribution by Number of Bedrooms",
        labels={
            "bedrooms_count": "Number of Bedrooms",
            "average_rate_per_night": "Average Rate Per Night ($)"
        }
    )

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Number of Bedrooms",
        yaxis_title="Average Rate Per Night ($)",
        showlegend=False,
        height=450
    )

    return fig


# City price comparison
def create_city_price_comparison():
    city_avg_rate = df.groupby("city")["average_rate_per_night"].mean().reset_index()
    city_avg_rate = city_avg_rate.sort_values(by="average_rate_per_night", ascending=False)

    top_10_cities = city_avg_rate.head(10)
    bottom_10_cities = city_avg_rate.tail(10)

    fig = make_subplots(
        rows=1, cols=2,
        horizontal_spacing=0.15,
        subplot_titles=("Top 10 Cities by Average Nightly Rate", "Bottom 10 Cities by Average Nightly Rate")
    )

    fig.add_trace(go.Bar(
        x=top_10_cities["average_rate_per_night"],
        y=top_10_cities["city"],
        orientation="h",
        marker=dict(color=top_10_cities["average_rate_per_night"], colorscale="Viridis"),
        name="Top Cities"
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=bottom_10_cities["average_rate_per_night"],
        y=bottom_10_cities["city"],
        orientation="h",
        marker=dict(color=bottom_10_cities["average_rate_per_night"], colorscale="Magma"),
        name="Bottom Cities"
    ), row=1, col=2)

    fig.update_layout(
        height=500,
        title_text="City-wise Airbnb Average Rates: Top vs Bottom 10",
        template="plotly_white",
        showlegend=False
    )

    fig.update_yaxes(autorange="reversed", title="City", row=1, col=1)
    fig.update_yaxes(autorange="reversed", title="City", row=1, col=2)
    fig.update_xaxes(title="Average Rate Per Night ($)", row=1, col=1)
    fig.update_xaxes(title="Average Rate Per Night ($)", row=1, col=2)

    return fig


# Create word cloud function
def create_word_cloud(df, city=None):
    """Create a word cloud from listing descriptions with optional city filtering"""
    filtered_df = df.copy()
    if city and city != "All Cities":
        filtered_df = filtered_df[filtered_df['city'] == city]

    all_descriptions = ' '.join(filtered_df['description'].fillna('').astype(str).tolist())
    
    stopwords = set(['the', 'and', 'to', 'of', 'in', 'a', 'is', 'with', 'for', 'on', 'at', 'from',
                     'this', 'that', 'will', 'are', 'be', 'have', 'has', 'you', 'we', 'our',
                     'your', 'their', 'us', 'can', 'just', 'or', 'by', 'not', 'an', 'it',
                     'its', 'but', 'also', 'as', 'one', 'two', 'there', 'here', 'all','my'])

    wordcloud = WordCloud(
        width=600,
        height=280,
        background_color='white',
        max_words=80,
        contour_width=2,
        contour_color='steelblue',
        stopwords=stopwords,
        collocations=False,
        min_font_size=8,  
        max_font_size=150,
        mode="RGBA"
    ).generate(all_descriptions)
    
    # Convert to PIL image 
    img = wordcloud.to_image()
    
    # Save to BytesIO 
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    encoded_image = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
    return encoded_image


def create_sentiment_analysis():
    """Create sentiment analysis visualizations (donut charts, etc.), but NOT the 3D geo graph."""
    df['sentiment_label'] = df['sentiment_label'].fillna('Neutral')
    filtered_df = df.dropna(subset=['average_rate_per_night', 'bedrooms_count', 'sentiment_label'])
    price_bins = ['$0-100', '$100-200', '$200-500', '$500-1000', '$1000+']
    filtered_df['price_bin'] = pd.cut(
        filtered_df['average_rate_per_night'],
        bins=[0, 100, 200, 500, 1000, float('inf')],
        labels=price_bins
    )
    price_fig = go.Figure()
    for sentiment, color in zip(['Friendly', 'Neutral', 'Aggressive'], ["#2ca02c", "#d3d3d3", "#d62728"]):
        df_sentiment = filtered_df[filtered_df['sentiment_label'] == sentiment]
        if len(df_sentiment) == 0:
            continue
        price_counts = df_sentiment['price_bin'].value_counts().sort_index()
        price_fig.add_trace(go.Pie(
            labels=price_counts.index,
            values=price_counts.values,
            name=sentiment,
            hole=0.4,
            showlegend=True,
            textinfo='percent',
            texttemplate='%{percent:.0f}%',
            marker=dict(colors=px.colors.sequential.Plasma[::-1]),
            title=dict(text=f"{sentiment} Price Distribution", font=dict(color=color, size=12)),
        ))
    price_fig.update_layout(
        title_text="Price Distribution by Sentiment",
        height=400,
        grid=dict(rows=1, columns=3),
        margin=dict(t=60, b=20, l=20, r=20)
    )

    bedroom_bins = ['Studio', '1 BR', '2 BR', '3 BR', '4+ BR']
    filtered_df['bedroom_bin'] = pd.cut(
        filtered_df['bedrooms_count'],
        bins=[-0.1, 0.9, 1.9, 2.9, 3.9, float('inf')],
        labels=bedroom_bins
    )
    bedroom_fig = go.Figure()
    for sentiment, color in zip(['Friendly', 'Neutral', 'Aggressive'], ["#2ca02c", "#d3d3d3", "#d62728"]):
        df_sentiment = filtered_df[filtered_df['sentiment_label'] == sentiment]
        if len(df_sentiment) == 0:
            continue
        bedroom_counts = df_sentiment['bedroom_bin'].value_counts().sort_index()
        bedroom_fig.add_trace(go.Pie(
            labels=bedroom_counts.index,
            values=bedroom_counts.values,
            name=sentiment,
            hole=0.4,
            showlegend=True,
            textinfo='percent',
            texttemplate='%{percent:.0f}%',
            marker=dict(colors=px.colors.sequential.Viridis),
            title=dict(text=f"{sentiment} Bedroom Distribution", font=dict(color=color, size=12)),
        ))
    bedroom_fig.update_layout(
        title_text="Bedroom Distribution by Sentiment",
        height=400,
        grid=dict(rows=1, columns=3),
        margin=dict(t=60, b=20, l=20, r=20)
    )
    return price_fig, bedroom_fig


layout = dbc.Container(fluid=True, children=[
    dbc.Row([
        dbc.Col([
            html.H1("Texas Airbnb Dashboard", className="display-4"),
            html.P(
                "Explore listings, pricing trends, and market analysis for Airbnb properties across Texas",
                className="lead"
            ),
            html.Hr(),
        ])
    ], className="mb-4"),

    # City search
    dbc.Row([
        dbc.Col([
            dbc.InputGroup([
                dbc.InputGroupText("Filter by City:"),
                dcc.Dropdown(
                    id="city-filter",
                    options=[{"label": city, "value": city} for city in cities],
                    value="All Cities",
                    searchable=True,
                    clearable=False,
                    style={"minWidth": "200px"}
                ),
                dbc.InputGroupText("Filter by Bedrooms:"),
                dbc.Select(
                    id="bedroom-filter",
                    options=[
                        {"label": "All", "value": "All"},
                        {"label": "Studio", "value": "0"},
                        {"label": "1 Bedroom", "value": "1"},
                        {"label": "2 Bedrooms", "value": "2"},
                        {"label": "3 Bedrooms", "value": "3"},
                        {"label": "4+ Bedrooms", "value": "4+"}
                    ],
                    value="All"
                ),
                dbc.Button("Apply Filter", id="apply-filter", color="primary", className="ms-2")
            ])
        ], width={"size": 8, "offset": 0})
    ], className="mb-4"),
    dbc.Row(
        [
            dbc.Col(dbc.Card([
                dbc.CardHeader("Total Listings"),
                dbc.CardBody(html.H4(id="total-listings", children=f"{n_listings:,}", className="card-title"))
            ], className="shadow-sm"), xs=6, sm=6, md=3, lg=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Cities"),
                dbc.CardBody(html.H4(id="total-cities", children=f"{n_cities}", className="card-title"))
            ], className="shadow-sm"), xs=6, sm=6, md=3, lg=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Avg. Price"),
                dbc.CardBody(html.H4(id="avg-price", children=f"${avg_price:.2f}", className="card-title"))
            ], className="shadow-sm"), xs=6, sm=6, md=3, lg=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Avg. Bedrooms"),
                dbc.CardBody(html.H4(id="avg-bedrooms", children=f"{avg_beds:.1f}", className="card-title"))
            ], className="shadow-sm"), xs=6, sm=6, md=3, lg=3),
        ],
        className="mb-4",
    ),

    #  Tab navigation
    dbc.Row([
        dbc.Col([
            html.H2("Airbnb Market Analysis", className="mt-2 mb-3"),
            dbc.Tabs([
                # Tab 1: Price Trends
                dbc.Tab(label="Price Trends", children=[
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Annual Price Trends"),
                                dbc.CardBody([
                                    dcc.Graph(
                                        id="yearly-rate-trend",
                                        figure=create_yearly_rate_trend()
                                    )
                                ])
                            ], className="shadow-sm mt-3 mb-3")
                        ]),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Daily Price Trends with 7-Day Moving Average"),
                                dbc.CardBody([
                                    dcc.Graph(
                                        id="moving-average-trend",
                                        figure=create_moving_average_trend()
                                    )
                                ])
                            ], className="shadow-sm mb-3")
                        ]),
                    ]),
                ]),

                # Tab 2: Market Structure
                dbc.Tab(label="Market Structure", children=[
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Top Cities and Hosts by Listing Count"),
                                dbc.CardBody([
                                    dcc.Graph(
                                        id="listings-count",
                                        figure=create_listings_count()
                                    )
                                ])
                            ], className="shadow-sm mt-3 mb-3")
                        ]),
                    ]),
                ]),

                # Tab 3: Price Analysis
                dbc.Tab(label="Price Analysis", children=[
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Price Distribution by Number of Bedrooms"),
                                dbc.CardBody([
                                    dcc.Graph(
                                        id="price-by-bedrooms",
                                        figure=create_price_by_bedrooms()
                                    )
                                ])
                            ], className="shadow-sm mt-3 mb-3")
                        ]),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("City Price Comparison"),
                                dbc.CardBody([
                                    dcc.Graph(
                                        id="city-price-comparison",
                                        figure=create_city_price_comparison()
                                    )
                                ])
                            ], className="shadow-sm mb-3")
                        ]),
                    ]),
                ]),

                # Tab 4: Amenities
                dbc.Tab(label="Amenities", children=[
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Listing Amenities Analysis"),
                                dbc.CardBody([
                                    dcc.Graph(
                                        id="kw-bar",
                                        figure=px.bar(
                                            kw_df,
                                            x='keyword',
                                            y='pct',
                                            text=kw_df['pct'].map("{:.1f}%".format),
                                            title="% of Listings Containing Keyword",
                                            labels={'pct': '% of listings', 'keyword': 'Keyword'},
                                            color='pct',
                                            color_continuous_scale='Viridis',
                                            height=400
                                        ).update_layout(xaxis_tickangle=-45)
                                    )
                                ])
                            ], className="shadow-sm mt-3 mb-3")
                        ]),
                    ]),
                ]),

                # Tab: Listing Description Tone Analysis
                dbc.Tab(label="Listing Description Tone Analysis", children=[
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Listing Description Tone Analysis"),
                                dbc.CardBody([
                                    html.P(
                                        "This analysis explores how the tone of property descriptions—categorized as Positive, Neutral, or Negative—relates to property characteristics. The donut charts below show how these tone categories are distributed across different price ranges and bedroom counts, providing insight into how listing language may correlate with property features.",
                                        className="mb-3"
                                    ),
                                    html.Div([
                                        html.Label("Select Tone Category:"),
                                        dcc.RadioItems(
                                            id="tone-selector",
                                            options=[
                                                {"label": "Positive", "value": "Positive"},
                                                {"label": "Neutral", "value": "Neutral"},
                                                {"label": "Negative", "value": "Negative"}
                                            ],
                                            value="Positive",
                                            inline=True,
                                            className="mb-3"
                                        )
                                    ]),
                                    dbc.Row([
                                        dbc.Col([
                                            dcc.Graph(
                                                id="sentiment-price-donut",
                                                responsive=True
                                            )
                                        ], width=6),
                                        dbc.Col([
                                            dcc.Graph(
                                                id="sentiment-bedroom-donut",
                                                responsive=True
                                            )
                                        ], width=6),
                                    ])
                                ])
                            ], className="shadow-sm mt-3 mb-3")
                        ]),
                    ]),
                ]),

                # Tab 5: Sample Listings
                dbc.Tab(label="Sample Listings", children=[
                    dbc.Row([
                        dbc.Col([
                            html.H5("Sample Listings", className="mt-3"),
                            html.Label("Rows to show:"),
                            dcc.Slider(
                                id='n-sample-slider',
                                min=5, max=20, step=5, value=10,
                                marks={i: f"{i}" for i in [5, 10, 15, 20]}
                            ),
                            dash_table.DataTable(
                                id='sample-table',
                                columns=[
                                    {"name": "City", "id": "city"},
                                    {"name": "Title", "id": "title"},
                                    {"name": "Price", "id": "average_rate_per_night", "type": "numeric",
                                     "format": {'specifier': "$,.2f"}},
                                    {"name": "Beds", "id": "bedrooms_count"},
                                    {"name": "Age (days)", "id": "listing_age"},
                                ],
                                page_size=20,
                                style_table={"overflowX": "auto"},
                                style_cell={"textAlign": "left", "padding": "5px"},
                                style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
                            )
                        ], width=12),
                    ], className="mt-3 mb-3"),
                ]),

                # Tab 6: Word Cloud
                dbc.Tab(label="Word Cloud", children=[
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.H5("Listing Description Word Cloud", className="mb-0"),
                                ]),
                                dbc.CardBody([
                                    dbc.Row([
                                        dbc.Col([
                                            html.Label("Select City:"),
                                            dcc.Dropdown(
                                                id='word-cloud-city-filter',
                                                options=[{"label": city, "value": city} for city in cities],
                                                value="All Cities",
                                                className="mb-2"
                                            ),
                                            dbc.Button("Generate", id="generate-word-cloud", color="primary", size="sm",
                                                       className="mb-2"),
                                            html.P(
                                                "This visualization shows frequently used words in property descriptions. The size indicates how often each word appears.",
                                                className="text-muted small mt-2"),
                                        ], width=3),

                                        dbc.Col([
                                            html.Div([
                                                html.Img(
                                                    id="word-cloud-image",
                                                    src=f"data:image/png;base64,{create_word_cloud(df)}",
                                                    style={'width': '100%', 'max-height': '300px',
                                                           'object-fit': 'contain'}
                                                ),
                                            ], style={'text-align': 'center'})
                                        ], width=9),
                                    ]),
                                ], className="p-3")
                            ], className="shadow-sm mt-3 mb-3")
                        ]),
                    ]),
                ]),
            ]),
        ], width=12),
    ]),

    # Footer with navigation
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P([
                "For geographic analysis and mapping of listings, visit the ",
                html.A("Geo Data Analysis", href="/geo_visualizations", className="text-decoration-none"),
                " page."
            ]),
            html.P([
                "For technical details about data preprocessing and methodology, visit the ",
                html.A("Technical Details", href="/technical", className="text-decoration-none"),
                " page."
            ]),
        ], className="mt-4 mb-4")
    ]),
], )

@dash.callback(
    [Output('total-listings', 'children'),
     Output('total-cities', 'children'),
     Output('avg-price', 'children'),
     Output('avg-bedrooms', 'children')],
    [Input('apply-filter', 'n_clicks')],
    [State('city-filter', 'value'),
     State('bedroom-filter', 'value')],
    prevent_initial_call=True
)
def update_stats(n_clicks, city_filter, bedroom_filter):
    n_listings, n_cities, avg_price, avg_beds = get_stats(city_filter, bedroom_filter)
    return f"{n_listings:,}", f"{n_cities}", f"${avg_price:.2f}", f"{avg_beds:.1f}"


# Callback for sample-table 
@dash.callback(
    Output('sample-table', 'data'),
    [Input('n-sample-slider', 'value'),
     Input('apply-filter', 'n_clicks')],
    [State('city-filter', 'value'),
     State('bedroom-filter', 'value')],
)
def update_sample(n, n_clicks, city_filter, bedroom_filter):
    ctx = dash.callback_context

    # Get the city filter value
    if not ctx.triggered or ctx.triggered[0]['prop_id'] == 'n-sample-slider.value':
        if dash.callback_context.states.get('city-filter.value'):
            city_filter = dash.callback_context.states['city-filter.value']
        else:
            city_filter = "All Cities"
    if city_filter == "All Cities":
        filtered_df = df
    else:
        filtered_df = df[df['city'] == city_filter]

    if bedroom_filter != "All":
        if bedroom_filter == "4+":
            filtered_df = filtered_df[filtered_df['bedrooms_count'] >= 4]
        else:
            filtered_df = filtered_df[filtered_df['bedrooms_count'] == int(bedroom_filter)]

    return filtered_df.head(n).to_dict('records')


@dash.callback(
    Output('word-cloud-image', 'src'),
    [Input('generate-word-cloud', 'n_clicks')],
    [State('word-cloud-city-filter', 'value')],
    prevent_initial_call=True
)
def update_word_cloud(n_clicks, city_filter):
    """Update the word cloud image based on the selected city filter"""
    return f"data:image/png;base64,{create_word_cloud(df, city=city_filter)}"


# Add callback to update donut charts based on selected tone
from dash import callback_context

@dash.callback(
    [Output('sentiment-price-donut', 'figure'), Output('sentiment-bedroom-donut', 'figure')],
    [Input('tone-selector', 'value')]
)
def update_tone_donuts(selected_tone):
    df['sentiment_label'] = df['sentiment_label'].fillna('Neutral')
    filtered_df = df.dropna(subset=['average_rate_per_night', 'bedrooms_count', 'sentiment_label'])
    
    # Filter data for selected tone
    df_sentiment = filtered_df[filtered_df['sentiment_label'] == selected_tone]
    
    # Price donut
    price_bins = ['$0-100', '$100-200', '$200-500', '$500-1000', '$1000+']
    filtered_df['price_bin'] = pd.cut(
        filtered_df['average_rate_per_night'], 
        bins=[0, 100, 200, 500, 1000, float('inf')],
        labels=price_bins
    )
    
    if len(df_sentiment) == 0:
        price_fig = go.Figure()
        price_fig.add_annotation(
            text=f"No data available for '{selected_tone}' tone category",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        price_fig.update_layout(
            title_text="Price Distribution by Tone",
            height=400,
            margin=dict(t=60, b=20, l=20, r=20)
        )
        
        bedroom_fig = go.Figure()
        bedroom_fig.add_annotation(
            text=f"No data available for '{selected_tone}' tone category",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        bedroom_fig.update_layout(
            title_text="Bedroom Distribution by Tone",
            height=400,
            margin=dict(t=60, b=20, l=20, r=20)
        )
        
        return price_fig, bedroom_fig
    
    df_sentiment['price_bin'] = pd.cut(
        df_sentiment['average_rate_per_night'],
        bins=[0, 100, 200, 500, 1000, float('inf')],
        labels=price_bins
    )
    price_counts = df_sentiment['price_bin'].value_counts().sort_index()
    
    price_fig = go.Figure()
    if len(price_counts) > 0:
        price_fig.add_trace(go.Pie(
            labels=price_counts.index,
            values=price_counts.values,
            name=selected_tone,
            hole=0.4,
            showlegend=True,
            textinfo='percent+value',
            texttemplate='%{percent:.2f}%<br>(%{value})',
            marker=dict(colors=px.colors.sequential.Plasma[::-1]),
            title=dict(text=f"{selected_tone} Price Distribution", font=dict(size=12)),
            hoverinfo='label+percent+name',
            textposition='inside'
        ))
    else:
        price_fig.add_annotation(
            text=f"No price data available for '{selected_tone}' tone category",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
    
    price_fig.update_layout(
        title_text="Price Distribution by Tone",
        height=400,
        margin=dict(t=60, b=20, l=20, r=20),
        showlegend=False
    )
    
    bedroom_bins = ['Studio', '1 BR', '2 BR', '3 BR', '4+ BR']
    df_sentiment['bedroom_bin'] = pd.cut(
        df_sentiment['bedrooms_count'],
        bins=[-0.1, 0.9, 1.9, 2.9, 3.9, float('inf')],
        labels=bedroom_bins
    )
    bedroom_counts = df_sentiment['bedroom_bin'].value_counts().sort_index()
    
    bedroom_fig = go.Figure()
    if len(bedroom_counts) > 0:
        bedroom_fig.add_trace(go.Pie(
            labels=bedroom_counts.index,
            values=bedroom_counts.values,
            name=selected_tone,
            hole=0.4,
            showlegend=True,
            textinfo='percent+value',
            texttemplate='%{percent:.2f}%<br>(%{value})',
            marker=dict(colors=px.colors.sequential.Viridis),
            title=dict(text=f"{selected_tone} Bedroom Distribution", font=dict(size=12)),
            hoverinfo='label+percent+name',
            textposition='inside'
        ))
    else:
        bedroom_fig.add_annotation(
            text=f"No bedroom data available for '{selected_tone}' tone category",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        
    bedroom_fig.update_layout(
        title_text="Bedroom Distribution by Tone",
        height=400,
        margin=dict(t=60, b=20, l=20, r=20),
        showlegend=False
    )
    
    return price_fig, bedroom_fig