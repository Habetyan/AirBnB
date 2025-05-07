import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.express as px
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
    ]),

    html.Br(),

    dbc.Row([
        dbc.Col([
            html.H4("Further Analysis"),
            html.P([
                "The insights from these correlation analyses inform the interactive visualizations available on the ",
                html.A("Analysis", href="/analysis"),
                " page. Use the navigation bar above to explore these interactive features."
            ]),
            dbc.Button("Go to Analysis", color="primary", href="/analysis", className="mt-2"),
        ])
    ])
], fluid=True)