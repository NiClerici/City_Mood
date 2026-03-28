-- Mood City Database Schema
-- Initialize database with all tables and city data

USE mood_city;

-- ============================================================================
-- 1. CITY TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS CITY (
    city_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert Swiss cities
INSERT IGNORE INTO CITY (name, latitude, longitude) VALUES
('Zürich', 47.3769, 8.5417),
('Luzern', 47.0502, 8.3093),
('Lausanne', 46.5197, 6.6323),
('Bern', 46.9480, 7.4474),
('Basel', 47.5596, 7.5886),
('Aarau', 47.3925, 8.0442),
('Genf', 46.2044, 6.1432),
('Locarno', 46.1690, 8.7995),
('Visp', 46.2937, 7.8815),
('Alpnach', 46.9431, 8.2726);


-- ============================================================================
-- 2. WEATHER TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS WEATHER (
    weather_id INT AUTO_INCREMENT PRIMARY KEY,
    city_id INT NOT NULL,
    timestamp DATETIME NOT NULL,
    weathercode INT NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES CITY(city_id),
    INDEX idx_city_timestamp (city_id, timestamp)
);


-- ============================================================================
-- 3. TRAFFIC TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS TRAFFIC (
    traffic_id INT AUTO_INCREMENT PRIMARY KEY,
    city_id INT NOT NULL,
    timestamp DATETIME NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    current_speed FLOAT NOT NULL,
    free_flow_speed FLOAT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES CITY(city_id),
    INDEX idx_city_timestamp (city_id, timestamp)
);


-- ============================================================================
-- 4. SBB TABLE (Zugverspätung)
-- ============================================================================

CREATE TABLE IF NOT EXISTS SBB (
    sbb_id INT AUTO_INCREMENT PRIMARY KEY,
    city_id INT NOT NULL,
    timestamp DATETIME NOT NULL,
    delay_minutes INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES CITY(city_id),
    INDEX idx_city_timestamp (city_id, timestamp)
);


-- ============================================================================
-- 5. MOOD_SCORE TABLE (berechnete Scores)
-- ============================================================================

CREATE TABLE IF NOT EXISTS MOOD_SCORE (
    score_id INT AUTO_INCREMENT PRIMARY KEY,
    city_id INT NOT NULL,
    timestamp DATETIME NOT NULL,
    weather_score FLOAT,
    sbb_score FLOAT,
    traffic_score FLOAT,
    mood_score FLOAT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES CITY(city_id),
    INDEX idx_city_timestamp (city_id, timestamp)
);

-- ============================================================================
-- INDEXES für Performance
-- ============================================================================

CREATE INDEX idx_weather_city ON WEATHER(city_id);
CREATE INDEX idx_traffic_city ON TRAFFIC(city_id);
CREATE INDEX idx_sbb_city ON SBB(city_id);
CREATE INDEX idx_mood_city ON MOOD_SCORE(city_id);
CREATE INDEX idx_mood_timestamp ON MOOD_SCORE(timestamp);
