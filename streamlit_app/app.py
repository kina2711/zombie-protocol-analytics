import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.optimize import curve_fit
import os

# ==========================================
# 1. CONFIG & SETUP
# ==========================================
st.set_page_config(
    page_title="Zombie Protocol - Analytics Dashboard",
    page_icon="🧟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện Dark Gaming Theme
st.markdown("""
<style>
    .main {
        background-color: #0E1117;
    }
    h1, h2, h3 {
        color: #00FF99 !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #FFFFFF;
    }
    div[data-testid="stMetricLabel"] {
        color: #AAAAAA;
    }
    .insight-box {
        background-color: #262730;
        border-left: 5px solid #FF4B4B;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. LOAD DATA
# ==========================================
@st.cache_data
def load_data():
    # Đường dẫn tương đối đến thư mục data (Sửa lại nếu cấu trúc folder của bạn khác)
    # Giả định: app.py nằm trong folder con, nên cần lùi ra 1 cấp (../data)
    # Hoặc nếu chạy từ root thì là ./data. Code này sẽ thử cả 2.
    possible_paths = ["data", "../data", "./"]

    data_path = None
    for p in possible_paths:
        if os.path.exists(os.path.join(p, "user_acquisition.csv")):
            data_path = p
            break

    if not data_path:
        return None, None, None, None

    try:
        df_ua = pd.read_csv(os.path.join(data_path, "user_acquisition.csv"))
        df_ev = pd.read_csv(os.path.join(data_path, "user_events_flat.csv"))
        df_iap = pd.read_csv(os.path.join(data_path, "iap_transactions.csv"))
        df_ads = pd.read_csv(os.path.join(data_path, "ad_impressions.csv"))

        # Convert Date & Time
        df_ua['install_date'] = pd.to_datetime(df_ua['install_date'])
        df_ev['event_date'] = pd.to_datetime(df_ev['event_date'])

        # Xử lý tên cột cho đồng bộ (nếu cần)
        # Ví dụ: đổi 'timestamp' thành datetime nếu cần phân tích theo giờ

        return df_ua, df_ev, df_iap, df_ads
    except Exception as e:
        st.error(f"Lỗi đọc file: {e}")
        return None, None, None, None


df_ua, df_ev, df_iap, df_ads = load_data()

if df_ua is None:
    st.error("⚠️ Không tìm thấy thư mục 'data' hoặc file CSV bị thiếu. Vui lòng kiểm tra lại cấu trúc thư mục.")
    st.stop()

# ==========================================
# 3. SIDEBAR FILTERS
# ==========================================
st.sidebar.title("🎮 Filters")
st.sidebar.caption("Lọc dữ liệu toàn trang")

# Filter by Marketing Source
sources = df_ua['source'].unique()
selected_sources = st.sidebar.multiselect("Nguồn User (Source)", sources, default=sources)

# Filter by Tier (Nếu có cột tier)
if 'tier' in df_ua.columns:
    tiers = df_ua['tier'].unique()
    selected_tiers = st.sidebar.multiselect("Thị trường (Tier)", tiers, default=tiers)
else:
    selected_tiers = []

# Apply Filter
if selected_sources:
    df_ua_filtered = df_ua[df_ua['source'].isin(selected_sources)]
else:
    df_ua_filtered = df_ua

if selected_tiers and 'tier' in df_ua.columns:
    df_ua_filtered = df_ua_filtered[df_ua_filtered['tier'].isin(selected_tiers)]

valid_users = df_ua_filtered['user_id'].unique()
df_ev_filtered = df_ev[df_ev['user_id'].isin(valid_users)]
df_iap_filtered = df_iap[df_iap['user_id'].isin(valid_users)]
df_ads_filtered = df_ads[df_ads['user_id'].isin(valid_users)]

# ==========================================
# 4. EXECUTIVE SUMMARY (KPIs)
# ==========================================
st.title("🧟 Zombie Protocol - Game Health Monitor")
st.markdown(f"**Data Period:** {df_ua['install_date'].min().date()} to {df_ua['install_date'].max().date()}")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

total_users = df_ua_filtered['user_id'].nunique()
iap_rev = df_iap_filtered['price'].sum()
ads_rev = df_ads_filtered['revenue'].sum()
total_rev = iap_rev + ads_rev
marketing_cost = df_ua_filtered['cpi'].sum()

# Tính ROAS (Return on Ad Spend)
roas = (total_rev / marketing_cost * 100) if marketing_cost > 0 else 0

with kpi1: st.metric("Active Users", f"{total_users:,}")
with kpi2: st.metric("Total Revenue", f"${total_rev:,.0f}", delta=f"Ads: ${ads_rev:,.0f}")
with kpi3: st.metric("Marketing Cost", f"${marketing_cost:,.0f}")
with kpi4:
    color = "normal" if roas >= 100 else "inverse"
    st.metric("ROAS", f"{roas:.1f}%", delta_color=color)

st.markdown("---")

# ==========================================
# 5. MAIN TABS
# ==========================================
tab_gameplay, tab_money, tab_retention = st.tabs([
    "💀 Gameplay & Difficulty (Diagnostic)",
    "💰 Monetization (Descriptive)",
    "🔮 Retention (Predictive)"
])

# ---------------------------------------------------------
# TAB 1: GAMEPLAY & DIFFICULTY (DIAGNOSTIC ANALYTICS)
# ---------------------------------------------------------
with tab_gameplay:
    st.subheader("Phân tích điểm gãy (Churn Points)")

    col_g1, col_g2 = st.columns([3, 1])

    with col_g1:
        # Tính tỷ lệ Win/Fail theo Level
        level_stats = df_ev_filtered.groupby(['level_id', 'event_name']).size().reset_index(name='count')

        # Chart Stacked Bar
        fig_funnel = px.bar(
            level_stats,
            x='level_id',
            y='count',
            color='event_name',
            title="Tỷ lệ Thắng/Thua theo Level (Level Funnel)",
            color_discrete_map={'level_complete': '#00CC96', 'level_fail': '#EF553B'},
            barmode='stack'
        )

        # Highlight Level 8 (nếu có dữ liệu level 8)
        if 8 in level_stats['level_id'].values:
            fig_funnel.add_annotation(
                x=8, y=level_stats[level_stats['level_id'] == 8]['count'].max(),
                text="Potential Churn Point",
                showarrow=True, arrowhead=1, yshift=10
            )

        st.plotly_chart(fig_funnel, use_container_width=True)

    with col_g2:
        st.markdown("""
        <div class='insight-box'>
        <b>🕵️ Data Analyst Insight:</b><br>
        Hãy chú ý vào <b>Level 8</b>.
        <br><br>
        Nếu cột màu đỏ (Fail) chiếm tỷ trọng lớn (>70%), đây là dấu hiệu của việc <b>Độ khó tăng đột ngột (Difficulty Spike)</b>.
        <br><br>
        User thường bỏ game (Churn) tại đây vì hết tài nguyên hoặc cảm thấy ức chế.
        </div>
        """, unsafe_allow_html=True)

        # Top Levels khó nhất
        fail_counts = df_ev_filtered[df_ev_filtered['event_name'] == 'level_fail'].groupby('level_id').size()
        total_counts = df_ev_filtered.groupby('level_id').size()
        fail_rates = (fail_counts / total_counts * 100).sort_values(ascending=False).head(5)

        st.write("**Top 5 Level Khó Nhất (% Fail):**")
        st.dataframe(fail_rates.rename("Fail Rate (%)").map("{:.1f}%".format))

# ---------------------------------------------------------
# TAB 2: MONETIZATION (DESCRIPTIVE ANALYTICS)
# ---------------------------------------------------------
with tab_money:
    st.subheader("Nguồn doanh thu đến từ đâu?")

    m1, m2 = st.columns(2)

    with m1:
        # IAP Breakdown
        iap_by_pack = df_iap_filtered.groupby('pack')['price'].sum().reset_index()
        fig_iap = px.pie(iap_by_pack, values='price', names='pack', title='IAP Revenue by Pack Type', hole=0.4)
        st.plotly_chart(fig_iap, use_container_width=True)

    with m2:
        # Ads Breakdown
        ads_by_place = df_ads_filtered.groupby('placement')['revenue'].sum().reset_index()
        fig_ads = px.bar(ads_by_place, x='placement', y='revenue', title='Ads Revenue by Placement', text_auto='.2s')
        fig_ads.update_traces(marker_color='#00AAFF')
        st.plotly_chart(fig_ads, use_container_width=True)

    st.info(
        "💡 **Gợi ý:** Nếu 'Revive' Ads (Hồi sinh) có doanh thu cao, chứng tỏ User chấp nhận xem quảng cáo để qua màn khó. Có thể tận dụng điều này ở Level 8.")

# ---------------------------------------------------------
# TAB 3: RETENTION & FORECAST (PREDICTIVE ANALYTICS)
# ---------------------------------------------------------
with tab_retention:
    st.subheader("Dự báo khả năng giữ chân người dùng (Retention Forecasting)")

    # 1. Tính Retention Curve thực tế
    # Merge Event với Install Date
    cohort_data = df_ev_filtered[['user_id', 'event_date']].merge(
        df_ua_filtered[['user_id', 'install_date']], on='user_id'
    )
    # Tính số ngày từ lúc install
    cohort_data['days_since_install'] = (cohort_data['event_date'] - cohort_data['install_date']).dt.days

    # Loại bỏ giá trị âm (nếu có lỗi data) và chỉ lấy trong khoảng hợp lý
    cohort_data = cohort_data[cohort_data['days_since_install'] >= 0]

    # Đếm số user active mỗi ngày (D0, D1, D2...)
    daily_active = cohort_data.groupby('days_since_install')['user_id'].nunique()
    total_cohort = df_ua_filtered['user_id'].nunique()

    retention_rate = (daily_active / total_cohort).reset_index(name='rate')
    # Bỏ D0 vì thường là 100% hoặc gần đó, gây nhiễu fit model
    retention_model_data = retention_rate[retention_rate['days_since_install'] > 0]

    col_r1, col_r2 = st.columns([2, 1])

    with col_r1:
        # 2. Predictive Model: Power Law (y = a * x^b)
        def power_law(x, a, b):
            return a * np.power(x, b)


        # Fit model
        if len(retention_model_data) > 5:
            try:
                popt, pcov = curve_fit(power_law, retention_model_data['days_since_install'],
                                       retention_model_data['rate'])

                # Dự báo cho 60 ngày
                x_pred = np.arange(1, 61)
                y_pred = power_law(x_pred, *popt)

                # Vẽ biểu đồ
                fig_ret = go.Figure()

                # Data thực tế
                fig_ret.add_trace(go.Scatter(
                    x=retention_model_data['days_since_install'],
                    y=retention_model_data['rate'],
                    mode='markers',
                    name='Actual Data',
                    marker=dict(color='#00FF99', size=8)
                ))

                # Đường dự báo
                fig_ret.add_trace(go.Scatter(
                    x=x_pred,
                    y=y_pred,
                    mode='lines',
                    name='Prediction (Power Law)',
                    line=dict(color='#FF4B4B', dash='dash')
                ))

                fig_ret.update_layout(
                    title="Retention Decay Curve & Prediction",
                    xaxis_title="Days Since Install",
                    yaxis_title="Retention Rate",
                    yaxis_tickformat='.0%',
                    legend=dict(x=0.7, y=1)
                )

                st.plotly_chart(fig_ret, use_container_width=True)

                d30_pred = power_law(30, *popt)
                st.success(
                    f"🔮 **Dự báo máy học:** Dựa trên xu hướng hiện tại, Retention D30 ước tính đạt **{d30_pred:.1%}**.")

            except Exception as e:
                st.warning(f"Không thể chạy mô hình dự báo do dữ liệu chưa đủ hội tụ. Lỗi: {e}")
                # Fallback: Chỉ vẽ line chart thường
                st.line_chart(retention_model_data.set_index('days_since_install')['rate'])
        else:
            st.warning("Chưa đủ dữ liệu (>5 ngày) để chạy mô hình dự báo.")

    with col_r2:
        st.write("#### Retention Table")
        st.dataframe(retention_rate.set_index('days_since_install').style.format("{:.1%}"))

        st.markdown("""
        > **Note:** Mô hình Power Law thường được dùng trong Game Analytics để dự đoán hành vi người chơi dài hạn dựa trên dữ liệu ngắn hạn (D1-D7).
        """)

# ==========================================
# FOOTER
# ==========================================
st.markdown("---")
st.markdown("Zombie Protocol Analytics • Powered by **Streamlit** & **Python**")
