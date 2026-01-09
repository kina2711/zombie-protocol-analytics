/* Query 03: Game Economy Balance (Source Analysis)
   Analyze how much Gold users earn at each level to detect inflation/deflation.
*/

SELECT
    level_id,
    COUNT(DISTINCT user_id) as players_reached,
    SUM(gold_earned) as total_gold_source,
    ROUND(AVG(gold_earned), 0) as avg_gold_per_level,
    -- Giả sử ta muốn biết trung bình mỗi user tích lũy được bao nhiêu tại level này
    ROUND(SUM(gold_earned) / COUNT(DISTINCT user_id), 0) as gold_per_user
FROM
    `zombie-protocol-analytics.analytics_zombie_protocol.master_events`
WHERE
    event_name = 'level_complete'
    AND level_id IS NOT NULL
GROUP BY
    1
ORDER BY
    1 ASC;