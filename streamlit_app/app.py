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

        # --- FIX BUG QUAN TRỌNG: DATE PARSING ---
        # Cột event_date trong CSV là số (ví dụ: 20251101).
        # Nếu không ép về string (.astype(str)), Pandas sẽ hiểu là mili-giây từ năm 1970 -> Sai ngày.
        
        # 1. Convert Event Date (Format: YYYYMMDD -> YYYY-MM-DD)
        df_e['event_date'] = pd.to_datetime(
            df_e['event_date'].astype(str), 
            format='%Y%m%d', 
            errors='coerce'
        ).dt.normalize()
        
        # 2. Convert Install Date (Format: YYYY-MM-DD -> YYYY-MM-DD)
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
    st.metric("Retention Model", "Power Law Fit")

st.markdown("---")

# 5. TABS
tab1, tab2, tab3, tab4 = st.tabs(["📅 Retention & Forecast", "🎮 Gameplay Difficulty", "💰 Monetization", "🚀 UA & ROAS"])

# === TAB 1: RETENTION & FORECAST ===
with tab1:
    # --- A. COHORT HEATMAP ---
    st.subheader("1. Historical Retention (Cohort)")
    
    # Merge dữ liệu
    cohort_data = df_filtered[['user_id', 'event_date']].merge(
        df_ua_filtered[['user_id', 'install_date']], on='user_id', how='inner'
    )
    
    # Tính khoảng cách ngày
    cohort_data['days_since_install'] = (cohort_data['event_date'] - cohort_data['install_date']).dt.days
    
    # Lọc bỏ ngày âm (đề phòng sai lệch nhỏ về giờ giấc)
    cohort_data = cohort_data[cohort_data['days_since_install'] >= 0]
    
    # Group & Pivot
    cohort_group = cohort_data.groupby(['install_date', 'days_since_install'])['user_id'].nunique().reset_index()
    cohort_pivot = cohort_group.pivot(index='install_date', columns='days_since_install', values='user_id')
    
    # --- KIỂM TRA DAY 0 ĐỂ TRÁNH KEYERROR ---
    if 0 in cohort_pivot.columns:
        cohort_size = cohort_pivot[0]
        retention_matrix = cohort_pivot.divide(cohort_size, axis=0)
        
        key_days = [0, 1, 3, 7, 14, 30]
        existing_days = [d for d in key_days if d in retention_matrix.columns]
        
        # Format index
        retention_matrix.index = retention_matrix.index.strftime('%Y-%m-%d')
        
        # Vẽ Heatmap
        if not retention_matrix.empty:
            fig_ret = px.imshow(
                retention_matrix[existing_days],
                labels=dict(x="Day", y="Cohort Date", color="Retention"),
                x=[f"D{d}" for d in existing_days],
                y=retention_matrix.index,
                text_auto='.1%', color_continuous_scale='RdYlGn', aspect="auto"
            )
            st.plotly_chart(fig_ret, use_container_width=True)
    else:
        st.warning("⚠️ Không tìm thấy dữ liệu Day 0. Đang kiểm tra dữ liệu...")
        st.write("Preview dữ liệu sai lệch (nếu có):")
        st.write(cohort_data.head())

    # --- B. FORECASTING CHART (POWER LAW) ---
    st.markdown("---")
    st.subheader("2. 🔮 Retention Forecasting (Power Law Model)")
    
    with st.expander("See Forecast Details", expanded=True):
        # 1. Chuẩn bị dữ liệu thực tế (Actual Data)
        total_installs_count = df_ua_filtered['user_id'].nunique()
        
        # Tính retention rate trung bình theo ngày (D1, D2...)
        if not cohort_data.empty:
            daily_retention = cohort_data.groupby('days_since_install')['user_id'].nunique() / total_installs_count
            daily_retention = daily_retention.reset_index()
            daily_retention.columns = ['day', 'retention']
            
            # Chỉ lấy ngày > 0 để fit (D0 luôn là 100%)
            actual_data = daily_retention[daily_retention['day'] > 0]

            if len(actual_data) >= 3: # Cần ít nhất 3 điểm dữ liệu
                # 2. Định nghĩa hàm Power Law
                def power_law(t, a, b):
                    return a * np.power(t, b)

                try:
                    # 3. Curve Fitting
                    popt, pcov = curve_fit(power_law, actual_data['day'], actual_data['retention'])
                    a_opt, b_opt = popt
                    
                    # 4. Dự báo tương lai (90 ngày)
                    forecast_days = np.arange(1, 91)
                    forecast_values = power_law(forecast_days, a_opt, b_opt)
                    
                    # 5. Vẽ biểu đồ
                    fig_forecast = go.Figure()

                    # Actual Data
                    fig_forecast.add_trace(go.Scatter(
                        x=actual_data['day'], y=actual_data['retention'],
                        mode='markers', name='Actual Data',
                        marker=dict(color='#00FF99', size=8, line=dict(width=1, color='white'))
                    ))

                    # Forecast Line
                    fig_forecast.add_trace(go.Scatter(
                        x=forecast_days, y=forecast_values,
                        mode='lines', name='Forecast (Power Law)',
                        line=dict(color='#AB63FA', width=3, dash='dash')
                    ))

                    fig_forecast.update_layout(
                        title=f"Retention Forecast (Predicted D30: {power_law(30, a_opt, b_opt):.1%}, D60: {power_law(60, a_opt, b_opt):.1%})",
                        xaxis_title="Days Since Install",
                        yaxis_title="Retention Rate",
                        yaxis_tickformat='.0%',
                        hovermode="x unified",
                        template="plotly_dark"
                    )
                    st.plotly_chart(fig_forecast, use_container_width=True)
                    st.info(f"📐 **Model Equation:** Retention = {a_opt:.3f} * t^({b_opt:.3f})")
                    
                except Exception as e:
                    st.warning(f"Không thể dự báo: Dữ liệu chưa hội tụ. ({e})")
            else:
                st.warning("Cần ít nhất 3 ngày dữ liệu (D1, D2, D3) để chạy mô hình dự báo.")
        else:
            st.info("Chưa có dữ liệu Cohort để dự báo.")

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
