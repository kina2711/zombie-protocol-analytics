import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# 1. CONFIG PAGE
st.set_page_config(
    page_title="Zombie Protocol Analytics",
    layout="wide"
)

# 2. LOAD DATA
@st.cache_data
def load_data():
    # Kiểm tra xem file có tồn tại không
    data_path = "data/user_events_flat.csv" 
    ua_path = "data/user_acquisition.csv"
    
    if not os.path.exists(data_path):
        st.error("Chưa tìm thấy file data! Hãy chạy script 'generate_data.py' trước.")
        return None, None
        
    df_events = pd.read_csv(data_path)
    df_ua = pd.read_csv(ua_path)
    return df_events, df_ua

df_events, df_ua = load_data()

if df_events is not None:
    # 3. HEADER METRICS
    st.title("Zombie Protocol - Game Health Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    total_users = df_ua['user_id'].nunique()
    total_sessions = df_events['session_id'].nunique()
    avg_level = df_events.groupby('user_id')['level_id'].max().mean()
    
    col1.metric("Total Users", f"{total_users:,}")
    col2.metric("Total Sessions", f"{total_sessions:,}")
    col3.metric("Avg Max Level", f"{avg_level:.1f}")
    
    st.divider()

    # 4. DEEP DIVE: LEVEL DIFFICULTY (Điểm nhấn của Project)
    st.subheader("1. Phân tích Phễu & Độ khó (Level Funnel & Difficulty)")
    
    # Chuẩn bị data cho Funnel
    level_stats = df_events.groupby('level_id').agg(
        Players=('user_id', 'nunique'),
        Failures=('event_name', lambda x: (x == 'level_fail').sum()),
        Attempts=('event_name', 'count')
    ).reset_index()
    
    level_stats['Win Rate'] = (1 - (level_stats['Failures'] / level_stats['Attempts'])) * 100
    level_stats['Churn Rate'] = level_stats['Players'].pct_change() * 100 # Tương đối
    
    # Biểu đồ Combo: Số người chơi vs Win Rate
    fig_funnel = go.Figure()
    
    # Cột: Số người chơi còn lại ở mỗi level
    fig_funnel.add_trace(go.Bar(
        x=level_stats['level_id'],
        y=level_stats['Players'],
        name='Active Players',
        marker_color='#1f77b4'
    ))
    
    # Đường: Tỷ lệ thắng (Win Rate)
    fig_funnel.add_trace(go.Scatter(
        x=level_stats['level_id'],
        y=level_stats['Win Rate'],
        name='Win Rate (%)',
        yaxis='y2',
        line=dict(color='red', width=3)
    ))
    
    fig_funnel.update_layout(
        title="Level Drop-off & Difficulty Analysis (Chú ý Level 8)",
        xaxis_title="Level ID",
        yaxis=dict(title="Number of Players"),
        yaxis2=dict(title="Win Rate (%)", overlaying='y', side='right', range=[0, 100]),
        legend=dict(x=0.7, y=1.0)
    )
    
    st.plotly_chart(fig_funnel, use_container_width=True)
    
    # Insight box
    st.info("""
    **Data Analyst Insight:** Hãy nhìn vào Level 8. Nếu logic 'Difficulty Spike' hoạt động đúng, bạn sẽ thấy đường màu đỏ (Win Rate) tụt dốc và cột màu xanh (Players) ở Level 9 giảm mạnh do user bỏ game.
    """)

    # 5. USER ACQUISITION
    st.subheader("2. Hiệu quả User Acquisition (UA)")
    
    col_ua1, col_ua2 = st.columns(2)
    
    with col_ua1:
        # Pie chart: Nguồn user
        fig_source = px.pie(df_ua, names='source', title='User Distribution by Source')
        st.plotly_chart(fig_source, use_container_width=True)
        
    with col_ua2:
        # Bar chart: Chi phí trung bình (CPI) theo Tier
        avg_cpi = df_ua.groupby('tier')['cpi'].mean().reset_index()
        fig_cpi = px.bar(avg_cpi, x='tier', y='cpi', title='Avg CPI by Tier', color='tier')
        st.plotly_chart(fig_cpi, use_container_width=True)

    # 6. MONETIZATION OVERVIEW
    st.subheader("3. Sơ bộ Monetization")
    iap_path = "data/iap_transactions.csv"
    if os.path.exists(iap_path):
        df_iap = pd.read_csv(iap_path)
        total_rev = df_iap['price'].sum()
        paying_users = df_iap['user_id'].nunique()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Revenue (IAP)", f"${total_rev:,.2f}")
        m2.metric("Paying Users", f"{paying_users}")
        m3.metric("ARPPU", f"${total_rev/paying_users:.2f}")
