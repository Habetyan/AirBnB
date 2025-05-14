import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from app.utils.data_loader import load_data

dash.register_page(
    __name__,
    path="/technical",
    title="Technical Details",
    name="Technical Details"
)

# Load both the raw and cleaned data
df_raw, df_cleaned = load_data(return_raw=True)

def create_missing_corr_heatmap():
    missing_cols = [col for col in df_raw.columns if df_raw[col].isna().sum() > 0]

    if not missing_cols:
        fig = px.imshow(
            np.array([[0]]),
            title="No Missing Values Found in Dataset"
        )
        return fig

    missing_df = df_raw[missing_cols].isna().astype(int)

    missing_corr = missing_df.corr()

    fig = px.imshow(
        missing_corr,
        x=missing_cols,
        y=missing_cols,
        text_auto='.2f',
        color_continuous_scale='RdBu_r',
        title="Correlation of Missing Values Between Features",
        labels={"color": "Correlation"}
    )

    fig.update_layout(
        height=550,
        width=600,
        xaxis_title="Features",
        yaxis_title="Features",
        margin=dict(l=50, r=50, t=50, b=50),
    )

    fig.update_xaxes(tickangle=-45)

    return fig

def create_feature_corr_heatmap():
    corr_features = [
        'average_rate_per_night',
        'bedrooms_count',
        'price_per_bedroom',
        'description_length',
        'sentiment_score',
        'listing_age'
    ]

    available_features = [f for f in corr_features if f in df_cleaned.columns]

    if len(available_features) < 2:
        fig = px.imshow(
            np.array([[0]]),
            title="Not enough features available for correlation analysis"
        )
        return fig

    corr_matrix = df_cleaned[available_features].corr()

    fig = px.imshow(
        corr_matrix,
        x=available_features,
        y=available_features,
        text_auto='.2f',
        color_continuous_scale='magma',
        title="Correlation Heatmap: Airbnb Pricing & Text Features",
        labels={"color": "Correlation"}
    )

    fig.update_layout(
        height=550,
        width=600,
        xaxis_title="Features",
        yaxis_title="Features",
        margin=dict(l=50, r=50, t=50, b=50),
    )

    fig.update_xaxes(tickangle=-45)

    return fig

def create_feature_distribution(feature_name='average_rate_per_night'):
    if feature_name not in df_cleaned.columns:
        return go.Figure().update_layout(title=f"Feature '{feature_name}' not found in dataset")
    
    if df_cleaned[feature_name].dtype in [np.float64, np.int64]:
        # For numeric features
        fig = go.Figure()
        
        # Add histogram
        fig.add_trace(go.Histogram(
            x=df_cleaned[feature_name],
            opacity=0.7,
            name="Distribution",
            marker_color='royalblue'
        ))
        
        # Add KDE curve
        hist_vals, bin_edges = np.histogram(
            df_cleaned[feature_name].dropna(), 
            bins=50, 
            density=True
        )
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        fig.add_trace(go.Scatter(
            x=bin_centers,
            y=hist_vals,
            mode='lines',
            name='Density',
            line=dict(color='firebrick', width=2)
        ))
        
        fig.update_layout(
            title=f"Distribution of {feature_name}",
            xaxis_title=feature_name,
            yaxis_title="Frequency",
            template='plotly_white',
            bargap=0.1
        )
        
    else:
        # For categorical features
        value_counts = df_cleaned[feature_name].value_counts().head(20)
        
        fig = px.bar(
            x=value_counts.index,
            y=value_counts.values,
            labels={'x': feature_name, 'y': 'Count'},
            title=f"Top Values for {feature_name}"
        )
        
        fig.update_layout(
            xaxis_tickangle=-45,
            template='plotly_white'
        )
        
    return fig

def create_data_cleaning_viz():
    # Before vs After cleaning stats
    before_null = df_raw.isnull().sum().sort_values(ascending=False)
    after_null = df_cleaned.isnull().sum().sort_values(ascending=False)
    
    before_percent = (before_null / len(df_raw) * 100).round(2)
    after_percent = (after_null / len(df_cleaned) * 100).round(2)
    
    # Create a dataframe for the visualization
    columns = [col for col in before_null.index if before_null[col] > 0]
    
    cleaning_data = []
    for col in columns:
        cleaning_data.append({
            'column': col,
            'stage': 'Before Cleaning',
            'missing_percent': before_percent[col]
        })
        cleaning_data.append({
            'column': col,
            'stage': 'After Cleaning',
            'missing_percent': after_percent[col] if col in after_percent.index else 0
        })
    
    cleaning_df = pd.DataFrame(cleaning_data)
    
    fig = px.bar(
        cleaning_df,
        x='column',
        y='missing_percent',
        color='stage',
        barmode='group',
        title='Missing Values Before and After Cleaning (%)',
        labels={'missing_percent': 'Missing Values (%)', 'column': 'Column', 'stage': 'Stage'}
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        template='plotly_white',
    )
    
    return fig

def create_feature_importance():
    # Feature importance visualization for predicting price
    features = [
        'bedrooms_count', 'listing_age', 'description_length', 
        'sentiment_score', 'has_luxury', 'has_family', 'has_pool',
        'has_downtown', 'has_modern', 'has_quiet'
    ]
    
    # Calculate correlation with price for each feature
    feature_corrs = []
    for feature in features:
        if feature in df_cleaned.columns:
            corr = df_cleaned[feature].corr(df_cleaned['average_rate_per_night'])
            feature_corrs.append({
                'feature': feature,
                'correlation': abs(corr),
                'direction': 'Positive' if corr >= 0 else 'Negative'
            })
    
    corr_df = pd.DataFrame(feature_corrs).sort_values('correlation', ascending=False)
    
    fig = px.bar(
        corr_df,
        x='feature',
        y='correlation',
        color='direction',
        title='Feature Correlation with Price (Absolute Value)',
        labels={'correlation': 'Absolute Correlation', 'feature': 'Feature'}
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        template='plotly_white'
    )
    
    return fig

def create_sentiment_price_plot():
    # Create a scatter plot of sentiment vs. price
    if 'sentiment_score' in df_cleaned.columns:
        fig = px.scatter(
            df_cleaned,
            x='sentiment_score',
            y='average_rate_per_night',
            color='bedrooms_count',
            opacity=0.6,
            title='Sentiment Score vs. Price',
            labels={
                'sentiment_score': 'Sentiment Score',
                'average_rate_per_night': 'Average Rate per Night ($)',
                'bedrooms_count': 'Bedrooms'
            },
            color_continuous_scale='Viridis'
        )
        
        # Add regression line
        fig.update_layout(template='plotly_white')
        
        # Add moving average trendline
        x_range = np.linspace(
            df_cleaned['sentiment_score'].min(),
            df_cleaned['sentiment_score'].max(),
            100
        )
        
        # Simple moving average
        sentiment_price_df = df_cleaned[['sentiment_score', 'average_rate_per_night']].dropna()
        sentiment_price_df = sentiment_price_df.sort_values('sentiment_score')
        
        window_size = min(50, len(sentiment_price_df))
        ma_series = sentiment_price_df['average_rate_per_night'].rolling(window=window_size).mean()
        
        fig.add_trace(go.Scatter(
            x=sentiment_price_df['sentiment_score'],
            y=ma_series,
            mode='lines',
            line=dict(color='red', width=3),
            name='Trend'
        ))
        
    else:
        fig = go.Figure().update_layout(title="Sentiment score not found in dataset")
    
    return fig

# Create layout
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("Technical Details & Data Methodology"),
            html.P("This page provides detailed information about the data processing and correlation analysis."),
            html.Hr(),

            html.Div([
                html.H4("Introduction"),
                html.P([
                    "Sharing economy and vacation rentals are among the hottest topics that has touched millions of lives across the globe. ",
                    "Airbnb has been instrumental in this space and currently operating in more than 191 countries. ",
                    "Hence, it'd be good idea to analyze this data and uncover insights."
                ]),

                html.H4("Dataset Overview"),
                html.P([
                    f"This dataset contains {df_raw.shape[0]:,} property listings from Texas, United States. ",
                    "The data was extracted by PromptCloud's Data-as-a-Service solution and includes the following fields:"
                ]),

                html.Ul([
                    html.Li("Rate per night"),
                    html.Li("Number of bedrooms"),
                    html.Li("City"),
                    html.Li("Joining month and year"),
                    html.Li("Longitude and Latitude"),
                    html.Li("Property description"),
                    html.Li("Property title"),
                    html.Li("Property URL")
                ]),

                html.H4("Data Preparation"),
                html.P([
                    "The raw data required several preprocessing steps to make it suitable for analysis. ",
                    "Below are the key data manipulations performed:"
                ]),

                html.Ul([
                    html.Li([
                        html.Strong("Cleaning & Type Conversion: "),
                        "Dollar signs were removed from rates, missing values were identified, and dates were properly formatted."
                    ]),
                    html.Li([
                        html.Strong("Missing Value Imputation: "),
                        "KNN (K-Nearest Neighbors) imputation was used to fill missing values in numeric fields based on similar records."
                    ]),
                    html.Li([
                        html.Strong("Text-based Feature Extraction: "),
                        "Missing bedroom counts were inferred from property descriptions using pattern matching."
                    ]),
                    html.Li([
                        html.Strong("Geospatial Clustering: "),
                        "K-means clustering was applied to latitude/longitude to identify geographic regions."
                    ]),
                    html.Li([
                        html.Strong("Feature Engineering: "),
                        "Additional features like price_per_bedroom, listing_age, and sentiment_score were calculated."
                    ]),
                    html.Li([
                        html.Strong("Sentiment Analysis: "),
                        "TextBlob was used to analyze the sentiment of property descriptions."
                    ]),
                    html.Li([
                        html.Strong("Keyword Extraction: "),
                        "Binary flags for keywords like 'luxury', 'family', 'quiet', etc. were created from descriptions."
                    ])
                ]),
            ], className="mb-4"),
        ])
    ]),

    # Data cleaning visualization
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Data Cleaning Effectiveness"),
                dbc.CardBody([
                    dcc.Graph(
                        id="data-cleaning-viz",
                        figure=create_data_cleaning_viz()
                    )
                ])
            ])
        ])
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            html.H4("Data Quality Analysis"),
            html.P([
                "Before diving into the analysis, it's important to understand the quality of the data. ",
                "The visualizations below show correlations between missing values and between key features in the dataset."
            ]),
        ])
    ]),

    dbc.Row([
        dbc.Col([
            html.H5("Missing Value Correlation"),
            dcc.Graph(
                id="missing-correlation-heatmap",
                figure=create_missing_corr_heatmap()
            ),
            html.P(
                "According to the missing value correlation heatmap, we can see correlation only between NA values for latitude and longitude, which is expected since these geographic coordinates are typically collected together."),
        ], md=6),

        dbc.Col([
            html.H5("Feature Correlation"),
            dcc.Graph(
                id="feature-correlation-heatmap",
                figure=create_feature_corr_heatmap()
            ),
            html.P([
                "This heatmap reveals interesting relationships between key features. Notable insights include:",
                html.Ul([
                    html.Li("Average rate per night positively correlates with bedroom count"),
                    html.Li(
                        "Price per bedroom negatively correlates with bedroom count, suggesting economies of scale"),
                    html.Li("Sentiment score and description length have a weak relationship with pricing")
                ])
            ]),
        ], md=6),
    ], className="mb-4"),

    # Feature Distribution Explorer
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Feature Distribution Explorer"),
                dbc.CardBody([
                    html.Label("Select Feature:"),
                    dcc.Dropdown(
                        id="feature-selector",
                        options=[
                            {"label": "Average Rate per Night", "value": "average_rate_per_night"},
                            {"label": "Bedrooms Count", "value": "bedrooms_count"},
                            {"label": "Price per Bedroom", "value": "price_per_bedroom"},
                            {"label": "Listing Age (days)", "value": "listing_age"},
                            {"label": "Description Length", "value": "description_length"},
                            {"label": "Sentiment Score", "value": "sentiment_score"},
                            {"label": "City", "value": "city"}
                        ],
                        value="average_rate_per_night"
                    ),
                    dcc.Graph(
                        id="feature-distribution-plot",
                        figure=create_feature_distribution()
                    )
                ])
            ])
        ])
    ], className="mb-4"),
    
    # Feature Importance and Sentiment Analysis
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Feature Importance for Price Prediction"),
                dbc.CardBody([
                    dcc.Graph(
                        id="feature-importance-plot",
                        figure=create_feature_importance()
                    )
                ])
            ])
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Sentiment Analysis vs. Price"),
                dbc.CardBody([
                    dcc.Graph(
                        id="sentiment-price-plot",
                        figure=create_sentiment_price_plot()
                    )
                ])
            ])
        ], md=6)
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            html.H4("Further Analysis"),
            html.P([
                "The insights from these correlation analyses inform the interactive visualizations available on the home page and geographic analysis sections. Use the navigation bar to explore the interactive features."
            ]),
            dbc.Button("Go to Home", color="primary", href="/", className="me-2 mt-2"),
            dbc.Button("Go to Geo Analysis", color="success", href="/geo_visualizations", className="mt-2"),
        ])
    ])
], fluid=True)

# Callbacks
@callback(
    Output("feature-distribution-plot", "figure"),
    Input("feature-selector", "value")
)
def update_feature_distribution(feature_name):
    return create_feature_distribution(feature_name)