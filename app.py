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

# Connect to the SQLite warehouse built in Step 5
@st.cache_data
def load_data():
    conn = sqlite3.connect("helpdesk_warehouse.db")
    df = pd.read_sql("SELECT * FROM fact_tickets", conn)
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['resolved_at'] = pd.to_datetime(df['resolved_at'])
    conn.close()
    return df

df = load_data()

# --- SIDEBAR CONTROLS ---
st.sidebar.title("Operational Controls")
selected_category = st.sidebar.multiselect(
    "Filter by Category",
    options=df['category'].unique(),
    default=df['category'].unique()
)

selected_priority = st.sidebar.multiselect(
    "Filter by Priority",
    options=df['priority'].unique(),
    default=df['priority'].unique()
)

filtered_df = df[
    (df['category'].isin(selected_category)) & 
    (df['priority'].isin(selected_priority))
]

# --- HEADER & KPI SUMMARY ---
st.title("🖥️ IT Helpdesk Analytics & Incident Detection Platform")
st.markdown("Automated batch processing, SLA tracking, and Z-score outage detection for 50,000+ support records.")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

total_tickets = len(filtered_df)
avg_resolution = filtered_df['resolution_hours'].mean()
sla_breach_rate = (filtered_df['is_sla_breached'].sum() / total_tickets) * 100 if total_tickets > 0 else 0
error_tickets = (filtered_df['error_code'] != 'NONE').sum()

kpi1.metric("Total Tickets", f"{total_tickets:,}")
kpi2.metric("Avg Resolution Time", f"{avg_resolution:.1f} hrs")
kpi3.metric("SLA Breach Rate", f"{sla_breach_rate:.1f}%")
kpi4.metric("Incident Error Tickets", f"{error_tickets:,}")

st.markdown("---")

# --- ANOMALY & OUTAGE SPIKE VISUALIZATION ---
st.subheader("🚨 Incident Detection: Rolling Volume Spikes (Outages)")

# Resample ticket creation into hourly bins
hourly_data = filtered_df.set_index('created_at').resample('1h').agg(
    ticket_count=('ticket_id', 'count')
).reset_index()

hourly_data['rolling_mean'] = hourly_data['ticket_count'].rolling(window=24, min_periods=1).mean()
hourly_data['rolling_std'] = hourly_data['ticket_count'].rolling(window=24, min_periods=1).std().fillna(1)
hourly_data['upper_bound'] = hourly_data['rolling_mean'] + (2.5 * hourly_data['rolling_std'])
hourly_data['is_anomaly'] = hourly_data['ticket_count'] > hourly_data['upper_bound']

fig_timeline = go.Figure()

# Normal ticket volume
fig_timeline.add_trace(go.Scatter(
    x=hourly_data['created_at'], 
    y=hourly_data['ticket_count'],
    mode='lines',
    name='Hourly Tickets',
    line=dict(color='#2b83ba', width=1.5)
))

# 24-hr threshold boundary
fig_timeline.add_trace(go.Scatter(
    x=hourly_data['created_at'], 
    y=hourly_data['upper_bound'],
    mode='lines',
    name='Dynamic Threshold (μ + 2.5σ)',
    line=dict(color='orange', dash='dot')
))

# Flagged Outage Points
anomalies = hourly_data[hourly_data['is_anomaly']]
fig_timeline.add_trace(go.Scatter(
    x=anomalies['created_at'], 
    y=anomalies['ticket_count'],
    mode='markers',
    name='Flagged Outage Spike',
    marker=dict(color='red', size=8, symbol='circle')
))

fig_timeline.update_layout(
    xaxis_title="Timeline",
    yaxis_title="Tickets Submitted Per Hour",
    height=400,
    margin=dict(l=20, r=20, t=30, b=20)
)
st.plotly_chart(fig_timeline, use_container_width=True)

# --- 15% RESOLUTION TIME OPTIMIZATION SIMULATION ---
st.markdown("---")
st.subheader("⚙️ What-If Analysis: Support Automation Impact")

col_left, col_right = st.columns([1, 2])

with col_left:
    st.write("**Simulate Self-Service Automation:**")
    reduction_pct = st.slider(
        "Automated Ticket Resolution Target (%)",
        min_value=5, max_value=30, value=15, step=1
    )
    
    projected_resolution = avg_resolution * (1 - (reduction_pct / 100))
    hours_saved = (avg_resolution - projected_resolution) * total_tickets

    st.info(f"Targeting a **{reduction_pct}% reduction** via self-service password/MFA resets cuts average resolution time to **{projected_resolution:.1f} hrs**.")
    st.success(f"Estimated Engineering Hours Saved: **{hours_saved:,.0f} hrs**")

with col_right:
    # Team Efficiency Comparison Bar Chart
    team_perf = filtered_df.groupby('assigned_team')['resolution_hours'].mean().reset_index()
    team_perf['Projected_Optimized'] = team_perf['resolution_hours'] * (1 - (reduction_pct / 100))
    
    fig_bar = px.bar(
        team_perf,
        x='assigned_team',
        y=['resolution_hours', 'Projected_Optimized'],
        barmode='group',
        labels={'value': 'Hours', 'assigned_team': 'Team', 'variable': 'Metric'},
        title="Current vs. Projected Resolution Time per Team"
    )
    st.plotly_chart(fig_bar, use_container_width=True)