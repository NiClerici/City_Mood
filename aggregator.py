"""
Mood City Aggregator v2
Sammelt Wetter-, Verspätungs- und Verkehrsdaten für Schweizer Städte
und speichert diese mit berechneten Mood-Scores in MySQL.

Lädt alle 30 Minuten neu über APScheduler.
"""

import json
import sys
import time
from datetime import datetime
from typing import Optional

import requests
import mysql.connector
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import *

def get_db_connection():
    """Get MySQL connection."""
    return mysql.connector.connect(**DB_CONFIG)

def get_city_id(conn, city_name: str) -> Optional[int]:
    """Get city_id from CITY table."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT city_id FROM CITY WHERE name = %s", (city_name,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()

def insert_weather(conn, city_id: int, timestamp: str, weathercode: int, lat: float, lon: float):
    """Insert weather data."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO WEATHER (city_id, timestamp, weathercode, latitude, longitude) VALUES (%s, %s, %s, %s, %s)",
            (city_id, timestamp, weathercode, lat, lon)
        )
        conn.commit()
    finally:
        cursor.close()

def insert_traffic(conn, city_id: int, timestamp: str, lat: float, lon: float, current_speed: float, free_speed: float):
    """Insert traffic data."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO TRAFFIC (city_id, timestamp, latitude, longitude, current_speed, free_flow_speed) VALUES (%s, %s, %s, %s, %s, %s)",
            (city_id, timestamp, lat, lon, current_speed, free_speed)
        )
        conn.commit()
    finally:
        cursor.close()

def insert_sbb(conn, city_id: int, timestamp: str, delay_minutes: int):
    """Insert SBB delay data."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO SBB (city_id, timestamp, delay_minutes) VALUES (%s, %s, %s)",
            (city_id, timestamp, delay_minutes)
        )
        conn.commit()
    finally:
        cursor.close()

# ============================================================================

def calculate_and_store_mood_scores(conn, city_id: int, timestamp: str):
    """Call MySQL stored procedure to calculate mood scores."""
    cursor = conn.cursor()
    try:
        cursor.callproc('calculate_mood_scores', (city_id, timestamp))
        conn.commit()
    finally:
        cursor.close()

# 1. WEATHER API (Open-Meteo)

def fetch_weather(lat: float, lon: float, city: str) -> Optional[dict]:
    """Fetch weather data from Open-Meteo API."""
    try:
        params = {"latitude": lat,"longitude": lon,"current_weather": True}
        r = requests.get(WEATHER_URL, params=params, timeout=REQUEST_TIMEOUT)
        
        if r.status_code != 200:
            return None
        
        current = r.json().get("current_weather", {})
        
        weather_code = current.get("weathercode")
        time_str = data.get("time", "")
        
        if weather_code is None:
            return None
        
        return {
            "lat": round(lat, 4),"lon": round(lon, 4),"time": time_str,"weathercode": weather_code,"city": city
        }
    
    except Exception as e:
        return None

# 2. SBB DELAY API (transport.opendata.ch)

def fetch_sbb_delay(city: str) -> Optional[dict]:
    """Fetch SBB delay data."""
    sbb_city = CITIES_SBB.get(city)
    if not sbb_city:
        return None
    
    try:
        params = {
            "station": sbb_city,
            "limit": 50
        }
        r = requests.get(SBB_URL, params=params, timeout=REQUEST_TIMEOUT)
        
        if r.status_code != 200:
            return None
        
        stationboard = r.json().get("stationboard", [])
        
        delay_count = 0
        for row in stationboard:
            stop = row.get("stop", {})
            delay = stop.get("delay", 0)
            
            if not delay:
                prog = stop.get("prognosis") or {}
                delay = prog.get("delay", 0)
            
            if delay and delay > 0:
                delay_count += 1
        
        return {
            "city": city,"delay": delay_count
        }
    
    except Exception as e:
        return None


# 3. TRAFFIC API (TomTom Flow Segment)

def fetch_traffic(lat: float, lon: float, city: str) -> Optional[dict]:
    """Fetch traffic data from TomTom Flow Segment API."""
    try:
        params = {
            "key": TOMTOM_API_KEY,
            "point": f"{lat},{lon}",
            "unit": "kmph"
        }
        r = requests.get(TRAFFIC_URL, params=params, timeout=REQUEST_TIMEOUT)
        
        if r.status_code != 200:
            return None
        
        flow_segment = r.json().get("flowSegmentData", {})
        
        current_speed = flow_segment.get("currentSpeed")
        free_flow_speed = flow_segment.get("freeFlowSpeed")
        
        if current_speed is None or free_flow_speed is None:
            print(f"⚠️ Traffic API missing data for {city}", file=sys.stderr)
            return None
        
        return {
            "lat": round(lat, 4),
            "lon": round(lon, 4),
            "currentSpeed": float(current_speed),
            "freeFlowSpeed": float(free_flow_speed),
            "city": city
        }
    
    except Exception as e:
        return None

# AGGREGATION & DATA INGESTION

def aggregate_and_store_city(db_conn, city: str, lat: float, lon: float) -> dict:
    """
    Aggregate all 3 API calls for a single city and store in DB.
    Returns result dict with all data and scores.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get city_id
    city_id = get_city_id(db_conn, city)
    if not city_id:
        return {"city": city, "error": "city_not_found"}
    
    # Fetch all 3 APIs
    weather_data = fetch_weather(lat, lon, city)
    sbb_data = fetch_sbb_delay(city)
    traffic_data = fetch_traffic(lat, lon, city)
    
    time.sleep(SLEEP_BETWEEN_CALLS)
    
    # Insert raw data into DB
    if weather_data:
        insert_weather(db_conn, city_id, timestamp, weather_data["weathercode"], weather_data["lat"], weather_data["lon"])
    
    if sbb_data:
        insert_sbb(db_conn, city_id, timestamp, sbb_data["delay"])
    
    if traffic_data:
        insert_traffic(db_conn, city_id, timestamp, traffic_data["lat"], traffic_data["lon"], 
                      traffic_data["currentSpeed"], traffic_data["freeFlowSpeed"])
    
    # Calculate mood scores in MySQL
    if weather_data and sbb_data and traffic_data:
        calculate_and_store_mood_scores(db_conn, city_id, timestamp)
    
    return {
        "city": city,
        "timestamp": timestamp,
        "weather": weather_data,
        "sbb_delay": sbb_data,
        "traffic": traffic_data
    }


def run_aggregation():
    """Run full aggregation cycle for all cities."""
    print(f"\n{'='*80}", file=sys.stderr)
    print(f"🔄 Running aggregation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
    print(f"{'='*80}", file=sys.stderr)
    
    try:
        db_conn = get_db_connection()
        results = []
        
        for city, (lat, lon) in CITIES.items():
            print(f"  📍 Processing {city}...", file=sys.stderr)
            result = aggregate_and_store_city(db_conn, city, lat, lon)
            results.append(result)
        
        db_conn.close()
        
        print(f"✅ Aggregation complete!\n", file=sys.stderr)
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        
    except mysql.connector.Error as e:
        print (e, file=sys.stderr)
    except Exception as e:
        print(e, file=sys.stderr)

# SCHEDULER & MAIN

def main():
    """Initialize scheduler and run aggregation every 30 minutes."""
    print(f"🚀 Mood City Aggregator v2 started", file=sys.stderr)
    print(f"   Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}", file=sys.stderr)
    print(f"   Schedule: Every {SCHEDULE_INTERVAL_MINUTES} minutes", file=sys.stderr)
    print(f"   Cities: {len(CITIES)}", file=sys.stderr)
    
    # Create scheduler
    scheduler = BackgroundScheduler()
    
    # Add job: run aggregation every 30 minutes
    scheduler.add_job(
        run_aggregation,
        trigger=IntervalTrigger(minutes=SCHEDULE_INTERVAL_MINUTES),
        id='aggregation_job',
        name='Mood City Aggregation',
        replace_existing=True
    )
    
    # Start scheduler
    scheduler.start()
    
    print(f"✅ Scheduler started\n", file=sys.stderr)
    
    # Run once immediately on startup
    print(f"📊 Running initial aggregation...\n", file=sys.stderr)
    run_aggregation()
    
    # Keep application running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print(f"\n⏹️ Shutting down...", file=sys.stderr)
        scheduler.shutdown()
        print(f"✅ Scheduler stopped", file=sys.stderr)


if __name__ == "__main__":
    main()
