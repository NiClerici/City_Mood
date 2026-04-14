# Mood City - Docker Data Ingest System

**Ein System zum Aggregieren von Wetter-, Verkehrs- und SBB-Daten für Schweizer Städte mit automatischer Speicherung in MySQL alle 30 Minuten.**

## 📋 Überblick

Das System besteht aus:
- **Python Container**: Sammelt Daten von 3 APIs alle 30 Minuten und berechnet Mood-Scores
- **MySQL Container**: Speichert Rohdaten und berechnete Scores in einer Datenbank

**Scoring-Formel** (basierend auf Projektbericht):
```
weather_score = 1 - (weathercode / 100)           # 0-100 scale, lower code = better
sbb_score = max(0, 1 - (delay_count*3 / 300))     # Count of delayed trains
traffic_score = currentSpeed / freeFlowSpeed       # Speed ratio
mood_score = 0.4*weather + 0.3*sbb + 0.3*traffic  # Weighted average
```

## 🚀 Quick Start
Full Docker Setup

**Voraussetzungen:**
- Docker Desktop muss laufen (Start auf macOS/Windows)
- Docker Compose v5.0+ (kommt mit Docker Desktop)

**Starten:**
```bash
# Terminal öffnen

# .env anlegen und API-Key setzen
cp .env.example .env
# Danach TOMTOM_API_KEY in .env eintragen

# Docker Compose starten (baut Images, startet MySQL + Python)
docker compose up --build

# CTRL+C zum Stoppen
```

**Logs anschauen (in separatem Terminal):**
```bash
docker compose logs -f python    # Python-Logs
docker compose logs -f mysql     # MySQL-Logs
docker compose logs              # Alle Logs
```

**MySQL direkt abfragen:**
```bash
# In separatem Terminal
docker compose exec mysql mysql -u mood_user -pmood_password mood_city

# Im MySQL Prompt:
SELECT * FROM MOOD_SCORE ORDER BY timestamp DESC LIMIT 10;
SELECT * FROM CITY;
SELECT COUNT(*) FROM WEATHER;
```

## 📁 Datei-Struktur

```
City_Mood/
├── aggregator.py          # Hauptskript (APIs + Scoring + DB + Scheduler)
├── requirements.txt       # Python Dependencies
├── Dockerfile             # Python Container Image
├── docker-compose.yml     # 2 Services: MySQL + Python
├── init.sql               # DB-Schema + Init Skript
```

## 🗄️ Datenbank-Schema

### Tables

**CITY** (Städte)
```
city_id (INT PK)
name (VARCHAR)
latitude (FLOAT)
longitude (FLOAT)
```

**WEATHER** (Rohdaten)
```
weather_id (INT PK)
city_id (INT FK)
timestamp (DATETIME)
weathercode (INT)
latitude (FLOAT)
longitude (FLOAT)
```

**TRAFFIC** (Rohdaten)
```
traffic_id (INT PK)
city_id (INT FK)
timestamp (DATETIME)
latitude (FLOAT)
longitude (FLOAT)
current_speed (FLOAT)
free_flow_speed (FLOAT)
```

**SBB** (Rohdaten)
```
sbb_id (INT PK)
city_id (INT FK)
timestamp (DATETIME)
delay_minutes (INT)   # Count of delayed trains
```

**MOOD_SCORE** (Berechnete Werte)
```
score_id (INT PK)
city_id (INT FK)
timestamp (DATETIME)
weather_score (FLOAT)
sbb_score (FLOAT)
traffic_score (FLOAT)
mood_score (FLOAT)    # Final score [0-1]
```

## 📊 Beispiel-Output

```json
{
  "city": "Zürich",
  "timestamp": "2026-03-23 14:38:09",
  "weather": {
    "lat": 47.3769,
    "lon": 8.5417,
    "time": "2026-03-23T13:30",
    "weathercode": 3,
    "city": "Zürich"
  },
  "sbb_delay": {
    "city": "Zürich",
    "delay": 10        # 10 delayed trains
  },
  "traffic": {
    "lat": 47.3769,
    "lon": 8.5417,
    "currentSpeed": 20.0,
    "freeFlowSpeed": 20.0,
    "city": "Zürich"
  },
  "scores": {
    "weather_score": 0.97,
    "sbb_score": 0.9,
    "traffic_score": 1.0,
    "mood_score": 0.958   # ← Final Mood Score
  }
}
```

## ⚙️ Konfiguration

**Environment Variablen** (in `.env`):
```
TOMTOM_API_KEY=<dein-api-key>   # Pflicht
DB_HOST=mysql                   # optional (default)
DB_USER=mood_user               # optional (default)
DB_PASSWORD=mood_password       # optional (default)
DB_NAME=mood_city               # optional (default)
DB_PORT=3306                    # optional (default)
```

**Schedule:**
- Standard: Alle 30 Minuten (siehe `aggregator.py` Zeile `SCHEDULE_INTERVAL_MINUTES = 30`)
- Beim Start: Einmalige initiale Aggregation

## 🐛 Troubleshooting

### "Docker daemon is not running"
→ Docker Desktop starten (macOS/Windows)

### "MySQL takes too long to init"
→ Erste Start kann 30-60 Sekunden dauern, MySQL-Health-Check wartet
→ Logs mit `docker compose logs -f mysql` ansehen

### "Connection refused: localhost:3306"
→ MySQL Container ist nicht hochgefahren
→ `docker compose logs mysql` ansehen

### "No module named mysql.connector"
→ Im lokalen Test: `pip install mysql-connector-python` (in venv)
→ Im Docker Container: `requirements.txt` installiert es automatisch

### APIs liefern keine Daten
→ Check Network-Connection oder API-Limits
→ Logs mit `docker compose logs python` ansehen

## 🔍 Monitoring

**Daten abrufen nach jedem Run:**
```bash
# Letzte 10 Mood Scores pro Stadt
mysql> SELECT city_id, timestamp, mood_score FROM MOOD_SCORE 
        ORDER BY timestamp DESC LIMIT 10;

# Durchschnittlicher Mood Score pro Stadt
mysql> SELECT c.name, AVG(m.mood_score) as avg_mood
        FROM MOOD_SCORE m
        JOIN CITY c ON m.city_id = c.city_id
        GROUP BY c.name;

# Trending Score über Zeit
mysql> SELECT timestamp, mood_score FROM MOOD_SCORE 
        WHERE city_id = 4 
        ORDER BY timestamp DESC LIMIT 50;
```

## 📝 Entwicklung & Testing


### Vollständiger Cycle mit docker-compose:
```bash
docker compose up --build
# Warte 30 min oder prüfe Logs
docker compose logs python
```

### Container-Logs speichern:
```bash
docker compose logs > logs.txt
```

## 🚢 Production Deployment

Für Production:
1. Environment Variablen via `.env` Datei setzen (nicht hardcoded)
2. `docker-compose.yml` mit sensiblen Daten updaten
3. MySQL Persistenz: Volumes sind bereits configured (`mysql_data:/var/lib/mysql`)
4. Log-Rotation einrichten (z.B. via Docker logging driver)
5. Monitoring + Alerts für fehlgeschlagene Aggregationen

## 📄 Lizenz & Quellen

- **Open-Meteo**: Kostenlose Wetter-API (keine Authentifizierung nötig)
- **transport.opendata.ch**: Schweiz öffentliche Verkehrsdaten (Open Data)
- **TomTom Traffic**: Kommerzielles Datenquellen (API-Key erforderlich)

---

**Last Updated:** March 28, 2026
**Version:** 2.0 (Docker + MySQL + APScheduler)
