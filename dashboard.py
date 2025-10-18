import os
from io import BytesIO
import streamlit as st
import pandas as pd
import boto3
import mysql.connector
from mysql.connector import errorcode
import plotly.express as px

st.set_page_config(page_title="Books Rating Analysis", layout="wide")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME", "books_db")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
S3_BUCKET = os.getenv("S3_BUCKET", "xideralaws-curso-benjamin-2")
S3_KEY = os.getenv("S3_KEY", "transformed/matched_books_final.csv")

@st.cache_data
def read_csv_from_s3(bucket: str, key: str, region: str) -> pd.DataFrame:
    try:
        s3 = boto3.client("s3", region_name=region)
        obj = s3.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()
        df = pd.read_csv(BytesIO(body))
        if 'price_avg' in df.columns:
            df = df.rename(columns={'price_avg': 'price'})
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

@st.cache_data
def read_table_from_mysql(table_name: str) -> pd.DataFrame:
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        query = f"SELECT * FROM {table_name};"
        df = pd.read_sql(query, conn)
        conn.close()
        if 'price_avg' in df.columns:
            df = df.rename(columns={'price_avg': 'price'})
        return df
    except mysql.connector.Error:
        return pd.DataFrame()

def load_data():
    if DB_HOST and DB_USER and DB_PASS:
        df = read_table_from_mysql("matched_books")
        if not df.empty:
            st.sidebar.success("📊 Datos desde MySQL")
            return df, "MySQL"
    df = read_csv_from_s3(S3_BUCKET, S3_KEY, AWS_REGION)
    if not df.empty:
        st.sidebar.info("📦 Datos desde S3")
        return df, "S3"
    return pd.DataFrame(), "None"

df, data_source = load_data()

if df.empty:
    st.stop()

st.title("📚 Amazon vs Goodreads: Rating Analysis")
st.markdown(f"**Data Source:** {data_source} | **Books:** {len(df):,}")

# SIDEBAR - SOLO Filtros de Rating y Outliers
st.sidebar.header("🔍 Filters")

show_outliers = st.sidebar.checkbox("Show only outliers (>2 pts difference)")

st.sidebar.subheader("Goodreads Rating")
gr_min, gr_max = st.sidebar.slider("Select range", 0.0, 10.0, (0.0, 10.0), key="gr")

st.sidebar.subheader("Amazon Rating")
amz_min, amz_max = st.sidebar.slider("Select range", 0.0, 10.0, (0.0, 10.0), key="amz")

st.sidebar.subheader("🔎 Search")
search_term = st.sidebar.text_input("Search by title or author")

# APLICAR FILTROS (SIN PRECIO)
df_filtered = df.copy()

if show_outliers:
    df_filtered = df_filtered[df_filtered['is_outlier'] == True]

df_filtered = df_filtered[
    (df_filtered['goodreads_rating_norm'] >= gr_min) &
    (df_filtered['goodreads_rating_norm'] <= gr_max) &
    (df_filtered['amazon_rating_norm'] >= amz_min) &
    (df_filtered['amazon_rating_norm'] <= amz_max)
]

if search_term:
    df_filtered = df_filtered[
        df_filtered['title'].str.contains(search_term, case=False, na=False) |
        df_filtered['authors_goodreads'].str.contains(search_term, case=False, na=False)
    ]

# KPIS
st.header(" Key Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Books", f"{len(df_filtered):,}")

with col2:
    avg_diff = df_filtered['rating_difference'].mean()
    st.metric("Avg Difference", f"{avg_diff:.2f} pts")

with col3:
    outliers = df_filtered['is_outlier'].sum()
    st.metric("Outliers", f"{outliers}")

with col4:
    # Mostrar cuántos tienen precio
    if 'price' in df_filtered.columns:
        books_with_price = df_filtered[df_filtered['price'].notna()]
        st.metric("Books with Price", f"{len(books_with_price):,}")
    else:
        st.metric("Books with Price", "N/A")

st.divider()

# SCATTER PLOT
st.header("📈 Ratings Comparison")

df_filtered['color'] = df_filtered['is_outlier'].map({True: '🔴 Outlier', False: '🔵 Normal'})

hover_cols = ['title', 'authors_goodreads', 'rating_difference']
if 'price' in df_filtered.columns:
    hover_cols.append('price')

fig = px.scatter(
    df_filtered,
    x='goodreads_rating_norm',
    y='amazon_rating_norm',
    color='color',
    hover_data=hover_cols,
    labels={
        'goodreads_rating_norm': 'Goodreads (0-10)',
        'amazon_rating_norm': 'Amazon (0-10)',
        'color': 'Type'
    },
    color_discrete_map={'🔴 Outlier': 'red', '🔵 Normal': 'lightblue'}
)

fig.add_shape(
    type='line',
    x0=0, y0=0, x1=10, y1=10,
    line=dict(color='gray', dash='dash')
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# PRICE ANALYSIS - Solo si hay libros con precio
if 'price' in df_filtered.columns:
    books_with_price = df_filtered[df_filtered['price'].notna() & (df_filtered['price'] > 0)]
    
    if len(books_with_price) > 0:
        st.header("Price Analysis")
        st.info(f" Analysis based on **{len(books_with_price)} books** with price data ({len(books_with_price)/len(df_filtered)*100:.1f}% of filtered books)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Price Distribution")
            fig_price = px.histogram(
                books_with_price,
                x='price',
                nbins=30,
                labels={'price': 'Price ($)'}
            )
            st.plotly_chart(fig_price, use_container_width=True)
            
            # Stats
            st.metric("Average Price", f"${books_with_price['price'].mean():.2f}")
            st.caption(f"Min: ${books_with_price['price'].min():.2f} | Max: ${books_with_price['price'].max():.2f}")
        
        with col2:
            st.subheader("Price vs Amazon Rating")
            fig_scatter = px.scatter(
                books_with_price,
                x='price',
                y='amazon_rating_norm',
                color='is_outlier',
                hover_data=['title', 'authors_goodreads'],
                labels={'price': 'Price ($)', 'amazon_rating_norm': 'Amazon Rating'},
                color_discrete_map={True: 'red', False: 'lightblue'}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
            
            # Correlation
            corr = books_with_price['price'].corr(books_with_price['amazon_rating_norm'])
            st.metric("Price-Rating Correlation", f"{corr:.3f}")
            if abs(corr) < 0.3:
                st.caption(" Weak correlation - price doesn't predict rating")
            elif corr > 0:
                st.caption(" Positive - expensive books rated higher")
            else:
                st.caption(" Negative - cheaper books rated higher")
        
        st.divider()

# TOP OUTLIERS
st.header(" Top 10 Biggest Discrepancies")

outliers_df = df_filtered[df_filtered['is_outlier'] == True].nlargest(10, 'rating_difference')

if len(outliers_df) > 0:
    display_cols = ['title', 'authors_goodreads', 'goodreads_rating_norm', 'amazon_rating_norm', 'rating_difference']
    if 'price' in outliers_df.columns:
        display_cols.append('price')
    
    outliers_display = outliers_df[display_cols].copy()
    
    rename_map = {
        'title': 'Title',
        'authors_goodreads': 'Author',
        'goodreads_rating_norm': 'Goodreads',
        'amazon_rating_norm': 'Amazon',
        'rating_difference': 'Difference',
        'price': 'Price ($)'
    }
    outliers_display = outliers_display.rename(columns=rename_map)
    
    for col in ['Goodreads', 'Amazon', 'Difference']:
        if col in outliers_display.columns:
            outliers_display[col] = outliers_display[col].round(2)
    
    if 'Price ($)' in outliers_display.columns:
        outliers_display['Price ($)'] = outliers_display['Price ($)'].round(2)
    
    st.dataframe(outliers_display, use_container_width=True, hide_index=True)
else:
    st.info("No outliers found with current filters")

st.divider()

# PLATFORM COMPARISON
st.header(" Platform Comparison")

col1, col2, col3 = st.columns(3)

with col1:
    avg_gr = df_filtered['goodreads_rating_norm'].mean()
    st.metric("Avg Goodreads", f"{avg_gr:.2f}/10")

with col2:
    avg_amz = df_filtered['amazon_rating_norm'].mean()
    st.metric("Avg Amazon", f"{avg_amz:.2f}/10")

with col3:
    diff = abs(avg_amz - avg_gr)
    higher = "Amazon" if avg_amz > avg_gr else "Goodreads"
    st.metric(f"{higher} is higher by", f"{diff:.2f} pts")

st.divider()

# FULL TABLE
with st.expander("🔍 View All Books"):
    display_cols = ['title', 'authors_goodreads', 'goodreads_rating_norm', 'amazon_rating_norm', 'rating_difference', 'is_outlier']
    if 'price' in df_filtered.columns:
        display_cols.insert(5, 'price')
    
    st.dataframe(df_filtered[display_cols], use_container_width=True, hide_index=True)
