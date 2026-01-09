/* COMMIT: 07_ltv_analytics.sql
   MỤC TIÊU: Tính LTV (Lifetime Value) theo Cohort.
   BUSINESS QUESTION: Trung bình một user cài game vào ngày X sẽ mang lại bao nhiêu doanh thu tích lũy sau N ngày?
   LOGIC: 
   1. Xác định Cohort (Ngày cài đặt).
   2. Tính doanh thu của từng user trong các ngày sau đó.
   3. Cộng dồn doanh thu (Cumulative Sum) và chia cho số lượng user ban đầu.
*/

WITH cohort_users AS (
    -- 1. Xác định ngày cài đặt và tổng số user mỗi ngày
    SELECT 
        MIN(PARSE_DATE('%Y%m%d', CAST(event_date AS STRING))) AS install_date,
        user_pseudo_id
    FROM `zombie-protocol-analytics.analytics_zombie_protocol.raw_events`
    GROUP BY 2
),

daily_revenue AS (
    -- 2. Tính doanh thu user tạo ra mỗi ngày
    SELECT 
        user_pseudo_id,
        PARSE_DATE('%Y%m%d', CAST(event_date AS STRING)) AS revenue_date,
        SUM(
            COALESCE((SELECT value.double_value FROM UNNEST(event_params) WHERE key = 'value'), 0)
        ) AS daily_rev
    FROM `zombie-protocol-analytics.analytics_zombie_protocol.raw_events`
    WHERE event_name = 'in_app_purchase'
    GROUP BY 1, 2
),

ltv_calculation AS (
    -- 3. Join Cohort với Doanh thu để tính LTV tích lũy
    SELECT
        C.install_date,
        DATE_DIFF(R.revenue_date, C.install_date, DAY) AS day_index,
        SUM(R.daily_rev) AS total_daily_rev
    FROM cohort_users C
    JOIN daily_revenue R ON C.user_pseudo_id = R.user_pseudo_id
    WHERE R.revenue_date >= C.install_date
    GROUP BY 1, 2
),

cohort_sizes AS (
    SELECT install_date, COUNT(DISTINCT user_pseudo_id) as cohort_size
    FROM cohort_users
    GROUP BY 1
)

SELECT
    L.install_date,
    S.cohort_size,
    L.day_index,
    -- Doanh thu tích lũy đến ngày N (Cumulative Revenue)
    SUM(L.total_daily_rev) OVER (PARTITION BY L.install_date ORDER BY L.day_index) AS cumulative_revenue,
    
    -- LTV = Doanh thu tích lũy / Số user ban đầu
    ROUND(
        SUM(L.total_daily_rev) OVER (PARTITION BY L.install_date ORDER BY L.day_index) / S.cohort_size, 
        4
    ) AS ltv_cumulative
    
FROM ltv_calculation L
JOIN cohort_sizes S ON L.install_date = S.install_date
ORDER BY 1, 3;
