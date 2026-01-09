/* COMMIT: 06_game_difficulty.sql
   MỤC TIÊU: Xác định Level nào quá khó khiến user bỏ cuộc.
   LOGIC: Tính Win Rate = Số lần thắng / (Thắng + Thua) tại mỗi Level.
*/

SELECT
    -- Lấy Level từ event_params
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'level') AS level_id,

    -- Đếm số lần chơi, thắng, thua
    COUNT(*) AS total_attempts,
    COUNTIF(event_name = 'level_complete') AS wins,
    COUNTIF(event_name = 'level_fail') AS losses,

    -- Tỷ lệ Thắng (Win Rate)
    ROUND(SAFE_DIVIDE(COUNTIF(event_name = 'level_complete'), COUNT(*)) * 100, 2) AS win_rate_percent,

    -- Số user bị kẹt ở level này (Churn tại level)
    COUNT(DISTINCT user_pseudo_id) AS unique_users_attempted

FROM `zombie-protocol-analytics.analytics_zombie_protocol.raw_events`
WHERE event_name IN ('level_complete', 'level_fail')
GROUP BY 1
ORDER BY level_id ASC;