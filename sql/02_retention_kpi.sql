/* Query 02: Retention Calculation (Optimized)
*/
WITH cohort AS (
  SELECT
    user_pseudo_id,
    MIN(event_date) as cohort_date
  FROM `zombie-protocol-analytics.analytics_zombie_protocol.master_events`
  GROUP BY 1
),
activity AS (
  SELECT DISTINCT
    user_pseudo_id,
    event_date
  FROM `zombie-protocol-analytics.analytics_zombie_protocol.master_events`
)

SELECT
  C.cohort_date,
  COUNT(DISTINCT C.user_pseudo_id) as cohort_size,
  COUNT(DISTINCT CASE WHEN DATE_DIFF(A.event_date, C.cohort_date, DAY) = 1 THEN C.user_pseudo_id END) as d1_retention,
  COUNT(DISTINCT CASE WHEN DATE_DIFF(A.event_date, C.cohort_date, DAY) = 3 THEN C.user_pseudo_id END) as d3_retention,
  COUNT(DISTINCT CASE WHEN DATE_DIFF(A.event_date, C.cohort_date, DAY) = 7 THEN C.user_pseudo_id END) as d7_retention

FROM cohort C
LEFT JOIN activity A ON C.user_pseudo_id = A.user_pseudo_id
GROUP BY 1
ORDER BY 1 DESC;