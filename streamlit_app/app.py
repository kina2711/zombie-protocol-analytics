import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# 1. PAGE CONFIG & LIGHT THEME
# ==========================================
st.set_page_config(
    page_title="Zombie Protocol - Analytics Hub",
    page_icon="🧟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Giao diện Nền Sáng (Clean Light Mode)
st.markdown("""
<style>
    /* 1. Main Background - Light Gray */
    .stApp {
        background-color: #F0F2F6;
        color: #31333F;
    }
    
    /* 2. Metric Cards - White with Shadow */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    div[data-testid="stMetricLabel"] {
        color: #6B7280; /* Gray-500 */
        font-size: 14px;
        font-weight: 500;
    }
    div[data-testid="stMetricValue"] {
        color: #111827; /* Gray-900 */
        font-size: 26px;
        font-weight: 700;
    }
    
    /* 3. Headers */
    h1, h2, h3 {
        color: #111827 !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    h3 {
        color: #2563EB !important; /* Blue highlight for subheaders */
    }
    
    /* 4. Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #FFFFFF;
        border-radius: 5px 5px 0 0;
        color: #4B5563;
        border: 1px solid #E5E7EB;
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF;
        color: #2563EB; /* Blue text for selected */
        border-top: 2px solid #2563EB;
    }
    
    /* 5. Sidebar */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E5E7EB;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA PROCESSING ENGINE
# ==========================================
@st.cache_data
def load_and_process_data():
    base_paths = ["data", "../data", "./"]
    data_path = None
    for p in base_paths:
        if os.path.exists(os.path.join(p, "user_acquisition.csv")):
            data_path = p
            break
            
    if not data_path: return None, None, None, None

    # Load Raw Data
    df_ua = pd.read_csv(os.path.join(data_path, "user_acquisition.csv"))
    df_ev = pd.read_csv(os.path.join(data_path, "user_events_flat.csv"))
    df_iap = pd.read_csv(os.path.join(data_path, "iap_transactions.csv"))
    df_ads = pd.read_csv(os.path.join(data_path, "ad_impressions.csv"))

    # Convert Datetime
    df_ua['install_date'] = pd.to_datetime(df_ua['install_date'])
    df_ev['event_date'] = pd.to_datetime(df_ev['event_date'])
    df_iap['timestamp'] = pd.to_datetime(df_iap['timestamp'])
    df_ads['timestamp'] = pd.to_datetime(df_ads['timestamp'])

    # --- Pre-calculate Complex Metrics ---
    iap_rev = df_iap.groupby('user_id')['price'].sum().rename('iap_rev')
    ads_rev = df_ads.groupby('user_id')['revenue'].sum().rename('ads_rev')
    
    df_master = df_ua.set_index('user_id').join([iap_rev, ads_rev]).fillna(0)
    df_master['total_revenue'] = df_master['iap_rev'] + df_master['ads_rev']
    
    return df_ua, df_ev, df_iap, df_ads, df_master

df_ua, df_ev, df_iap, df_ads, df_master = load_and_process_data()

if df_ua is None:
    st.error("⚠️ Data not found. Run generate_data.py first.")
    st.stop()

# ==========================================
# 3. SIDEBAR FILTERS
# ==========================================
st.sidebar.title("🛠️ Filter Panel")

tiers = df_ua['tier'].unique()
selected_tiers = st.sidebar.multiselect("Market Tier", tiers, default=tiers)

df_master_filtered = df_master[df_master['tier'].isin(selected_tiers)]
valid_users = df_master_filtered.index.tolist()

df_ev_filtered = df_ev[df_ev['user_id'].isin(valid_users)]
df_iap_filtered = df_iap[df_iap['user_id'].isin(valid_users)]
df_ads_filtered = df_ads[df_ads['user_id'].isin(valid_users)]

# ==========================================
# 4. DASHBOARD TABS
# ==========================================
st.title("🧟 Zombie Protocol Analytics")
st.caption(f"Reporting Period: {df_ua['install_date'].min().date()} to {df_ua['install_date'].max().date()}")

tab_health, tab_ingame, tab_monetization = st.tabs([
    "📈 Game Health & Engagement", 
    "🎮 In-Game Analysis (Core Loop)", 
    "💰 Monetization & LTV"
])

# ---------------------------------------------------------------------
# TAB 1: GAME HEALTH
# ---------------------------------------------------------------------
with tab_health:
    st.markdown("### 1. Key Performance Indicators (KPIs)")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    
    dau_series = df_ev_filtered.groupby('event_date')['user_id'].nunique()
    avg_dau = int(dau_series.mean())
    total_rev = df_master_filtered['total_revenue'].sum()
    total_users = len(df_master_filtered)
    arpu = total_rev / total_users if total_users > 0 else 0
    avg_session_duration = df_ev_filtered['duration'].mean() / 60
    
    with c1: st.metric("Avg DAU", f"{avg_dau:,}")
    with c2: st.metric("Total Revenue", f"${total_rev:,.0f}")
    with c3: st.metric("ARPU (All Time)", f"${arpu:.2f}")
    with c4: st.metric("Avg Session", f"{avg_session_duration:.1f} min")
    with c5: st.metric("Ads Views/User", f"{(len(df_ads_filtered)/total_users):.1f}")
    
    st.markdown("---")
    
    c_chart1, c_chart2 = st.columns([2, 1])
    
    with c_chart1:
        st.subheader("Daily Active Users (DAU) Trend")
        fig_dau = px.line(dau_series, x=dau_series.index, y=dau_series.values, 
                          markers=True, line_shape='spline', template='plotly_white') # Light Template
        fig_dau.update_traces(line_color='#2563EB', line_width=3)
        fig_dau.update_layout(xaxis_title="Date", yaxis_title="Active Users", height=350)
        st.plotly_chart(fig_dau, use_container_width=True)
        
    with c_chart2:
        st.subheader("User Distribution by Tier")
        tier_counts = df_master_filtered['tier'].value_counts()
        fig_pie = px.pie(values=tier_counts.values, names=tier_counts.index, hole=0.6,
                         color_discrete_sequence=px.colors.sequential.RdBu, template='plotly_white')
        fig_pie.update_layout(height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

# ---------------------------------------------------------------------
# TAB 2: IN-GAME ANALYSIS
# ---------------------------------------------------------------------
with tab_ingame:
    st.markdown("### 2. Player Journey & Core Loop Analysis")
    
    col_funnel, col_stat = st.columns([3, 1])
    
    with col_funnel:
        st.subheader("📍 Level Progression Funnel")
        user_max_level = df_ev_filtered.groupby('user_id')['level_id'].max()
        
        level_range = range(1, 21)
        funnel_data = []
        for lvl in level_range:
            count = user_max_level[user_max_level >= lvl].count()
            funnel_data.append({'level': f"Lvl {lvl}", 'users': count})
            
        df_funnel = pd.DataFrame(funnel_data)
        
        fig_funnel = go.Figure(go.Funnel(
            y=df_funnel['level'],
            x=df_funnel['users'],
            textinfo="value+percent previous",
            marker={"color": "#636EFA"}
        ))
        fig_funnel.update_layout(height=500, title="User Survival Rate by Level", template='plotly_white')
        st.plotly_chart(fig_funnel, use_container_width=True)

    with col_stat:
        st.subheader("☠️ Top Churn Levels")
        churn_levels = user_max_level.value_counts().sort_index().head(10)
        st.dataframe(churn_levels.rename("Churned Users"), height=400)

    st.subheader("⚖️ Difficulty Balance (Win vs. Fail Rate)")
    level_outcomes = df_ev_filtered.groupby(['level_id', 'event_name']).size().unstack(fill_value=0).head(20)
    
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(x=level_outcomes.index, y=level_outcomes['level_complete'], name='Win', marker_color='#10B981'))
    fig_bar.add_trace(go.Bar(x=level_outcomes.index, y=level_outcomes['level_fail'], name='Fail', marker_color='#EF4444'))
    
    fig_bar.update_layout(barmode='stack', title="Win/Fail Ratio per Level", height=400, template='plotly_white')
    st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------------------------
# TAB 3: MONETIZATION & LTV
# ---------------------------------------------------------------------
with tab_monetization:
    st.markdown("### 3. ROI & Economy Analysis")
    
    m1, m2, m3, m4 = st.columns(4)
    
    paying_users = df_master_filtered[df_master_filtered['iap_rev'] > 0]
    arppu = paying_users['iap_rev'].mean()
    avg_cpi = df_master_filtered['cpi'].mean()
    
    with m1: st.metric("Paying Users", f"{len(paying_users)} ({len(paying_users)/len(df_master_filtered):.1%})")
    with m2: st.metric("ARPPU", f"${arppu:.2f}")
    with m3: st.metric("Avg CPI", f"${avg_cpi:.2f}")
    with m4: st.metric("Ads Revenue %", f"{(df_master_filtered['ads_rev'].sum()/total_rev):.1%}")

    st.markdown("---")

    st.subheader("💸 LTV vs. CPI (ROAS Analysis)")
    
    # Calculate Data for LTV
    iap_daily = df_iap_filtered.merge(df_master[['install_date', 'tier']], left_on='user_id', right_index=True)
    iap_daily['day_diff'] = (iap_daily['timestamp'] - iap_daily['install_date']).dt.days
    
    ads_daily = df_ads_filtered.merge(df_master[['install_date', 'tier']], left_on='user_id', right_index=True)
    ads_daily['day_diff'] = (ads_daily['timestamp'] - ads_daily['install_date']).dt.days
    
    iap_agg = iap_daily.groupby(['tier', 'day_diff'])['price'].sum().reset_index().rename(columns={'price': 'rev'})
    ads_agg = ads_daily.groupby(['tier', 'day_diff'])['revenue'].sum().reset_index().rename(columns={'revenue': 'rev'})
    total_rev_daily = pd.concat([iap_agg, ads_agg]).groupby(['tier', 'day_diff'])['rev'].sum().reset_index()
    
    fig_ltv = go.Figure()
    colors = {'Tier 1': '#EF4444', 'Tier 2': '#F59E0B', 'Tier 3': '#10B981'} # Red, Amber, Green
    
    for tier in selected_tiers:
        tier_data = total_rev_daily[total_rev_daily['tier'] == tier].sort_values('day_diff')
        n_users = len(df_master[df_master['tier'] == tier])
        
        if n_users > 0:
            max_day = 30
            days_range = pd.DataFrame({'day_diff': range(max_day + 1)})
            tier_data = days_range.merge(tier_data, on='day_diff', how='left').fillna(0)
            
            tier_data['cumulative_rev'] = tier_data['rev'].cumsum()
            tier_data['ltv'] = tier_data['cumulative_rev'] / n_users
            tier_cpi = df_master[df_master['tier'] == tier]['cpi'].mean()
            
            fig_ltv.add_trace(go.Scatter(
                x=tier_data['day_diff'], y=tier_data['ltv'],
                mode='lines+markers', name=f'LTV - {tier}',
                line=dict(color=colors.get(tier, 'gray'), width=3)
            ))
            
            fig_ltv.add_trace(go.Scatter(
                x=[0, max_day], y=[tier_cpi, tier_cpi],
                mode='lines', name=f'CPI - {tier}',
                line=dict(color=colors.get(tier, 'gray'), dash='dot', width=1),
                showlegend=False
            ))

    fig_ltv.update_layout(
        title="Cumulative LTV vs. CPI (Day 0 to Day 30)",
        xaxis_title="Days Since Install",
        yaxis_title="USD ($)",
        hovermode="x unified",
        height=500,
        template='plotly_white' # Light Template
    )
    st.plotly_chart(fig_ltv, use_container_width=True)

    c_pack, c_ads = st.columns(2)
    with c_pack:
        st.subheader("📦 Revenue by Pack")
        pack_rev = df_iap_filtered.groupby('pack')['price'].sum().sort_values(ascending=False)
        fig_pack = px.bar(pack_rev, x=pack_rev.values, y=pack_rev.index, orientation='h', 
                          color=pack_rev.values, color_continuous_scale='Blues', template='plotly_white')
        st.plotly_chart(fig_pack, use_container_width=True)
        
    with c_ads:
        st.subheader("📺 Ads Performance")
        ads_place = df_ads_filtered.groupby('placement')['revenue'].sum()
        fig_ads = px.pie(values=ads_place.values, names=ads_place.index, hole=0.4, 
                         title="Ads Revenue Share", template='plotly_white')
        st.plotly_chart(fig_ads, use_container_width=True)
