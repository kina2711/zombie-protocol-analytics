import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. CONFIGURATION & LIGHT THEME STYLING
st.set_page_config(
    page_title="Zombie Protocol Analytics",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Light Professional UI
# Style: Clean, White/Gray Background, High Contrast Text
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #F9FAFB; /* Light Gray Background */
        color: #111827; /* Dark Text */
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E5E7EB;
    }

    /* Metric Cards Styling (Light Mode) */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px;
        color: #6B7280; /* Gray 500 */
        font-weight: 600;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #111827; /* Gray 900 */
        font-weight: 700;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: #FFFFFF;
        padding: 10px 10px 0 10px;
        border-radius: 8px 8px 0 0;
        border-bottom: 1px solid #E5E7EB;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        font-weight: 600;
        color: #6B7280;
    }
    .stTabs [aria-selected="true"] {
        color: #2563EB; /* Blue 600 */
        border-bottom: 3px solid #2563EB;
    }

    /* Headings */
    h1, h2, h3 {
        color: #111827;
        font-family: 'Inter', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# 2. DATA PIPELINE & LOGIC
@st.cache_data
def load_dataset():
    """Load and preprocess raw game data."""
    try:
        df = pd.read_csv('data/game_data.csv')
        df['date'] = pd.to_datetime(df['date'])
        return df
    except FileNotFoundError:
        return None


def compute_wallet_metrics(df):
    """Compute daily cumulative gold balance."""
    daily_flow = df.groupby('date')['gold_change'].sum().reset_index()
    daily_flow['cumulative_gold'] = daily_flow['gold_change'].cumsum()
    daily_dau = df.groupby('date')['user_id'].nunique().reset_index(name='active_users')
    merged_df = pd.merge(daily_flow, daily_dau, on='date')
    merged_df['avg_balance'] = merged_df['cumulative_gold'] / merged_df['active_users']
    return merged_df


def calculate_cohort_retention(df):
    """
    Tính toán Cohort Retention Matrix từ Raw Data.
    Logic:
    1. Tìm Install Date (Min Date) cho mỗi User.
    2. Tính khoảng cách ngày (Day Diff) giữa Activity Date và Install Date.
    3. Pivot table để ra ma trận Retention %.
    """
    # 1. Xác định Install Date cho mỗi user
    user_install = df.groupby('user_id')['date'].min().rename('install_date')
    df_cohort = df.merge(user_install, on='user_id')

    # 2. Tính số ngày kể từ khi Install (Day Index)
    df_cohort['day_diff'] = (df_cohort['date'] - df_cohort['install_date']).dt.days

    # 3. Gom nhóm theo Cohort (Ngày cài) và Day Index
    cohort_data = df_cohort.groupby(['install_date', 'day_diff'])['user_id'].nunique().reset_index()

    # 4. Tính Cohort Size (Số lượng user ngày đầu tiên - Day 0)
    cohort_sizes = cohort_data[cohort_data['day_diff'] == 0][['install_date', 'user_id']]
    cohort_sizes.rename(columns={'user_id': 'cohort_size'}, inplace=True)

    # Merge lại để tính %
    cohort_data = cohort_data.merge(cohort_sizes, on='install_date')
    cohort_data['retention_rate'] = (cohort_data['user_id'] / cohort_data['cohort_size']) * 100

    # Chỉ lấy các ngày quan trọng (D0, D1, D3, D7, D14, D30) để hiển thị cho gọn
    target_days = [0, 1, 3, 7, 14, 30]
    cohort_data = cohort_data[cohort_data['day_diff'].isin(target_days)]

    # 5. Pivot Table cho Heatmap
    retention_matrix = cohort_data.pivot(index='install_date', columns='day_diff', values='retention_rate')

    # Format index ngày tháng cho đẹp
    retention_matrix.index = retention_matrix.index.strftime('%Y-%m-%d')

    return retention_matrix, cohort_sizes


# Load Data
df_raw = load_dataset()

# 3. SIDEBAR: FILTERS
st.sidebar.title("Control Panel")

if df_raw is not None:
    min_date = df_raw['date'].min()
    max_date = df_raw['date'].max()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Filter Logic
    mask = (df_raw['date'].dt.date >= date_range[0]) & (df_raw['date'].dt.date <= date_range[1])
    df_filtered = df_raw.loc[mask]

    st.sidebar.markdown("---")
    st.sidebar.info(f"**Data Loaded:** {len(df_filtered):,} events")
else:
    df_filtered = None

# 4. MAIN DASHBOARD

if df_filtered is not None and not df_filtered.empty:
    st.title("ZOMBIE PROTOCOL: ANALYTICS HUB")
    st.markdown("Monitor KPI performance, economy health, and user retention.")
    st.markdown("---")

    # KPI CARDS
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    total_rev = df_filtered['revenue'].sum()
    unique_users = df_filtered['user_id'].nunique()
    avg_dau = df_filtered.groupby('date')['user_id'].nunique().mean()
    arpu = total_rev / unique_users if unique_users > 0 else 0

    kpi1.metric("Avg DAU", f"{int(avg_dau):,}")
    kpi2.metric("Total Users", f"{unique_users:,}")
    kpi3.metric("Revenue", f"${total_rev:,.0f}")
    kpi4.metric("ARPU", f"${arpu:.2f}")

    st.markdown("###")

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs([
        "Overview",
        "Retention & Cohorts",
        "Economy",
        "Level Funnel"
    ])

    # TAB 1: OVERVIEW
    with tab1:
        st.subheader("Traffic & Revenue Trend")
        daily_kpi = df_filtered.groupby('date').agg({'user_id': 'nunique', 'revenue': 'sum'}).reset_index()

        fig_trend = go.Figure()
        fig_trend.add_trace(
            go.Bar(x=daily_kpi['date'], y=daily_kpi['revenue'], name='Revenue ($)', marker_color='#93C5FD', yaxis='y2'))
        fig_trend.add_trace(
            go.Scatter(x=daily_kpi['date'], y=daily_kpi['user_id'], name='DAU', line=dict(color='#2563EB', width=3)))

        fig_trend.update_layout(
            template="plotly_white",
            height=450,
            yaxis=dict(title="Active Users"),
            yaxis2=dict(title="Revenue ($)", overlaying='y', side='right', showgrid=False),
            legend=dict(orientation="h", y=1.1, x=0),
            hovermode="x unified"
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    # TAB 2: COHORT ANALYSIS
    with tab2:
        st.subheader("User Retention Heatmap")
        st.markdown("Tracking user return rate on Day 1, 3, 7, 14, 30 after installation.")

        # Calculate Cohort
        retention_matrix, cohort_sizes = calculate_cohort_retention(df_filtered)

        if not retention_matrix.empty:
            # Heatmap Visualization
            fig_cohort = px.imshow(
                retention_matrix,
                labels=dict(x="Days Since Install", y="Install Date", color="Retention (%)"),
                x=retention_matrix.columns,
                y=retention_matrix.index,
                color_continuous_scale="Blues",  # Light Theme friendly
                text_auto='.1f',
                aspect="auto"
            )
            fig_cohort.update_layout(
                template="plotly_white",
                height=600,
                xaxis_title="Days Later (D0, D1, D7...)",
                yaxis_title="Cohort Date"
            )
            st.plotly_chart(fig_cohort, use_container_width=True)

            # Insight Text
            avg_d1 = retention_matrix[1].mean() if 1 in retention_matrix.columns else 0
            avg_d7 = retention_matrix[7].mean() if 7 in retention_matrix.columns else 0

            col_c1, col_c2 = st.columns(2)
            col_c1.info(f"**Average D1 Retention:** {avg_d1:.1f}% (Benchmark: >35%)")
            col_c2.info(f"**Average D7 Retention:** {avg_d7:.1f}% (Benchmark: >15%)")
        else:
            st.warning("Not enough data to generate Cohort Analysis.")

    # TAB 3: ECONOMY
    with tab3:
        col_eco1, col_eco2 = st.columns(2)
        with col_eco1:
            st.subheader("Source vs Sink")
            eco_df = df_filtered[df_filtered['event_name'].isin(['currency_source', 'currency_sink'])].copy()
            eco_df['amount_abs'] = eco_df['gold_change'].abs()
            eco_daily = eco_df.groupby(['date', 'event_name'])['amount_abs'].sum().reset_index()

            fig_flow = px.bar(
                eco_daily, x='date', y='amount_abs', color='event_name',
                color_discrete_map={'currency_source': '#10B981', 'currency_sink': '#EF4444'},
                labels={'amount_abs': 'Gold Volume'}
            )
            fig_flow.update_layout(template="plotly_white", legend=dict(orientation="h", y=1.1, x=0))
            st.plotly_chart(fig_flow, use_container_width=True)

        with col_eco2:
            st.subheader("Avg Wallet Balance")
            balance_df = compute_wallet_metrics(df_filtered)
            fig_bal = px.line(balance_df, x='date', y='avg_balance', markers=True)
            fig_bal.update_traces(line_color='#8B5CF6', line_width=3)
            fig_bal.update_layout(template="plotly_white", yaxis_title="Avg Gold")
            st.plotly_chart(fig_bal, use_container_width=True)

    # TAB 4: FUNNEL
    with tab4:
        st.subheader("Level Difficulty Funnel")
        level_df = df_filtered[df_filtered['event_name'].isin(['level_complete', 'level_fail'])]

        if not level_df.empty:
            level_stats = level_df.groupby('level')['event_name'].value_counts().unstack(fill_value=0)
            if 'level_complete' not in level_stats.columns: level_stats['level_complete'] = 0
            if 'level_fail' not in level_stats.columns: level_stats['level_fail'] = 0

            level_stats['total'] = level_stats['level_complete'] + level_stats['level_fail']
            level_stats['win_rate'] = (level_stats['level_complete'] / level_stats['total']) * 100
            level_stats = level_stats.reset_index()

            fig_funnel = go.Figure()
            fig_funnel.add_trace(
                go.Bar(x=level_stats['level'], y=level_stats['total'], name='Attempts', marker_color='#E5E7EB'))
            fig_funnel.add_trace(
                go.Scatter(x=level_stats['level'], y=level_stats['win_rate'], name='Win Rate %', yaxis='y2',
                           line=dict(color='#F59E0B', width=3)))

            fig_funnel.update_layout(
                template="plotly_white",
                height=500,
                xaxis=dict(title="Level", dtick=1),
                yaxis=dict(title="Attempts"),
                yaxis2=dict(title="Win Rate %", overlaying='y', side='right', range=[0, 100]),
                legend=dict(orientation="h", y=1.1, x=0)
            )
            st.plotly_chart(fig_funnel, use_container_width=True)

            # Anomaly Table
            critical = level_stats[level_stats['win_rate'] < 30]
            if not critical.empty:
                st.error("Critical Levels Detected (Win Rate < 30%)")
                st.dataframe(critical[['level', 'total', 'win_rate']].style.format({'win_rate': '{:.2f}%'}),
                             use_container_width=True)

else:
    st.info("Please generate data first: `python data_generator/generate_data.py`")
