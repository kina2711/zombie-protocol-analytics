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
with tab1:
    st.subheader("1. Weekly Retention Cohort (GA4 Style)")
    
    # --- A. PREPARE DATA ---
    cohort_data = df_filtered[['user_id', 'event_date']].merge(
        df_ua_filtered[['user_id', 'install_date']], on='user_id', how='inner'
    )
    
    # 1. Chuyển đổi ngày sang "Tuần bắt đầu" (Thứ 2 hàng tuần)
    cohort_data['install_week'] = cohort_data['install_date'].dt.to_period('W-MON').dt.start_time
    cohort_data['event_week'] = cohort_data['event_date'].dt.to_period('W-MON').dt.start_time
    
    # 2. Tính khoảng cách tuần
    cohort_data['weeks_since_install'] = (cohort_data['event_week'] - cohort_data['install_week']).dt.days // 7
    cohort_data = cohort_data[cohort_data['weeks_since_install'] >= 0] # Lọc ngày âm
    
    # 3. Group & Pivot
    group = cohort_data.groupby(['install_week', 'weeks_since_install'])['user_id'].nunique().reset_index()
    pivot = group.pivot(index='install_week', columns='weeks_since_install', values='user_id')
    
    # --- B. DISPLAY HEATMAP ---
    if 0 in pivot.columns:
        cohort_sizes = pivot[0]
        retention_matrix = pivot.divide(cohort_sizes, axis=0)
        
        # Tạo nhãn trục Y (vd: Nov 23 - Nov 29)
        y_labels = []
        for start_date in retention_matrix.index:
            end_date = start_date + pd.Timedelta(days=6)
            label = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"
            y_labels.append(label)
        
        retention_matrix.index = y_labels
        
        # Vẽ Heatmap
        fig_ret = px.imshow(
            retention_matrix,
            labels=dict(x="Weeks Since Install", y="Cohort", color="Retention"),
            x=[f"Week {c}" for c in retention_matrix.columns],
            y=retention_matrix.index,
            text_auto='.1%', 
            color_continuous_scale='Blues', # Màu xanh giống GA4
            aspect="auto"
        )
        fig_ret.update_xaxes(side="top")
        fig_ret.update_layout(margin=dict(l=0, r=0, t=50, b=0), coloraxis_showscale=False)
        st.plotly_chart(fig_ret, use_container_width=True)
        
        # --- C. DRILL DOWN ---
        st.markdown("---")
        col_dd1, col_dd2 = st.columns([1, 2])
        
        with col_dd1:
            st.subheader("2. Cohort Drill-down")
            st.info("Select a cohort week above to see daily drop-off.")
            selected_cohort_label = st.selectbox("Select Cohort:", options=y_labels, index=0)
            
        with col_dd2:
            # Lấy data chi tiết cho tuần đã chọn
            selected_index = y_labels.index(selected_cohort_label)
            selected_week_start = pivot.index[selected_index]
            
            detail_df = cohort_data[cohort_data['install_week'] == selected_week_start].copy()
            detail_df['days_since_install'] = (detail_df['event_date'] - detail_df['install_date']).dt.days
            
            daily_trend = detail_df.groupby('days_since_install')['user_id'].nunique()
            base_size = daily_trend.get(0, 0)
            
            if base_size > 0:
                daily_pct = (daily_trend / base_size * 100).reset_index(name='retention')
                fig_detail = px.line(daily_pct, x='days_since_install', y='retention', markers=True,
                                   title=f"Daily Retention for {selected_cohort_label}",
                                   labels={'days_since_install': 'Day', 'retention': 'Retention (%)'})
                fig_detail.update_traces(line_color='#AB63FA', fill='tozeroy')
                st.plotly_chart(fig_detail, use_container_width=True)
            else:
                st.warning("No data for Day 0.")

    else:
        st.warning("Not enough data to form cohorts.")

    # --- D. FORECASTING (EXPANDER) ---
    with st.expander("🔮 Advanced: Power Law Forecast Model"):
        total_installs = df_ua_filtered['user_id'].nunique()
        # Tính daily retention chung cho toàn server
        daily_global = cohort_data.groupby(
            (cohort_data['event_date'] - cohort_data['install_date']).dt.days
        )['user_id'].nunique() / total_installs
        
        daily_global = daily_global.reset_index()
        daily_global.columns = ['day', 'retention']
        actual_data = daily_global[daily_global['day'] > 0]

        if len(actual_data) >= 3:
            def power_law(t, a, b): return a * np.power(t, b)
            try:
                popt, _ = curve_fit(power_law, actual_data['day'], actual_data['retention'])
                forecast_days = np.arange(1, 91)
                forecast_vals = power_law(forecast_days, *popt)
                
                fig_cast = go.Figure()
                fig_cast.add_trace(go.Scatter(x=actual_data['day'], y=actual_data['retention'], mode='markers', name='Actual'))
                fig_cast.add_trace(go.Scatter(x=forecast_days, y=forecast_vals, mode='lines', name='Forecast', line=dict(dash='dash')))
                fig_cast.update_layout(title="90-Day Retention Forecast", template="plotly_dark", yaxis_tickformat='.0%')
                st.plotly_chart(fig_cast, use_container_width=True)
            except: st.warning("Data not converging for forecast.")

# === TAB 2: GAMEPLAY ===
with tab2:
    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        st.subheader("Level Outcomes")
        lvl_df = df_filtered[df_filtered['event_name'].isin(['level_complete', 'level_fail'])]
        if not lvl_df.empty:
            lvl_stats = lvl_df.groupby(['level_id', 'event_name']).size().reset_index(name='count')
            fig_lvl = px.bar(lvl_stats, x='level_id', y='count', color='event_name', barmode='group',
                           color_discrete_map={'level_complete': '#00CC96', 'level_fail': '#EF553B'})
            st.plotly_chart(fig_lvl, use_container_width=True)
    with col_g2:
        st.subheader("Win Rate Data")
        if not lvl_df.empty:
            pivot = lvl_df.groupby(['level_id', 'event_name']).size().unstack(fill_value=0)
            pivot['Total'] = pivot.get('level_complete', 0) + pivot.get('level_fail', 0)
            pivot['Win Rate'] = (pivot.get('level_complete', 0) / pivot['Total'] * 100).round(1)
            st.dataframe(pivot[['Win Rate']], use_container_width=True)

# === TAB 3: MONETIZATION ===
with tab3:
    col_m1, col_m2 = st.columns(2)
    iap_df = df_filtered[df_filtered['event_name'] == 'iap_purchase']
    with col_m1:
        st.subheader("Revenue Mix")
        if not iap_df.empty:
            fig_pie = px.pie(iap_df, names='product_id', values='price', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
    with col_m2:
        st.subheader("Daily Revenue")
        if not iap_df.empty:
            daily = iap_df.groupby('event_date')['price'].sum().reset_index()
            st.plotly_chart(px.line(daily, x='event_date', y='price', markers=True), use_container_width=True)

# === TAB 4: UA & ROAS ===
with tab4:
    st.subheader("Marketing Efficiency (ROAS)")
    user_ltv = df_filtered[df_filtered['event_name'] == 'iap_purchase'].groupby('user_id')['price'].sum().reset_index(name='ltv')
    ua_roas = df_ua_filtered.merge(user_ltv, on='user_id', how='left').fillna(0)
    
    stats = ua_roas.groupby('source').agg(
        Users=('user_id', 'count'), Cost=('cpi', 'sum'), Rev=('ltv', 'sum')
    ).reset_index()
    stats['ROAS (%)'] = (stats['Rev'] / stats['Cost'] * 100).round(1)
    
    fig_roas = px.bar(stats, x='source', y='ROAS (%)', color='source', text='ROAS (%)')
    fig_roas.add_hline(y=100, line_dash="dot", annotation_text="Break-even")
    st.plotly_chart(fig_roas, use_container_width=True)
