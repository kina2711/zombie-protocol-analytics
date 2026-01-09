/* COMMIT: 02_retention_heatmap.sql
   MỤC TIÊU: Tạo dataset chuẩn Long Format để vẽ Cohort Heatmap.
   OUTPUT: Cohort Date | Day Index (0,1,2...) | Retention Rate (%)
*/

WITH cohort_users AS (
    SELECT
        user_pseudo_id,
        MIN(PARSE_DATE('%Y%m%d', CAST(event_date AS STRING))) AS install_date
    FROM `zombie-protocol-analytics.analytics_zombie_protocol.raw_events`
    GROUP BY 1
),

daily_activity AS (
    SELECT DISTINCT
        user_pseudo_id,
        PARSE_DATE('%Y%m%d', CAST(event_date AS STRING)) AS active_date
    FROM `zombie-protocol-analytics.analytics_zombie_protocol.raw_events`
    WHERE event_name = 'session_start'
),

retention_base AS (
    SELECT
        C.install_date,
        DATE_DIFF(A.active_date, C.install_date, DAY) AS day_index,
        COUNT(DISTINCT C.user_pseudo_id) AS active_users
    FROM cohort_users C
    JOIN daily_activity A ON C.user_pseudo_id = A.user_pseudo_id
    WHERE DATE_DIFF(A.active_date, C.install_date, DAY) BETWEEN 0 AND 30 -- Lấy 30 ngày đầu
    GROUP BY 1, 2
),

cohort_size AS (
    SELECT install_date, COUNT(DISTINCT user_pseudo_id) as total_users
    FROM cohort_users
    GROUP BY 1
)

SELECT
    R.install_date,
    R.day_index, -- Trục X của Heatmap (Day 0, 1, 2...)
    R.active_users,
    S.total_users,
    -- Retention Rate (%) -> Giá trị tô màu Heatmap
    ROUND((R.active_users / S.total_users) * 100, 2) AS retention_rate
FROM retention_base R
JOIN cohort_size S ON R.install_date = S.install_date
ORDER BY 1, 2;