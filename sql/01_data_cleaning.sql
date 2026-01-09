/* COMMIT: 01_data_cleaning.sql
   MỤC TIÊU: Làm sạch và chuẩn hóa dữ liệu từ bảng Raw (Nested JSON).
   INPUT: `zombie-protocol-analytics.analytics_zombie_protocol.raw_events`
   OUTPUT: Bảng phẳng chứa các trường quan trọng.
*/

SELECT
    -- 1. Chuẩn hóa thời gian (Integer -> Date)
    PARSE_DATE('%Y%m%d', CAST(event_date AS STRING)) AS date,
    TIMESTAMP_MICROS(event_timestamp) AS timestamp,
    event_name,
    user_pseudo_id AS user_id,

    -- 2. Trích xuất thông tin User & Session
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'user_type') AS user_segment,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,

    -- 3. Trích xuất thông tin Game (Level, Kết quả)
    COALESCE(
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'level'),
        1
    ) AS current_level,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'mission_id') AS mission_id,

    -- 4. Trích xuất thông tin Kinh tế (Revenue, Gold)
    COALESCE(
        (SELECT value.double_value FROM UNNEST(event_params) WHERE key = 'value'),
        0.0
    ) AS revenue_usd,
    COALESCE(
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'amount'),
        0
    ) AS gold_amount

FROM `zombie-protocol-analytics.analytics_zombie_protocol.raw_events`
WHERE event_date >= 20250101
ORDER BY event_timestamp DESC;