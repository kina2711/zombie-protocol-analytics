/* Query 07: User Acquisition & ROAS (Return on Ad Spend)
   Logic: Join Marketing Data (Cost) with Game Data (Revenue) to measure campaign efficiency.
*/

WITH user_revenue AS (
    -- 1. Tính tổng doanh thu (LTV) của từng user trọn đời
    SELECT
        user_id,
        SUM(revenue) as total_ltv
    FROM
        `zombie-protocol-analytics.analytics_zombie_protocol.master_events`
    WHERE
        event_name = 'iap_purchase'
    GROUP BY
        1
),

marketing_costs AS (
    -- 2. Lấy thông tin nguồn và chi phí cài đặt
    SELECT
        user_id,
        source,
        cpi, -- Cost Per Install
        install_date
    FROM
        `zombie-protocol-analytics.analytics_zombie_protocol.user_acquisition`
    WHERE
        install_date BETWEEN '2025-11-01' AND '2025-11-30'
)

-- 3. Tổng hợp Metrics
SELECT
    m.source,
    COUNT(DISTINCT m.user_id) as installs,

    -- Tổng chi phí Marketing (Total Spend)
    ROUND(SUM(m.cpi), 2) as total_spend,

    -- Tổng doanh thu từ nhóm user này
    ROUND(SUM(COALESCE(r.total_ltv, 0)), 2) as total_revenue,

    -- Chỉ số CPI trung bình (Cost Per Install)
    ROUND(AVG(m.cpi), 2) as avg_cpi,

    -- Chỉ số ARPU của nguồn này (Average Revenue Per User)
    ROUND(AVG(COALESCE(r.total_ltv, 0)), 2) as arpu,

    -- Chỉ số quan trọng nhất: ROAS (Return on Ad Spend)
    -- ROAS > 100% (hoặc 1.0) là lãi, < 100% là lỗ
    ROUND(SAFE_DIVIDE(SUM(COALESCE(r.total_ltv, 0)), SUM(m.cpi)) * 100, 2) as roas_percentage

FROM
    marketing_costs m
LEFT JOIN
    user_revenue r ON m.user_id = r.user_id
GROUP BY
    1
ORDER BY
    roas_percentage DESC;