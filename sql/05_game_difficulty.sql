/* Query 05: Level Difficulty Curve (Win Rate Analysis)
   Identify "Choke Points" where users drop off due to difficulty.
*/

SELECT
    level_id,
    COUNT(*) as total_attempts,
    COUNTIF(win_loss_status = 'Win') as wins,
    COUNTIF(win_loss_status = 'Fail') as fails,
    -- Tính Win Rate %
    ROUND(COUNTIF(win_loss_status = 'Win') / COUNT(*), 2) as win_rate,
    -- Tính tỷ lệ chết (Fail Rate)
    ROUND(COUNTIF(win_loss_status = 'Fail') / COUNT(*), 2) as fail_rate
FROM
    `zombie-protocol-analytics.analytics_zombie_protocol.master_events`
WHERE
    event_name IN ('level_complete', 'level_fail')
    AND level_id IS NOT NULL
GROUP BY
    1
ORDER BY
    1 ASC;