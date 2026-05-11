-- Materialized View: mv_daily_mood
-- Simulates a materialized view in MySQL via a pre-computed table + stored procedure + event.
-- Purpose: Performance optimization (Kriterium 5) – avoids full aggregation over MOOD_SCORE
--          on every Metabase dashboard load.

-- ============================================================================
-- 1. PRE-COMPUTED TABLE (Materialized View)
-- ============================================================================

CREATE TABLE IF NOT EXISTS mv_daily_mood (
    city_id      INT          NOT NULL,
    date         DATE         NOT NULL,
    avg_mood     FLOAT,
    avg_weather  FLOAT,
    avg_sbb      FLOAT,
    avg_traffic  FLOAT,
    updated_at   DATETIME     NOT NULL,
    PRIMARY KEY (city_id, date),
    INDEX idx_mv_date (date),
    FOREIGN KEY (city_id) REFERENCES CITY(city_id)
);


-- ============================================================================
-- 2. REFRESH PROCEDURE
-- ============================================================================

DROP PROCEDURE IF EXISTS refresh_mv_daily_mood;

DELIMITER //

CREATE PROCEDURE refresh_mv_daily_mood()
BEGIN
    REPLACE INTO mv_daily_mood (city_id, date, avg_mood, avg_weather, avg_sbb, avg_traffic, updated_at)
    SELECT
        city_id,
        DATE(timestamp),
        ROUND(AVG(mood_score),    4),
        ROUND(AVG(weather_score), 4),
        ROUND(AVG(sbb_score),     4),
        ROUND(AVG(traffic_score), 4),
        NOW()
    FROM MOOD_SCORE
    WHERE mood_score IS NOT NULL
    GROUP BY city_id, DATE(timestamp);
END //

DELIMITER ;


-- ============================================================================
-- 3. SCHEDULED EVENT (daily refresh)
-- ============================================================================

-- Enable the event scheduler if not already active:
-- SET GLOBAL event_scheduler = ON;

DROP EVENT IF EXISTS ev_refresh_mv_daily_mood;

CREATE EVENT ev_refresh_mv_daily_mood
    ON SCHEDULE EVERY 1 DAY
    STARTS (CURRENT_DATE + INTERVAL 1 DAY)
    DO CALL refresh_mv_daily_mood();


-- ============================================================================
-- 4. USAGE (run manually to populate immediately)
-- ============================================================================

-- CALL refresh_mv_daily_mood();


-- ============================================================================
-- PERFORMANCE COMPARISON (for report – Kriterium 5)
-- ============================================================================

-- BEFORE optimization: query aggregates over all raw MOOD_SCORE rows every time
-- EXPLAIN SELECT c.name, DATE(ms.timestamp), AVG(ms.mood_score)
--         FROM MOOD_SCORE ms JOIN CITY c ON ms.city_id = c.city_id
--         GROUP BY ms.city_id, DATE(ms.timestamp);

-- AFTER optimization: reads from pre-computed mv_daily_mood (single row per city/day)
-- EXPLAIN SELECT c.name, m.date, m.avg_mood
--         FROM mv_daily_mood m JOIN CITY c ON m.city_id = c.city_id
--         ORDER BY m.date DESC;
