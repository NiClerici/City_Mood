-- Stored Procedure: Calculates mood scores from raw data

USE mood_city;
DELIMITER //

CREATE PROCEDURE IF NOT EXISTS calculate_mood_scores(
    IN p_city_id INT,
    IN p_timestamp DATETIME
)
BEGIN
    INSERT INTO MOOD_SCORE (city_id, timestamp, weather_score, sbb_score, traffic_score, mood_score)
    SELECT 
        p_city_id, p_timestamp,
        GREATEST(0, LEAST(1, 1 - (w.weathercode / 100.0))),
        GREATEST(0, LEAST(1, 1 - (s.delay_minutes * 3 / 300.0))),
        GREATEST(0, LEAST(1, t.current_speed / NULLIF(t.free_flow_speed, 0))),
        GREATEST(0, LEAST(1,
            0.4 * GREATEST(0, LEAST(1, 1 - (w.weathercode / 100.0))) +
            0.3 * GREATEST(0, LEAST(1, 1 - (s.delay_minutes * 3 / 300.0))) +
            0.3 * GREATEST(0, LEAST(1, t.current_speed / NULLIF(t.free_flow_speed, 0)))
        ))
    FROM WEATHER w
    JOIN SBB s USING (city_id, timestamp)
    JOIN TRAFFIC t USING (city_id, timestamp)
    WHERE w.city_id = p_city_id AND w.timestamp = p_timestamp
    LIMIT 1;
END//

DELIMITER ;
