import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="IT Helpdesk Analytics & Incident Engine",
    page_icon="🖥️",
    layout="wide"
)

# --- FILE UPLOADER IN SIDEBAR ---
st.sidebar.title("Data Source")
uploaded_file = st.sidebar.file_uploader(
    "Upload custom data (Excel or CSV)", 
    type=["xlsx", "xls", "csv"]
)

@st.cache_data
def load_default_data():
    conn = sqlite3.connect("helpdesk_warehouse.db")
    df = pd.read_sql("SELECT * FROM fact_tickets", conn)
    conn.close()
    return df

# Determine whether to read the uploaded file or default database
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        st.sidebar.success(f"Loaded: {uploaded_file.name}")
    except Exception as e:
        st.sidebar.error(f"Error loading file: {e}")
        df = load_default_data()
else:
    df = load_default_data()
    st.sidebar.info("Using default generated warehouse data (50,000 tickets).")

# Ensure required datetime columns are formatted properly
df['created_at'] = pd.to_datetime(df['created_at'])
df['resolved_at'] = pd.to_datetime(df['resolved_at'])

# Fallback check for missing calculated columns if a raw file is uploaded
if 'resolution_hours' not in df.columns:
    df['resolution_hours'] = ((df['resolved_at'] - df['created_at']).dt.total_seconds() / 3600.0).round(2)

if 'is_sla_breached' not in df.columns:
    sla_targets = {'P1-Critical': 4.0, 'P2-High': 12.0, 'P3-Medium': 48.0, 'P4-Low': 96.0}
    df['sla_target_hours'] = df['priority'].map(sla_targets).fillna(48.0)
    df['is_sla_breached'] = df['resolution_hours'] > df['sla_target_hours']

if 'error_code' not in df.columns:
    df['error_code'] = 'NONE'
