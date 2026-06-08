USE mood_city;
DELIMITER //

CREATE PROCEDURE IF NOT EXISTS calculate_mood_scores(
    IN p_city_id   INT,
    IN p_timestamp DATETIME
)
BEGIN
    -- Lokale Variablen fuer die berechneten Scores
    DECLARE v_weather_score  FLOAT DEFAULT 0;
    DECLARE v_sbb_score      FLOAT DEFAULT 0;
    DECLARE v_traffic_score  FLOAT DEFAULT 0;
    DECLARE v_mood_score     FLOAT DEFAULT 0;
    DECLARE v_count          INT   DEFAULT 0;

    -- Pruefen ob Rohdaten fuer Stadt + Zeitpunkt vorhanden sind
    SELECT COUNT(*) INTO v_count
    FROM   WEATHER w
    JOIN   SBB     s USING (city_id, timestamp)
    JOIN   TRAFFIC t USING (city_id, timestamp)
    WHERE  w.city_id   = p_city_id
      AND  w.timestamp = p_timestamp;

    -- Nur berechnen wenn alle drei Datenquellen vorhanden sind
    IF v_count > 0 THEN

        SELECT
            GREATEST(0, LEAST(1, 1 - (w.weathercode / 100.0))),
            GREATEST(0, LEAST(1, 1 - (s.delay_minutes * 3 / 300.0))),
            GREATEST(0, LEAST(1, COALESCE(t.current_speed / NULLIF(t.free_flow_speed, 0), 0)))
        INTO v_weather_score, v_sbb_score, v_traffic_score
        FROM   WEATHER w
        JOIN   SBB     s USING (city_id, timestamp)
        JOIN   TRAFFIC t USING (city_id, timestamp)
        WHERE  w.city_id   = p_city_id
          AND  w.timestamp = p_timestamp
        LIMIT  1;

        -- Gewichteter Mood-Score
        SET v_mood_score = GREATEST(0, LEAST(1,
            0.4 * v_weather_score +
            0.3 * v_sbb_score     +
            0.3 * v_traffic_score
        ));

        -- Berechnete Scores speichern
        INSERT INTO MOOD_SCORE (city_id, timestamp, weather_score, sbb_score, traffic_score, mood_score)
        VALUES (p_city_id, p_timestamp, v_weather_score, v_sbb_score, v_traffic_score, v_mood_score);

    END IF;

END//

DELIMITER ;
