import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Zombie Protocol: Cohort Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS tùy chỉnh để làm đẹp bảng Heatmap
st.markdown("""
<style>
    .stApp { background-color: #F9FAFB; color: #111827; }
    h1, h2, h3 { font-family: 'Inter', sans-serif; }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. DATA PIPELINE
# -----------------------------------------------------------------------------
@st.cache_data
def load_dataset():
    """Load dữ liệu và xử lý ngày tháng."""
    try:
        df = pd.read_csv('data/game_data.csv')
        df['date'] = pd.to_datetime(df['date'])
        # Lọc dữ liệu từ 1/1/2025 theo yêu cầu
        df = df[df['date'] >= '2025-01-01']
        return df
    except FileNotFoundError:
        return None


def calculate_triangular_cohort(df):
    """
    Xử lý dữ liệu Raw thành ma trận Cohort Heatmap (Triangular).
    """
    # 1. Xác định Install Date cho mỗi user (Ngày đầu tiên xuất hiện)
    # Group by User ID -> Lấy Min Date
    user_install = df.groupby('user_id')['date'].min().rename('install_date')
    df_merged = df.merge(user_install, on='user_id')

    # 2. Tính Day Index (Ngày hoạt động - Ngày cài đặt)
    df_merged['day_index'] = (df_merged['date'] - df_merged['install_date']).dt.days

    # 3. Tạo bảng tổng hợp: Install Date | Day Index | Active Users
    cohort_data = df_merged.groupby(['install_date', 'day_index'])['user_id'].nunique().reset_index()
    cohort_data.rename(columns={'user_id': 'active_users'}, inplace=True)

    # 4. Tính Cohort Size (Số user tại Day 0)
    cohort_sizes = cohort_data[cohort_data['day_index'] == 0][['install_date', 'active_users']]
    cohort_sizes.rename(columns={'active_users': 'cohort_size'}, inplace=True)

    # 5. Merge lại để tính % Retention
    cohort_data = cohort_data.merge(cohort_sizes, on='install_date')
    cohort_data['retention_rate'] = (cohort_data['active_users'] / cohort_data['cohort_size']) * 100

    # 6. Format lại ngày tháng cho Index (Bỏ giờ phút giây)
    cohort_data['install_date_str'] = cohort_data['install_date'].dt.strftime('%Y-%m-%d')

    # 7. PIVOT TABLE: Hàng=Ngày cài, Cột=Day Index, Giá trị=Retention%
    # Chỉ lấy đến Day 14 hoặc 30 để bảng không quá dài
    cohort_data = cohort_data[cohort_data['day_index'] <= 14]

    cohort_pivot = cohort_data.pivot(
        index='install_date_str',
        columns='day_index',
        values='retention_rate'
    )

    # Lấy thêm cột Cohort Size để hiển thị bên cạnh (như ảnh mẫu)
    cohort_size_df = cohort_sizes.copy()
    cohort_size_df['install_date_str'] = cohort_size_df['install_date'].dt.strftime('%Y-%m-%d')
    cohort_size_df = cohort_size_df.set_index('install_date_str')['cohort_size']

    return cohort_pivot, cohort_size_df


# Load Data
df_raw = load_dataset()

# -----------------------------------------------------------------------------
# 3. MAIN APP
# -----------------------------------------------------------------------------
if df_raw is not None and not df_raw.empty:
    st.title("ZOMBIE PROTOCOL: COHORT MASTER")
    st.markdown("---")

    # TAB XỬ LÝ
    tab1, tab2 = st.tabs(["Triangular Cohort Heatmap", "Stats Overview"])

    with tab1:
        st.subheader("Classic Retention Matrix")
        st.caption("Dữ liệu tính từ 01/01/2025. Hiển thị tỷ lệ quay lại (%) theo ngày.")

        # Tính toán
        retention_matrix, cohort_sizes = calculate_triangular_cohort(df_raw)

        # Layout: Chia cột để hiển thị Size và Heatmap
        col1, col2 = st.columns([1, 5])

        with col1:
            st.markdown("**New Users**")
            # Hiển thị cột Cohort Size dạng bảng nhỏ
            st.dataframe(cohort_sizes, height=600, use_container_width=True)

        with col2:
            st.markdown("**Retention Rate (%) by Days Since Install**")

            # VẼ HEATMAP TAM GIÁC (PLOTLY)
            fig = px.imshow(
                retention_matrix,
                labels=dict(x="Day Index", y="Cohort Date", color="Retention (%)"),
                text_auto='.1f',  # Hiển thị số thập phân 1 số
                color_continuous_scale='RdYlGn',
                aspect="auto",
                origin='upper'  # Đảo ngược trục Y để ngày mới nhất ở dưới
            )

            fig.update_layout(
                height=600,
                xaxis_title="Days Later (0 = Install Day)",
                yaxis_title=None,
                xaxis=dict(side='top'),  # Đưa trục X lên đầu cho dễ nhìn
                coloraxis_showscale=False  # Ẩn thanh màu bên phải cho gọn
            )

            # Xử lý hiển thị NaN thành màu trắng (để tạo hình tam giác)
            fig.update_traces(xgap=1, ygap=1)  # Tạo khe hở giữa các ô

            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # Thống kê nhanh D1, D7
        st.subheader("Quick Stats")
        if 1 in retention_matrix.columns:
            avg_d1 = retention_matrix[1].mean()
            st.metric("Average D1 Retention", f"{avg_d1:.1f}%")

        if 7 in retention_matrix.columns:
            avg_d7 = retention_matrix[7].mean()
            st.metric("Average D7 Retention", f"{avg_d7:.1f}%")

else:
    st.error("Chưa có dữ liệu! Hãy chạy lệnh: `python data_generator/generate_data.py`")
