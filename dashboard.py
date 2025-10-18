import os
from io import BytesIO
import streamlit as st
import pandas as pd
import boto3
import mysql.connector
from mysql.connector import errorcode
import plotly.express as px

# Configuración
st.set_page_config(page_title="Books Rating Analysis", layout="wide")

# Variables de entorno
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME", "books_db")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
S3_BUCKET = os.getenv("S3_BUCKET", "xideralaws-curso-benjamin-2")
S3_KEY = os.getenv("S3_KEY", "transformed/matched_books_final.csv")

# Funciones de carga
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
        st.error(f"Error leyendo desde S3: {e}")
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
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_BAD_DB_ERROR:
            st.warning(f"Base de datos '{DB_NAME}' no encontrada. Usando S3 como fallback.")
        elif err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            st.warning("Credenciales MySQL incorrectas. Usando S3 como fallback.")
        elif err.errno == errorcode.ER_NO_SUCH_TABLE:
            st.warning(f"Tabla '{table_name}' no existe. Usando S3 como fallback.")
        else:
            st.warning(f"Error MySQL: {err}. Usando S3 como fallback.")
        return pd.DataFrame()

def load_data():
    if DB_HOST and DB_USER and DB_PASS:
        df = read_table_from_mysql("matched_books")
        if not df.empty:
            st.sidebar.success("📊 Datos cargados desde MySQL")
            return df, "MySQL"
    
    df = read_csv_from_s3(S3_BUCKET, S3_KEY, AWS_REGION)
    if not df.empty:
        st.sidebar.info("📦 Datos cargados desde S3")
        return df, "S3"
    
    st.error("No se pudieron cargar los datos desde MySQL ni S3")
    return pd.DataFrame(), "None"

# Cargar datos
df, data_source = load_data()

if df.empty:
    st.stop()

# Limpiar columna de precio (NUEVO - IMPORTANTE)
if 'price' in df.columns:
    # Eliminar NaN y valores extremos
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df = df[df['price'].notna()]  # Eliminar NaN
    df = df[df['price'] > 0]  # Eliminar precios negativos/cero
    df = df[df['price'] < 500]  # Eliminar outliers extremos (libros >$500)

st.title("📚 Amazon vs Goodreads: Rating Analysis")
st.markdown(f"**Data Source:** {data_source} | **Books:** {len(df):,}")

# SIDEBAR
st.sidebar.header("🔍 Filters")

show_outliers = st.sidebar.checkbox("Show only outliers (>2 pts difference)")

st.sidebar.subheader("Goodreads Rating")
gr_min, gr_max = st.sidebar.slider(
    "Select range",
    0.0, 10.0, (0.0, 10.0),
    key="gr_range"
)

st.sidebar.subheader("Amazon Rating")
amz_min, amz_max = st.sidebar.slider(
    "Select range",
    0.0, 10.0, (0.0, 10.0),
    key="amz_range"
)

# Filtro de precio CORREGIDO
price_filter_enabled = False
if 'price' in df.columns and len(df[df['price'].notna()]) > 0:
    st.sidebar.subheader("Price Range")
    
    # Calcular min/max de precios válidos
    valid_prices = df['price'].dropna()
    price_min = float(valid_prices.min())
    price_max = float(valid_prices.max())
    
    # Mostrar cuántos libros tienen precio
    st.sidebar.caption(f"{len(valid_prices):,} books have price data")
    
    # Checkbox para activar filtro
    price_filter_enabled = st.sidebar.checkbox("Enable price filter")
    
    if price_filter_enabled:
        price_range = st.sidebar.slider(
            "Select price ($)",
            price_min, price_max, (price_min, price_max)
        )

st.sidebar.subheader("🔎 Search")
search_term = st.sidebar.text_input("Search by title or author")

# APLICAR FILTROS
df_filtered = df.copy()

if show_outliers:
    df_filtered = df_filtered[df_filtered['is_outlier'] == True]

df_filtered = df_filtered[
    (df_filtered['goodreads_rating_norm'] >= gr_min) &
    (df_filtered['goodreads_rating_norm'] <= gr_max) &
    (df_filtered['amazon_rating_norm'] >= amz_min) &
    (df_filtered['amazon_rating_norm'] <=
