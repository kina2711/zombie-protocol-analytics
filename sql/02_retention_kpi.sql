/* COMMIT: 02_retention_kpi.sql
   MỤC TIÊU: Tính Retention Rate (D1, D7, D30).
   LOGIC: So sánh ngày Active với ngày Install đầu tiên.
*/

WITH cohort_users AS (
    -- Tìm ngày cài đặt (Install Date)
    SELECT
        user_pseudo_id,
        MIN(PARSE_DATE('%Y%m%d', CAST(event_date AS STRING))) AS install_date
    FROM `zombie-protocol-analytics.analytics_zombie_protocol.raw_events`
    GROUP BY 1
),

daily_activity AS (
    -- Tìm các ngày user có hoạt động (Active Date)
    SELECT DISTINCT
        user_pseudo_id,
        PARSE_DATE('%Y%m%d', CAST(event_date AS STRING)) AS active_date
    FROM `zombie-protocol-analytics.analytics_zombie_protocol.raw_events`
    WHERE event_name = 'session_start'
)

SELECT
    C.install_date,
    COUNT(DISTINCT C.user_pseudo_id) AS cohort_size,

    -- D1 Retention
    COUNT(DISTINCT CASE WHEN DATE_DIFF(A.active_date, C.install_date, DAY) = 1 THEN C.user_pseudo_id END) AS d1_users,
    ROUND(COUNT(DISTINCT CASE WHEN DATE_DIFF(A.active_date, C.install_date, DAY) = 1 THEN C.user_pseudo_id END) / COUNT(DISTINCT C.user_pseudo_id) * 100, 2) AS d1_percent,

    -- D7 Retention
    COUNT(DISTINCT CASE WHEN DATE_DIFF(A.active_date, C.install_date, DAY) = 7 THEN C.user_pseudo_id END) AS d7_users,
    ROUND(COUNT(DISTINCT CASE WHEN DATE_DIFF(A.active_date, C.install_date, DAY) = 7 THEN C.user_pseudo_id END) / COUNT(DISTINCT C.user_pseudo_id) * 100, 2) AS d7_percent,

    -- D30 Retention
    COUNT(DISTINCT CASE WHEN DATE_DIFF(A.active_date, C.install_date, DAY) = 30 THEN C.user_pseudo_id END) AS d30_users,
    ROUND(COUNT(DISTINCT CASE WHEN DATE_DIFF(A.active_date, C.install_date, DAY) = 30 THEN C.user_pseudo_id END) / COUNT(DISTINCT C.user_pseudo_id) * 100, 2) AS d30_percent

FROM cohort_users C
LEFT JOIN daily_activity A ON C.user_pseudo_id = A.user_pseudo_id
GROUP BY 1
ORDER BY 1 DESC;