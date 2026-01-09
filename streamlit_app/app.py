import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from scipy.optimize import curve_fit

# 1. CONFIG PAGE
st.set_page_config(
    page_title="Zombie Protocol Analytics",
    layout="wide",
    page_icon="🧟"
)

# Custom CSS
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    div[data-testid="metric-container"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 10px;
        border-radius: 8px;
        color: #FFFFFF;
    }
</style>
""", unsafe_allow_html=True)

# 2. LOAD DATA (FIXED VERSION)
@st.cache_data
def load_data():
    base_paths = ["data", "../data", "./"]
    data_dir = None
    for p in base_paths:
        if os.path.exists(os.path.join(p, "user_events_flat.csv")):
            data_dir = p
            break
    
    if data_dir is None: return None, None

    try:
        df_e = pd.read_csv(os.path.join(data_dir, "user_events_flat.csv"))
        df_u = pd.read_csv(os.path.join(data_dir, "user_acquisition.csv"))

        # --- FIX DATE PARSING ---
        # 1. Event Date: Convert từ chuỗi số "20251101" sang datetime
        df_e['event_date'] = pd.to_datetime(
            df_e['event_date'].astype(str), 
            format='%Y%m%d', 
            errors='coerce'
        ).dt.normalize()
        
        # 2. Install Date: Convert và normalize về 00:00:00
        df_u['install_date'] = pd.to_datetime(
            df_u['install_date'], 
            errors='coerce'
        ).dt.normalize()
        
        return df_e, df_u
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None

df_events, df_ua = load_data()

if df_events is None:
    st.error("Data not found! Run `python data_generator/generate_data.py`")
    st.stop()

# 3. FILTER PANEL
st.sidebar.title("🧟 Filter Panel")
countries = st.sidebar.multiselect("Country", df_events['country'].unique(), default=df_events['country'].unique())
df_filtered = df_events[df_events['country'].isin(countries)]
valid_users = df_filtered['user_id'].unique()
df_ua_filtered = df_ua[df_ua['user_id'].isin(valid_users)]

# 4. HEADER METRICS
st.title("🧟 Zombie Protocol: Game Performance")
st.markdown(f"**Data Period:** Nov 2025 | **Active Users:** {df_filtered['user_id'].nunique():,}")

col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("Total Installs", f"{df_ua_filtered['user_id'].nunique():,}")
with col2: st.metric("Total Revenue", f"${df_filtered['price'].sum():,.0f}")
with col3: 
    dau = df_filtered.groupby('event_date')['user_id'].nunique().mean()
    st.metric("Avg DAU", f"{int(dau):,}")
with col4:
    st.metric("Retention Model", "Weekly Cohort")

st.markdown("---")

# 5. TABS
tab1, tab2, tab3, tab4 = st.tabs(["📅 Weekly Retention", "🎮 Gameplay Difficulty", "💰 Monetization", "🚀 UA & ROAS"])

# === TAB 1: WEEKLY RETENTION COHORT ===
with tab
