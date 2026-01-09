/* COMMIT: 04_engagement_kpi.sql
   MỤC TIÊU: Theo dõi DAU, MAU và Stickiness.
*/

WITH daily_stats AS (
    SELECT
        PARSE_DATE('%Y%m%d', CAST(event_date AS STRING)) AS date,
        COUNT(DISTINCT user_pseudo_id) AS dau
    FROM `zombie-protocol-analytics.analytics_zombie_protocol.raw_events`
    WHERE event_name = 'session_start'
    GROUP BY 1
),

monthly_stats AS (
    SELECT
        DATE_TRUNC(PARSE_DATE('%Y%m%d', CAST(event_date AS STRING)), MONTH) AS month_start,
        COUNT(DISTINCT user_pseudo_id) AS mau
    FROM `zombie-protocol-analytics.analytics_zombie_protocol.raw_events`
    WHERE event_name = 'session_start'
    GROUP BY 1
)

SELECT
    D.date,
    D.dau,
    M.mau,
    -- Stickiness: Tỷ lệ người chơi hàng ngày trên tổng người chơi tháng
    ROUND((D.dau / M.mau) * 100, 2) AS stickiness_percent
FROM daily_stats D
LEFT JOIN monthly_stats M ON DATE_TRUNC(D.date, MONTH) = M.month_start
ORDER BY 1 DESC;