import dash
from dash import html, dcc, dash_table, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import matplotlib.pyplot as plt
from app.utils.data_loader import load_data
from wordcloud import WordCloud
import io
import base64

dash.register_page(__name__, path="/", name="Home")

# load
df = load_data()
df['year'] = df['date_of_listing'].dt.year
cities = sorted(df['city'].unique())
cities.insert(0, "All Cities")  # Add "All Cities" option at the beginning

price_min = int(df['average_rate_per_night'].min())
price_max = int(df['average_rate_per_night'].max())
bedrooms_max = int(df['bedrooms_count'].max())

def get_stats(city_filter="All Cities", price_range=None):
    filtered_df = df.copy()
    
    if city_filter != "All Cities":
        filtered_df = filtered_df[filtered_df['city'] == city_filter]
    
    if price_range:
        min_price, max_price = price_range
        filtered_df = filtered_df[(filtered_df['average_rate_per_night'] >= min_price) & 
                               (filtered_df['average_rate_per_night'] <= max_price)]

    n_listings = filtered_df.shape[0]
    n_cities = 1 if city_filter != "All Cities" else filtered_df['city'].nunique()
    avg_price = filtered_df['average_rate_per_night'].mean()
    avg_beds = filtered_df['bedrooms_count'].mean()

    return n_listings, n_cities, avg_price, avg_beds, filtered_df

n_listings, n_cities, avg_price, avg_beds, _ = get_stats()
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
def create_yearly_rate_trend(filtered_df=None):
    df_to_use = filtered_df if filtered_df is not None else df
    avg_rate_per_year = df_to_use.groupby('year')['average_rate_per_night'].mean().reset_index()
    years = avg_rate_per_year['year'].tolist()

    # Generate colors
    colors = [plt.cm.rainbow(i / len(years)) for i in range(len(years))]
    hex_colors = ['rgba({},{},{},{})'.format(int(r * 255), int(g * 255), int(b * 255), a)
                  for r, g, b, a in colors]

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
def create_moving_average_trend(filtered_df=None):
    df_to_use = filtered_df if filtered_df is not None else df
    df_sorted = df_to_use.sort_values(by='date_of_listing')

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
def create_listings_count(filtered_df=None):
    df_to_use = filtered_df if filtered_df is not None else df
    city_listing_count = df_to_use["city"].value_counts().reset_index()
    city_listing_count.columns = ["city", "num_listings"]

    host_listings_count = df_to_use["title"].value_counts().reset_index()
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
def create_price_by_bedrooms(filtered_df=None, selected_bedrooms=None):
    df_to_use = filtered_df if filtered_df is not None else df
    filtered_df = df_to_use.dropna(subset=["bedrooms_count", "average_rate_per_night"])
    
    if selected_bedrooms:
        filtered_df = filtered_df[filtered_df['bedrooms_count'].isin(selected_bedrooms)]

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
def create_city_price_comparison(filtered_df=None):
    df_to_use = filtered_df if filtered_df is not None else df
    city_avg_rate = df_to_use.groupby("city")["average_rate_per_night"].mean().reset_index()
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


# Word cloud creation
def create_word_cloud(filtered_df=None, city=None):
    df_for_wc = filtered_df if filtered_df is not None else df
    
    if city and city != "All Cities":
        df_for_wc = df_for_wc[df_for_wc['city'] == city]
    
    all_text = ' '.join(df_for_wc['description'].dropna().astype(str))
    
    wordcloud = WordCloud(
        width=800, 
        height=400,
        background_color='white',
        max_words=200,
        contour_width=3,
        contour_color='steelblue'
    ).generate(all_text)
    
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    
    # Convert the plot to an image
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png')
    plt.close()
    img_buf.seek(0)
    
    return 'data:image/png;base64,{}'.format(base64.b64encode(img_buf.read()).decode())


# Layout
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Texas Airbnb Analysis Dashboard"),
            html.P("A comprehensive analysis of Airbnb listings in Texas, USA."),
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
                                id="city-filter",
                                options=[{"label": city, "value": city} for city in cities],
                                value="All Cities",
                                clearable=False
                            ),
                        ], width=4),
                        dbc.Col([
                            html.Label("Price Range ($):"),
                            dcc.RangeSlider(
                                id="price-range-slider",
                                min=price_min,
                                max=price_max,
                                step=10,
                                value=[price_min, price_max],
                                marks={i: f"${i}" for i in range(price_min, price_max+1, 200)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            ),
                        ], width=4),
                        dbc.Col([
                            html.Label("Bedrooms:"),
                            dcc.Dropdown(
                                id="bedrooms-filter",
                                options=[{"label": str(i), "value": i} for i in range(1, bedrooms_max+1)],
                                value=[1, 2, 3],
                                multi=True
                            ),
                        ], width=3),
                        dbc.Col([
                            dbc.Button("Apply Filters", id="apply-filter", color="primary", className="mt-4"),
                        ], width=1),
                    ]),
                ])
            ]),
        ])
    ], className="mb-4"),
    
    # Stats cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Total Listings"),
                dbc.CardBody([
                    html.H3(id="total-listings", children=f"{n_listings:,}"),
                ])
            ]),
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Cities"),
                dbc.CardBody([
                    html.H3(id="total-cities", children=f"{n_cities}"),
                ])
            ]),
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Average Price"),
                dbc.CardBody([
                    html.H3(id="avg-price", children=f"${avg_price:.2f}"),
                ])
            ]),
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Average Bedrooms"),
                dbc.CardBody([
                    html.H3(id="avg-bedrooms", children=f"{avg_beds:.1f}"),
                ])
            ]),
        ], width=3),
    ], className="mb-4"),

    # Trend graphs
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Yearly Price Trends"),
                dbc.CardBody([
                    dcc.Graph(id="yearly-rate-trend", figure=create_yearly_rate_trend())
                ])
            ]),
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Moving Average Trend"),
                dbc.CardBody([
                    dcc.Graph(id="moving-average-trend", figure=create_moving_average_trend())
                ])
            ]),
        ], width=6),
    ], className="mb-4"),

    # Box plot and city comparison
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Price Distribution by Bedrooms"),
                dbc.CardBody([
                    dcc.Graph(id="price-by-bedrooms", figure=create_price_by_bedrooms())
                ])
            ]),
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("City Price Comparison"),
                dbc.CardBody([
                    dcc.Graph(id="city-price-comparison", figure=create_city_price_comparison())
                ])
            ]),
        ], width=6),
    ], className="mb-4"),

    # Count by City and Host
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Listings by City and Host"),
                dbc.CardBody([
                    dcc.Graph(id="listings-count", figure=create_listings_count())
                ])
            ]),
        ]),
    ], className="mb-4"),

    # Word Cloud and Sample Table
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Word Cloud from Property Descriptions"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("City Filter for Word Cloud:"),
                            dcc.Dropdown(
                                id="word-cloud-city-filter",
                                options=[{"label": city, "value": city} for city in cities],
                                value="All Cities",
                                clearable=False
                            ),
                        ], width=6),
                        dbc.Col([
                            dbc.Button("Generate Word Cloud", id="generate-word-cloud", color="secondary", className="mt-4"),
                        ], width=6),
                    ]),
                    html.Div([
                        html.Img(id="word-cloud-image", style={"width": "100%"})
                    ], className="mt-3"),
                ])
            ]),
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Sample Listings"),
                dbc.CardBody([
                    html.Label("Number of samples:"),
                    dcc.Slider(
                        id="n-sample-slider",
                        min=5,
                        max=20,
                        step=5,
                        value=10,
                        marks={i: str(i) for i in range(5, 21, 5)},
                    ),
                    dash_table.DataTable(
                        id="sample-table",
                        columns=[
                            {"name": "City", "id": "city"},
                            {"name": "Title", "id": "title"},
                            {"name": "Bedrooms", "id": "bedrooms_count"},
                            {"name": "Price/Night", "id": "average_rate_per_night", "type": "numeric", "format": {"specifier": "$,.2f"}},
                        ],
                        style_cell={
                            'textAlign': 'left',
                            'overflow': 'hidden',
                            'textOverflow': 'ellipsis',
                            'maxWidth': 0,
                        },
                        style_data_conditional=[
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': 'rgb(248, 248, 248)'
                            }
                        ],
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        },
                        page_size=10,
                    ),
                ])
            ]),
        ], width=6),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Listing Keywords"),
                dbc.CardBody([
                    dcc.Graph(
                        id="keyword-chart",
                        figure=px.bar(
                            kw_df,
                            x="keyword",
                            y="pct",
                            color="pct",
                            color_continuous_scale="Viridis",
                            labels={"keyword": "Keyword", "pct": "Percentage of Listings (%)"},
                            title="Percentage of Listings with Key Features",
                        ).update_layout(template="plotly_white")
                    )
                ])
            ]),
        ]),
    ]),
], fluid=True)


# Callbacks
@callback(
    [Output('total-listings', 'children'),
     Output('total-cities', 'children'),
     Output('avg-price', 'children'),
     Output('avg-bedrooms', 'children'),
     Output('yearly-rate-trend', 'figure'),
     Output('moving-average-trend', 'figure'),
     Output('listings-count', 'figure'),
     Output('price-by-bedrooms', 'figure'),
     Output('city-price-comparison', 'figure'),
     Output('keyword-chart', 'figure')],
    [Input('apply-filter', 'n_clicks')],
    [State('city-filter', 'value'),
     State('price-range-slider', 'value'),
     State('bedrooms-filter', 'value')],
    prevent_initial_call=True
)
def update_dashboard(n_clicks, city_filter, price_range, bedrooms_filter):
    n_listings, n_cities, avg_price, avg_beds, filtered_df = get_stats(city_filter, price_range)
    
    if bedrooms_filter:
        filtered_df = filtered_df[filtered_df['bedrooms_count'].isin(bedrooms_filter)]
    
    # Create keyword counts for filtered data
    kw_df_filtered = (
        filtered_df[keywords]
        .sum()
        .rename("count")
        .reset_index()
        .rename(columns={'index': 'keyword'})
    )
    kw_df_filtered['pct'] = kw_df_filtered['count'] / len(filtered_df) * 100
    
    # Create all the updated figures
    yearly_fig = create_yearly_rate_trend(filtered_df)
    moving_avg_fig = create_moving_average_trend(filtered_df)
    listings_fig = create_listings_count(filtered_df)
    price_bedrooms_fig = create_price_by_bedrooms(filtered_df, bedrooms_filter)
    city_price_fig = create_city_price_comparison(filtered_df)
    
    keyword_fig = px.bar(
        kw_df_filtered,
        x="keyword",
        y="pct",
        color="pct",
        color_continuous_scale="Viridis",
        labels={"keyword": "Keyword", "pct": "Percentage of Listings (%)"},
        title="Percentage of Listings with Key Features",
    ).update_layout(template="plotly_white")
    
    return (
        f"{n_listings:,}",
        f"{n_cities}",
        f"${avg_price:.2f}",
        f"{avg_beds:.1f}",
        yearly_fig,
        moving_avg_fig,
        listings_fig,
        price_bedrooms_fig,
        city_price_fig,
        keyword_fig
    )


@callback(
    Output('sample-table', 'data'),
    [Input('n-sample-slider', 'value'),
     Input('apply-filter', 'n_clicks')],
    [State('city-filter', 'value'),
     State('price-range-slider', 'value'),
     State('bedrooms-filter', 'value')],
)
def update_sample(n, n_clicks, city_filter, price_range, bedrooms_filter):
    _, _, _, _, filtered_df = get_stats(city_filter, price_range)
    
    if bedrooms_filter:
        filtered_df = filtered_df[filtered_df['bedrooms_count'].isin(bedrooms_filter)]
    
    return filtered_df.sample(min(n, len(filtered_df))).to_dict('records')


@callback(
    Output('word-cloud-image', 'src'),
    [Input('generate-word-cloud', 'n_clicks'),
     Input('apply-filter', 'n_clicks')],
    [State('word-cloud-city-filter', 'value'),
     State('city-filter', 'value'),
     State('price-range-slider', 'value'),
     State('bedrooms-filter', 'value')],
    prevent_initial_call=True
)
def update_word_cloud(wc_n_clicks, filter_n_clicks, wc_city_filter, city_filter, price_range, bedrooms_filter):
    _, _, _, _, filtered_df = get_stats(city_filter, price_range)
    
    if bedrooms_filter:
        filtered_df = filtered_df[filtered_df['bedrooms_count'].isin(bedrooms_filter)]
        
    return create_word_cloud(filtered_df, wc_city_filter)