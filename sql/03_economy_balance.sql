/* COMMIT: 03_economy_balance.sql
   MỤC TIÊU: Game Economy Health Check.
   METRICS: Total Source (Tiền vào), Total Sink (Tiền ra), Net Flow.
*/

SELECT
  PARSE_DATE('%Y%m%d', CAST(event_date AS STRING)) AS date,

  -- 1. SOURCE: Tổng tiền người chơi kiếm được
  SUM(CASE WHEN event_name = 'currency_source' THEN
      (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'amount')
      ELSE 0 END) AS total_source,

  -- 2. SINK: Tổng tiền người chơi tiêu đi
  SUM(CASE WHEN event_name = 'currency_sink' THEN
      (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'amount')
      ELSE 0 END) AS total_sink,

  -- 3. NET FLOW & RATIO
  (SUM(CASE WHEN event_name = 'currency_source' THEN (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'amount') ELSE 0 END)
   -
   SUM(CASE WHEN event_name = 'currency_sink' THEN (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'amount') ELSE 0 END)) AS net_flow,

  SAFE_DIVIDE(
    SUM(CASE WHEN event_name = 'currency_source' THEN (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'amount') ELSE 0 END),
    SUM(CASE WHEN event_name = 'currency_sink' THEN (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'amount') ELSE 0 END)
  ) AS source_sink_ratio -- Nếu > 1.2 liên tục là dấu hiệu lạm phát

FROM `zombie-protocol-analytics.analytics_zombie_protocol.raw_events`
WHERE event_name IN ('currency_source', 'currency_sink')
GROUP BY 1
ORDER BY 1 DESC;