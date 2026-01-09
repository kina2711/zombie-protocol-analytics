/* Query 06: Monetization KPIs (Daily)
   Track Revenue, ARPU (Avg Revenue Per User), and ARPPU (Avg Revenue Per Paying User)
*/

WITH daily_stats AS (
    SELECT
        event_date, -- Đã là kiểu DATE, không cần PARSE
        COUNT(DISTINCT user_id) as dau,
        COUNT(DISTINCT CASE WHEN event_name = 'iap_purchase' THEN user_id END) as paying_users,
        SUM(revenue) as total_revenue
    FROM
        `zombie-protocol-analytics.analytics_zombie_protocol.master_events`
    GROUP BY
        1
)

SELECT
    event_date,
    dau,
    paying_users,
    COALESCE(total_revenue, 0) as total_revenue,

    -- ARPU: Doanh thu trung bình trên mỗi User Active
    ROUND(SAFE_DIVIDE(total_revenue, dau), 3) as arpu,

    -- ARPPU: Doanh thu trung bình trên mỗi User CÓ TRẢ TIỀN
    ROUND(SAFE_DIVIDE(total_revenue, paying_users), 3) as arppu,

    -- Conversion Rate: Tỷ lệ chuyển đổi thành người nạp tiền
    ROUND(SAFE_DIVIDE(paying_users, dau), 4) as conversion_rate

FROM
    daily_stats
ORDER BY
    event_date DESC;