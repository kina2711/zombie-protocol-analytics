/* COMMIT: 05_monetization_kpi.sql
   MỤC TIÊU: Tính ARPU (Doanh thu/User), ARPPU (Doanh thu/User trả phí).
*/

WITH daily_revenue AS (
    SELECT
        PARSE_DATE('%Y%m%d', CAST(event_date AS STRING)) AS date,
        COUNT(DISTINCT user_pseudo_id) AS active_users,

        -- Đếm số người trả phí (Payer)
        COUNT(DISTINCT CASE WHEN event_name = 'in_app_purchase' THEN user_pseudo_id END) AS paying_users,

        -- Tổng doanh thu
        SUM(CASE WHEN event_name = 'in_app_purchase' THEN
            (SELECT value.double_value FROM UNNEST(event_params) WHERE key = 'value')
            ELSE 0 END) AS total_revenue
    FROM `zombie-protocol-analytics.analytics_zombie_protocol.raw_events`
    GROUP BY 1
)

SELECT
    date,
    total_revenue,
    active_users,
    paying_users,

    -- ARPU: Doanh thu trung bình trên mỗi User active
    SAFE_DIVIDE(total_revenue, active_users) AS arpu,

    -- ARPPU: Doanh thu trung bình trên mỗi User trả phí (Whales chi bao nhiêu?)
    SAFE_DIVIDE(total_revenue, paying_users) AS arppu,

    -- Conversion Rate: Tỷ lệ chuyển đổi thành khách hàng trả phí
    ROUND(SAFE_DIVIDE(paying_users, active_users) * 100, 2) AS conversion_rate_percent

FROM daily_revenue
WHERE total_revenue > 0
ORDER BY 1 DESC;