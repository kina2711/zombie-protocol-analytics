import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. CONFIGURATION & STYLING
st.set_page_config(
    page_title="Zombie Protocol Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Professional Dashboard UI
# Style: Dark Modern, Card-based layout, Clean Typography
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #0E1117;
    }

    /* Metric Cards Styling */
    div[data-testid="stMetric"] {
        background-color: #1F2937;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px;
        color: #9CA3AF;
        font-weight: 500;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #F9FAFB;
        font-weight: 700;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 14px;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px;
        color: #9CA3AF;
        font-size: 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1F2937;
        color: #60A5FA;
        border-bottom: 2px solid #60A5FA;
    }

    /* Headers */
    h1, h2, h3 {
        color: #F3F4F6;
        font-family: 'Inter', sans-serif;
    }

    /* DataFrame Styling */
    .dataframe {
        font-family: 'Inter', sans-serif;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# 2. DATA PIPELINE
@st.cache_data
def load_dataset():
    """
    Load and preprocess raw game data.
    Returns: DataFrame or None if file missing.
    """
    try:
        df = pd.read_csv('data/game_data.csv')
        df['date'] = pd.to_datetime(df['date'])
        return df
    except FileNotFoundError:
        return None

def compute_wallet_metrics(df):
    """
    Compute daily cumulative gold balance and active user base.
    """
    # Aggregate daily gold flow
    daily_flow = df.groupby('date')['gold_change'].sum().reset_index()
    daily_flow['cumulative_gold'] = daily_flow['gold_change'].cumsum()

    # Count daily active users
    daily_dau = df.groupby('date')['user_id'].nunique().reset_index(name='active_users')

    # Merge and calculate average
    merged_df = pd.merge(daily_flow, daily_dau, on='date')
    merged_df['avg_balance'] = merged_df['cumulative_gold'] / merged_df['active_users']

    return merged_df

# Load Data
df_raw = load_dataset()

# 3. SIDEBAR: GLOBAL FILTERS
st.sidebar.markdown("### Configuration")

if df_raw is not None:
    # Date Range Filter
    min_date = df_raw['date'].min()
    max_date = df_raw['date'].max()

    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # User Segment Filter
    # Check if 'segment' column exists, otherwise use 'user_type' or default
    segment_col = 'user_type' if 'user_type' in df_raw.columns else 'segment'
    if segment_col in df_raw.columns:
        available_segments = df_raw[segment_col].unique()
        selected_segments = st.sidebar.multiselect(
            "User Segments",
            options=available_segments,
            default=available_segments
        )
    else:
        selected_segments = []

    # Apply Filters
    mask = (df_raw['date'].dt.date >= date_range[0]) & (df_raw['date'].dt.date <= date_range[1])
    if selected_segments:
        mask = mask & (df_raw[segment_col].isin(selected_segments))

    df_filtered = df_raw.loc[mask]
else:
    df_filtered = None

st.sidebar.markdown("---")
st.sidebar.caption("System Version: v2.4.0")
st.sidebar.caption("Environment: Production")

# 4. MAIN DASHBOARD LAYOUT

if df_filtered is not None and not df_filtered.empty:
    st.title("ZOMBIE PROTOCOL: ANALYTICS DASHBOARD")
    st.markdown("Operational Metrics & Performance Indicators")
    st.markdown("---")

    # High-level KPI Cards
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    # Metrics Calculation
    total_rev = df_filtered['revenue'].sum()
    unique_users = df_filtered['user_id'].nunique()
    avg_dau = df_filtered.groupby('date')['user_id'].nunique().mean()
    arpu = total_rev / unique_users if unique_users > 0 else 0

    # Calculate Delta (vs Previous Period - Simulated logic for demo)
    # In production, this should compare with (start_date - period)

    with kpi_col1:
        st.metric("Avg Daily Active Users (DAU)", f"{int(avg_dau):,}")
    with kpi_col2:
        st.metric("Total Period Users", f"{unique_users:,}")
    with kpi_col3:
        st.metric("Total Revenue", f"${total_rev:,.2f}")
    with kpi_col4:
        st.metric("ARPU", f"${arpu:.2f}")

    st.markdown("###")  # Spacer

    # TABS: Logical Separation of Concerns
    tab1, tab2, tab3 = st.tabs([
        "Performance Overview",
        "Economy Health",
        "Progression & Difficulty"
    ])

    # TAB 1: PERFORMANCE OVERVIEW
    with tab1:
        st.subheader("Traffic & Revenue Trends")

        # Prepare Time-series Data
        daily_kpi = df_filtered.groupby('date').agg({
            'user_id': 'nunique',
            'revenue': 'sum'
        }).reset_index().rename(columns={'user_id': 'DAU', 'revenue': 'Revenue'})

        # Dual Axis Chart
        fig_trend = go.Figure()

        # Bar: Revenue
        fig_trend.add_trace(go.Bar(
            x=daily_kpi['date'],
            y=daily_kpi['Revenue'],
            name='Revenue ($)',
            marker_color='#3B82F6',
            opacity=0.6,
            yaxis='y2'
        ))

        # Line: DAU
        fig_trend.add_trace(go.Scatter(
            x=daily_kpi['date'],
            y=daily_kpi['DAU'],
            name='Active Users',
            mode='lines+markers',
            line=dict(color='#10B981', width=3),
            marker=dict(size=6)
        ))

        fig_trend.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=450,
            xaxis=dict(title="Date", showgrid=False),
            yaxis=dict(title="Active Users", showgrid=True, gridcolor='#374151'),
            yaxis2=dict(title="Revenue ($)", overlaying='y', side='right', showgrid=False),
            legend=dict(orientation="h", y=1.1, x=0),
            margin=dict(l=0, r=0, t=40, b=0)
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    # TAB 2: ECONOMY HEALTH
    with tab2:
        col_eco1, col_eco2 = st.columns([1, 1])

        with col_eco1:
            st.subheader("Source vs. Sink Distribution")

            # Data Processing
            eco_df = df_filtered[df_filtered['event_name'].isin(['currency_source', 'currency_sink'])].copy()
            eco_df['amount_abs'] = eco_df['gold_change'].abs()

            eco_daily = eco_df.groupby(['date', 'event_name'])['amount_abs'].sum().reset_index()

            # Stacked Bar Chart
            fig_flow = px.bar(
                eco_daily,
                x='date',
                y='amount_abs',
                color='event_name',
                labels={'amount_abs': 'Currency Volume', 'event_name': 'Flow Type'},
                color_discrete_map={'currency_source': '#10B981', 'currency_sink': '#EF4444'}
            )
            fig_flow.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", y=1.1, x=0),
                margin=dict(l=0, r=0, t=20, b=0)
            )
            st.plotly_chart(fig_flow, use_container_width=True)

        with col_eco2:
            st.subheader("Average Wallet Balance")

            # Compute Balance
            balance_df = compute_wallet_metrics(df_filtered)

            # Line Chart
            fig_bal = px.line(
                balance_df,
                x='date',
                y='avg_balance',
                markers=True
            )
            fig_bal.update_traces(line_color='#8B5CF6', line_width=3)
            fig_bal.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis_title="Avg Gold per User",
                margin=dict(l=0, r=0, t=20, b=0)
            )
            st.plotly_chart(fig_bal, use_container_width=True)

        # Insight / Warning System (Professional Text)
        with st.expander("Diagnostic Analysis", expanded=True):
            net_flow = eco_df[eco_df['event_name'] == 'currency_source']['amount_abs'].sum() - \
                       eco_df[eco_df['event_name'] == 'currency_sink']['amount_abs'].sum()

            status_color = "red" if net_flow < 0 else "green"
            st.markdown(f"**Net System Flow:** <span style='color:{status_color}'>{net_flow:,.0f} Gold</span>",
                        unsafe_allow_html=True)
            st.caption(
                "A positive net flow indicates accumulation (potential inflation). A negative net flow indicates deficit (potential deflation).")

    # TAB 3: PROGRESSION & DIFFICULTY
    with tab3:
        st.subheader("Level Progression Funnel")

        # Filter Level Events
        level_df = df_filtered[df_filtered['event_name'].isin(['level_complete', 'level_fail'])]

        if not level_df.empty:
            # Aggregate Data
            level_stats = level_df.groupby('level')['event_name'].value_counts().unstack(fill_value=0)

            # Normalize Columns
            if 'level_complete' not in level_stats.columns: level_stats['level_complete'] = 0
            if 'level_fail' not in level_stats.columns: level_stats['level_fail'] = 0

            # Metric Calculation
            level_stats['total_attempts'] = level_stats['level_complete'] + level_stats['level_fail']
            level_stats['win_rate'] = (level_stats['level_complete'] / level_stats['total_attempts']) * 100
            level_stats = level_stats.reset_index()

            # Visualization: Attempts vs Win Rate
            fig_funnel = go.Figure()

            # Bar: Attempts
            fig_funnel.add_trace(go.Bar(
                x=level_stats['level'],
                y=level_stats['total_attempts'],
                name='Total Attempts',
                marker_color='#4B5563',
                opacity=0.5
            ))

            # Line: Win Rate
            fig_funnel.add_trace(go.Scatter(
                x=level_stats['level'],
                y=level_stats['win_rate'],
                name='Win Rate (%)',
                mode='lines+markers',
                yaxis='y2',
                line=dict(color='#F59E0B', width=3)
            ))

            # Threshold Line
            fig_funnel.add_hline(y=30, line_dash="dot", line_color="#EF4444", yref="y2",
                                 annotation_text="Critical Threshold (30%)")

            fig_funnel.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=500,
                xaxis=dict(title="Level ID", dtick=1),
                yaxis=dict(title="Volume"),
                yaxis2=dict(title="Win Rate (%)", overlaying='y', side='right', range=[0, 100]),
                legend=dict(orientation="h", y=1.1, x=0),
                margin=dict(l=0, r=0, t=40, b=0)
            )
            st.plotly_chart(fig_funnel, use_container_width=True)

            # Anomaly Detection Report
            st.subheader("Anomaly Detection Report")
            critical_levels = level_stats[level_stats['win_rate'] < 30].sort_values('win_rate')

            if not critical_levels.empty:
                st.dataframe(
                    critical_levels[['level', 'total_attempts', 'win_rate']].style.format({'win_rate': '{:.2f}%'}),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No levels detected below the critical win rate threshold.")

        else:
            st.warning("Insufficient gameplay data for analysis.")

else:
    # Empty State / Initialization
    st.info("Awaiting Dataset. Please execute the data generation pipeline.")
    st.code("python data_generator/generate_data.py", language="bash")