"""
Export MySQL tables to JSON files for mongoimport.

Exports five collections:
  - cities.json       (from CITY)
  - weather.json      (from WEATHER)
  - sbb.json          (from SBB)
  - traffic.json      (from TRAFFIC)
  - mood_scores.json  (from MOOD_SCORE)

Run before mongoimport.sh:
  python3 export_mysql_to_json.py
"""

import json
import os
import sys
from datetime import datetime

import mysql.connector
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "user":     os.getenv("DB_USER",     "mood_user"),
    "password": os.getenv("DB_PASSWORD", "mood_password"),
    "database": os.getenv("DB_NAME",     "mood_city"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "use_pure": True,
}

OUTPUT_DIR = os.path.dirname(__file__)


def to_serializable(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value


def export_table(cursor, query, output_file):
    cursor.execute(query)
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    docs = []
    for row in rows:
        docs.append({col: to_serializable(val) for col, val in zip(columns, row)})
    path = os.path.join(OUTPUT_DIR, output_file)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    print(f"  Exported {len(docs):>6} documents → {output_file}")
    return len(docs)


def main():
    print("Connecting to MySQL...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        sys.exit(1)

    cursor = conn.cursor()
    print("Exporting tables:")

    export_table(cursor,
        "SELECT city_id, name, latitude, longitude, created_at FROM CITY ORDER BY city_id",
        "cities.json")

    export_table(cursor,
        "SELECT weather_id, city_id, timestamp, weathercode, latitude, longitude, created_at FROM WEATHER ORDER BY weather_id",
        "weather.json")

    export_table(cursor,
        "SELECT sbb_id, city_id, timestamp, delay_minutes, created_at FROM SBB ORDER BY sbb_id",
        "sbb.json")

    export_table(cursor,
        "SELECT traffic_id, city_id, timestamp, latitude, longitude, current_speed, free_flow_speed, created_at FROM TRAFFIC ORDER BY traffic_id",
        "traffic.json")

    export_table(cursor,
        "SELECT score_id, city_id, timestamp, weather_score, sbb_score, traffic_score, mood_score, created_at FROM MOOD_SCORE ORDER BY score_id",
        "mood_scores.json")

    cursor.close()
    conn.close()
    print("\nDone. Run mongoimport.sh next.")


if __name__ == "__main__":
    main()
