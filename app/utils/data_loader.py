import pandas as pd
import numpy as np
import re
from pathlib import Path

from sklearn.impute import KNNImputer
from sklearn.preprocessing import LabelEncoder
from sklearn.cluster import KMeans
from textblob import TextBlob

PARQUET_PATH = Path("Airbnb_Texas.parquet")
PARQUET_RAW_PATH = Path("Airbnb_Texas_raw.parquet")


def load_data(return_raw=False):
    """
    Load and process the Airbnb Texas data

    Parameters:
    -----------
    return_raw : bool, default=False
        If True, returns both raw and cleaned dataframes (df_raw, df_cleaned)
        If False, returns only the cleaned dataframe

    Returns:
    --------
    pandas.DataFrame or tuple of pandas.DataFrame
        Cleaned dataframe or (raw_df, cleaned_df) if return_raw=True
    """
    # Check if we already have processed data
    if PARQUET_PATH.exists() and (not return_raw or PARQUET_RAW_PATH.exists()):
        df_cleaned = pd.read_parquet(PARQUET_PATH)
        if return_raw:
            df_raw = pd.read_parquet(PARQUET_RAW_PATH)
            return df_raw, df_cleaned
        return df_cleaned

    try:
        df = pd.read_parquet(PARQUET_PATH)
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        # Return a simple placeholder DataFrame for debugging
        return pd.DataFrame({'Error': ['Data loading failed']})

    if return_raw and not PARQUET_RAW_PATH.exists():
        df.to_parquet(PARQUET_RAW_PATH, compression="snappy", index=False)

    df_cleaned = df.copy()

    df_cleaned['average_rate_per_night'] = (
        df_cleaned['average_rate_per_night']
        .replace(r'[\$,]', '', regex=True)
        .astype(float)
    )
    df_cleaned['bedrooms_count'] = pd.to_numeric(df_cleaned['bedrooms_count'], errors='coerce')
    df_cleaned['date_of_listing'] = pd.to_datetime(df_cleaned['date_of_listing'], errors='coerce')

    df_cleaned['latitude'] = df_cleaned.groupby('city')['latitude'].transform(lambda x: x.fillna(x.mean()))
    df_cleaned['longitude'] = df_cleaned.groupby('city')['longitude'].transform(lambda x: x.fillna(x.mean()))

    # Extract bedrooms from description
    def extract_bedrooms_fixed(desc):
        if pd.isnull(desc): return np.nan
        for pat in [r'(\d+)\s*bedrooms?', r'(\d+)\s*beds?', r'(\d+)\s*rooms?']:
            m = re.search(pat, desc, flags=re.IGNORECASE)
            if m: return int(m.group(1))
        word_map = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        for w, n in word_map.items():
            if re.search(rf'\b{w}[-\s]?bedroom', desc, flags=re.IGNORECASE): return n
        return 1 if "studio" in desc.lower() else np.nan

    mask = df_cleaned['bedrooms_count'].isna()
    df_cleaned.loc[mask, 'bedrooms_count'] = (
        df_cleaned.loc[mask, 'description'].apply(extract_bedrooms_fixed)
    )

    # Drop rows missing critical columns (except bedrooms_count)
    required = [c for c in df_cleaned.columns if c != 'bedrooms_count']
    df_cleaned = df_cleaned.dropna(subset=required)

    # KNN-impute numeric features
    knn_cols = ['average_rate_per_night', 'latitude', 'longitude', 'bedrooms_count']
    imputer = KNNImputer(n_neighbors=5)
    df_cleaned[knn_cols] = imputer.fit_transform(df_cleaned[knn_cols])
    df_cleaned['bedrooms_count'] = df_cleaned['bedrooms_count'].round().astype('Int64')

    # Engineered features
    df_cleaned['price_per_bedroom'] = df_cleaned['average_rate_per_night'] / df_cleaned['bedrooms_count']
    df_cleaned['listing_year'] = df_cleaned['date_of_listing'].dt.year
    df_cleaned['listing_month'] = df_cleaned['date_of_listing'].dt.month
    df_cleaned['listing_dayofweek'] = df_cleaned['date_of_listing'].dt.dayofweek
    df_cleaned['listing_age'] = (pd.Timestamp.today() - df_cleaned['date_of_listing']).dt.days

    # Encode city
    le = LabelEncoder()
    df_cleaned['city_encoded'] = le.fit_transform(df_cleaned['city'].astype(str))

    # Geo-clustering
    geo = df_cleaned[['latitude', 'longitude']].dropna()
    km = KMeans(n_clusters=5, random_state=0)
    df_cleaned.loc[geo.index, 'geo_cluster'] = km.fit_predict(geo)

    # Text features
    df_cleaned['description_length'] = df_cleaned['description'].astype(str).str.len()
    keywords = ['luxury', 'family', 'quiet', 'downtown', 'pool', 'modern']
    for kw in keywords:
        df_cleaned[f'has_{kw}'] = (
            df_cleaned['description']
            .astype(str)
            .str.contains(kw, case=False, na=False)
            .astype(int)
        )
    df_cleaned['sentiment_score'] = (
        df_cleaned['description']
        .astype(str)
        .apply(lambda txt: TextBlob(txt).sentiment.polarity)
    )

    # Cache to Parquet and return
    df_cleaned.to_parquet(PARQUET_PATH, compression="snappy", index=False)

    if return_raw:
        return df, df_cleaned
    return df_cleaned
