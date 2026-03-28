import os

CITIES = {
    "Zürich": (47.3769, 8.5417),
    "Luzern": (47.0502, 8.3093),
    "Lausanne": (46.5197, 6.6323),
    "Bern": (46.9480, 7.4474),
    "Basel": (47.5596, 7.5886),
    "Aarau": (47.3925, 8.0442),
    "Genf": (46.2044, 6.1432),
    "Locarno": (46.1690, 8.7995),
    "Visp": (46.2937, 7.8815),
    "Alpnach": (46.9431, 8.2726),
}

CITIES_SBB = {
    "Zürich": "Zuerich HB",
    "Luzern": "Luzern",
    "Lausanne": "Lausanne",
    "Bern": "Bern",
    "Basel": "Basel SBB",
    "Aarau": "Aarau",
    "Genf": "Genf",
    "Locarno": "Locarno",
    "Visp": "Visp",
    "Alpnach": "Alpnach",
}

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
SBB_URL = "https://transport.opendata.ch/v1/stationboard"
TRAFFIC_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/relative/12/json"

TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "DrcD6yGnXculh2SBJtSCIXHBUKr13wE0")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "mood_user"),
    "password": os.getenv("DB_PASSWORD", "mood_password"),
    "database": os.getenv("DB_NAME", "mood_city"),
    "port": int(os.getenv("DB_PORT", 3306)),
}

REQUEST_TIMEOUT = 10
SLEEP_BETWEEN_CALLS = 0.1
SCHEDULE_INTERVAL_MINUTES = 30
