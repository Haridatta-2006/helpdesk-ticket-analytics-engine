import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import uuid
import os
from datetime import datetime, timedelta
import random

st.set_page_config(
    page_title="IT Helpdesk Analytics & Incident Engine",
    page_icon="🖥️",
    layout="wide"
)

# --- AUTO-GENERATE DATABASE IF RUNNING ON CLOUD FOR THE FIRST TIME ---
DB_FILE = "helpdesk_warehouse.db"

def initialize_database():
    if not os.path.exists(DB_FILE):
        with st.spinner("Initializing 50,000 enterprise tickets data warehouse..."):
            categories = ['Access/MFA', 'Network/VPN', 'Hardware', 'Software', 'Database']
            teams = ['Tier-1 Support', 'NetOps', 'SysAdmin', 'SecOps', 'Desktop-Support']
            priorities = ['P1-Critical', 'P2-High', 'P3-Medium', 'P4-Low']
            sla_targets = {'P1-Critical': 4.0, 'P2-High': 12.0, 'P3-Medium': 48.0, 'P4-Low': 96.0}

            start_time = datetime(2026, 1, 1, 9, 0, 0)
            data = []

            for _ in range(50000):
                created = start_time + timedelta(minutes=random.randint(0, 90 * 24 * 60))
                priority = random.choices(priorities, weights=[0.05, 0.15, 0.50, 0.30])[0]
                base_hours = {'P1-Critical': 2.0, 'P2-High': 8.0, 'P3-Medium': 24.0, 'P4-Low': 72.0}[priority]
                actual_hours = max(0.2, random.gauss(base_hours, base_hours * 0.4))
                resolved = created + timedelta(hours=actual_hours)
                
                has_error = random.random() < 0.08
                err = f"ERR_50{random.randint(0, 4)}" if has_error else 'NONE'

                data.append({
                    "ticket_id": f"TCK-{uuid.uuid4().hex[:8].upper()}",
                    "created_at": created.isoformat(),
                    "resolved_at": resolved.isoformat(),
                    "category": random.choice(categories),
                    "priority": priority,
                    "assigned_team": random.choice(teams),
                    "error_code": err,
                    "reopen_count": random.choices([0, 1, 2], weights=[0.85, 0.10, 0.05])[0]
                })

            # Intentional outage spike
            outage_start = start_time + timedelta(days=15, hours=10)
            for _ in range(500):
                data.append({
                    "ticket_id": f"TCK-{uuid.uuid4().hex[:8].upper()}",
                    "created_at": (outage_start + timedelta(minutes=random.randint(0, 120))).isoformat(),
                    "resolved_at": (outage_start + timedelta(hours=random.uniform(1.5, 4.0))).isoformat(),
                    "category": "Network/VPN",
                    "priority": "P1-Critical",
                    "assigned_team": "NetOps",
                    "error_code": "ERR_502",
                    "reopen_count": 0
                })

            df = pd.DataFrame(data)
            df['created_at_dt'] = pd.to_datetime(df['created_at'])
            df['resolved_at_dt'] = pd.to_datetime(df['resolved_at'])
            df['resolution_hours'] = ((df['resolved_at_dt'] - df['created_at_dt']).dt.total_seconds() / 3600.0).round(2)
            df['sla_target_hours'] = df['priority'].map(sla_targets)
            df['is_sla_breached'] = df['resolution_hours'] > df['sla_target_hours']
            df = df.drop(columns=['created_at_dt', 'resolved_at_dt'])

            conn = sqlite3.connect(DB_FILE)
            df.to_sql('fact_tickets', conn, if_exists='replace', index=False)
            conn.close()

initialize_database()

# --- SIDEBAR & FILE UPLOADER ---
st.sidebar.title("Data Source")
uploaded_file = st.sidebar.file_uploader("Upload custom data (CSV or Excel)", type=["csv", "xlsx", "xls"])

@st.cache_data
def load_default_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT * FROM fact_tickets", conn)
    conn.close()
    return df

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
    st.sidebar.info("Using default 50,000 ticket dataset.")

# Ensure datetimes and metrics exist
df['created_at'] = pd.to_datetime(df['created_at'])
df['resolved_at'] = pd.to_datetime(df['resolved_at'])

if 'resolution_hours' not in df.columns:
    df['resolution_hours'] = ((df['resolved_at'] - df['created_at']).dt.total_seconds() / 3600.0).round(2)

if 'is_sla_breached' not in df.columns:
    sla_map = {'P1-Critical': 4.0, 'P2-High': 12.0, 'P3-Medium': 48.0, 'P4-Low': 96.0}
    df['sla_target_hours'] = df['priority'].map(sla_map).fillna(48.0)
    df['is_sla_breached'] = df['resolution_hours'] > df['sla_target_hours']

if 'error_code' not in df.columns:
    df['error_code'] = 'NONE'

# --- FILTERS ---
selected_category = st.sidebar.multiselect("Category", options=df['category'].unique(), default=df['category'].unique())
selected_priority = st.sidebar.multiselect("Priority", options=df['priority'].unique(), default=df['priority'].unique())

filtered_df = df[(df['category'].isin(selected_category)) & (df['priority'].isin(selected_priority))]

# --- DASHBOARD UI ---
st.title("🖥️ IT Helpdesk Analytics & Incident Detection Platform")
st.markdown("Automated batch processing, SLA tracking, and Z-score outage detection for enterprise support records.")

k1, k2, k3, k4 = st.columns(4)
total_tickets = len(filtered_df)
avg_res = filtered_df['resolution_hours'].mean() if total_tickets > 0 else 0
breach_pct = (filtered_df['is_sla_breached'].sum() / total_tickets * 100) if total_tickets > 0 else 0
err_count = (filtered_df['error_code'] != 'NONE').sum()

k1.metric("Total Tickets", f"{total_tickets:,}")
k2.metric("Avg Resolution Time", f"{avg_res:.1f} hrs")
k3.metric("SLA Breach Rate", f"{breach_pct:.1f}%")
k4.metric("Error Incidents", f"{err_count:,}")

st.markdown("---")

# --- ANOMALY GRAPH ---
st.subheader("🚨 Incident Detection: Rolling Volume Spikes (Outages)")
hourly_data = filtered_df.set_index('created_at').resample('1h').agg(ticket_count=('ticket_id', 'count')).reset_index()
hourly_data['rolling_mean'] = hourly_data['ticket_count'].rolling(window=24, min_periods=1).mean()
hourly_data['rolling_std'] = hourly_data['ticket_count'].rolling(window=24, min_periods=1).std().fillna(1)
hourly_data['upper_bound'] = hourly_data['rolling_mean'] + (2.5 * hourly_data['rolling_std'])
hourly_data['is_anomaly'] = hourly_data['ticket_count'] > hourly_data['upper_bound']

fig = go.Figure()
fig.add_trace(go.Scatter(x=hourly_data['created_at'], y=hourly_data['ticket_count'], mode='lines', name='Hourly Volume', line=dict(color='#2b83ba')))
fig.add_trace(go.Scatter(x=hourly_data['created_at'], y=hourly_data['upper_bound'], mode='lines', name='Threshold (μ + 2.5σ)', line=dict(color='orange', dash='dot')))
anomalies = hourly_data[hourly_data['is_anomaly']]
fig.add_trace(go.Scatter(x=anomalies['created_at'], y=anomalies['ticket_count'], mode='markers', name='Detected Spike', marker=dict(color='red', size=8)))
fig.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20), xaxis_title="Time", yaxis_title="Hourly Tickets")
st.plotly_chart(fig, use_container_width=True)

# --- 15% OPTIMIZATION SLIDER ---
st.markdown("---")
st.subheader("⚙️ What-If Simulation: Support Automation Impact")
c1, c2 = st.columns([1, 2])

with c1:
    target_reduction = st.slider("Target Automation Reduction (%)", 5, 30, 15, 1)
    projected = avg_res * (1 - target_reduction / 100)
    saved = (avg_res - projected) * total_tickets
    st.info(f"Targeting **{target_reduction}% cut** drops average resolution to **{projected:.1f} hrs**.")
    st.success(f"Est. Engineering Hours Saved: **{saved:,.0f} hrs**")

with c2:
    team_perf = filtered_df.groupby('assigned_team')['resolution_hours'].mean().reset_index()
    team_perf['Optimized'] = team_perf['resolution_hours'] * (1 - target_reduction / 100)
    fig_bar = px.bar(team_perf, x='assigned_team', y=['resolution_hours', 'Optimized'], barmode='group', title="Current vs. Projected Resolution Time per Team")
    st.plotly_chart(fig_bar, use_container_width=True)
