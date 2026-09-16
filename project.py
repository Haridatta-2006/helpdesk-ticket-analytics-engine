import pandas as pd
import numpy as np
import uuid
import sqlite3
from datetime import datetime, timedelta
import random

print("--- STEP 1: Generating 50,000 Support Tickets ---")
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
        "created_at": created,
        "resolved_at": resolved,
        "category": random.choice(categories),
        "priority": priority,
        "assigned_team": random.choice(teams),
        "error_code": err,
        "reopen_count": random.choices([0, 1, 2], weights=[0.85, 0.10, 0.05])[0]
    })

# Inject outage spike: 500 network error tickets in a 2-hour window
outage_start = start_time + timedelta(days=15, hours=10)
for _ in range(500):
    data.append({
        "ticket_id": f"TCK-{uuid.uuid4().hex[:8].upper()}",
        "created_at": outage_start + timedelta(minutes=random.randint(0, 120)),
        "resolved_at": outage_start + timedelta(hours=random.uniform(1.5, 4.0)),
        "category": "Network/VPN",
        "priority": "P1-Critical",
        "assigned_team": "NetOps",
        "error_code": "ERR_502",
        "reopen_count": 0
    })

df = pd.DataFrame(data)

print("--- STEP 2: Processing Metrics & SLA Targets ---")
df['resolution_hours'] = ((df['resolved_at'] - df['created_at']).dt.total_seconds() / 3600.0).round(2)
df['sla_target_hours'] = df['priority'].map(sla_targets)
df['is_sla_breached'] = df['resolution_hours'] > df['sla_target_hours']

print("--- STEP 3: Saving to SQLite Database (helpdesk_warehouse.db) ---")
conn = sqlite3.connect("helpdesk_warehouse.db")
df['created_at'] = df['created_at'].astype(str)
df['resolved_at'] = df['resolved_at'].astype(str)
df.to_sql('fact_tickets', conn, if_exists='replace', index=False)
conn.close()

print("Pipeline completed successfully! 'helpdesk_warehouse.db' is ready.")