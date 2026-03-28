#!/usr/bin/env python3
"""
Local Test Script for Mood City Aggregator
Simulates database with in-memory storage
Used for quick testing without Docker/MySQL
"""

import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

# Simulate database with in-memory storage
class FakeDB:
    def __init__(self):
        self.cities = {
            1: {"city_id": 1, "name": "Zürich", "lat": 47.3769, "lon": 8.5417},
            2: {"city_id": 2, "name": "Luzern", "lat": 47.0502, "lon": 8.3093},
            3: {"city_id": 3, "name": "Lausanne", "lat": 46.5197, "lon": 6.6323},
            4: {"city_id": 4, "name": "Bern", "lat": 46.9480, "lon": 7.4474},
            5: {"city_id": 5, "name": "Basel", "lat": 47.5596, "lon": 7.5886},
        }
        self.weather = []
        self.traffic = []
        self.sbb = []
        self.mood_scores = []
    
    def insert_weather(self, city_id, timestamp, weathercode, lat, lon):
        self.weather.append({"city_id": city_id, "timestamp": timestamp, "weathercode": weathercode, "lat": lat, "lon": lon})
    
    def insert_traffic(self, city_id, timestamp, lat, lon, current_speed, free_speed):
        self.traffic.append({"city_id": city_id, "timestamp": timestamp, "lat": lat, "lon": lon, "current_speed": current_speed, "free_speed": free_speed})
    
    def insert_sbb(self, city_id, timestamp, delay_minutes):
        self.sbb.append({"city_id": city_id, "timestamp": timestamp, "delay_minutes": delay_minutes})
    
    def insert_mood_score(self, city_id, timestamp, w_score, s_score, t_score, m_score):
        self.mood_scores.append({"city_id": city_id, "timestamp": timestamp, "weather_score": w_score, "sbb_score": s_score, "traffic_score": t_score, "mood_score": m_score})

# Initialize fake DB
db = FakeDB()

# Import real API functions from aggregator
import sys
sys.path.insert(0, '/Users/nicoclerici/Documents/Studium/3.Sem HSLU/BDLS/City_Mood')
from aggregator import (
    fetch_weather, fetch_sbb_delay, fetch_traffic,
    calculate_weather_score, calculate_sbb_score, calculate_traffic_score, calculate_mood_score,
    CITIES
)

def run_local_test():
    """Run aggregation locally without Docker."""
    print(f"\n{'='*80}", file=sys.stderr)
    print(f"🧪 LOCAL TEST: Mood City Aggregator", file=sys.stderr)
    print(f"{'='*80}\n", file=sys.stderr)
    
    results = []
    
    for city_name, (lat, lon) in list(CITIES.items())[:3]:  # Test only first 3 cities
        print(f"📍 Testing {city_name}...", file=sys.stderr)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Fetch data
        weather = fetch_weather(lat, lon, city_name)
        sbb = fetch_sbb_delay(city_name)
        traffic = fetch_traffic(lat, lon, city_name)
        
        # Calculate scores
        w_score = calculate_weather_score(weather["weathercode"]) if weather else None
        s_score = calculate_sbb_score(sbb["delay"]) if sbb else None
        t_score = calculate_traffic_score(traffic["currentSpeed"], traffic["freeFlowSpeed"]) if traffic else None
        m_score = calculate_mood_score(w_score, s_score, t_score) if all(s is not None for s in [w_score, s_score, t_score]) else None
        
        result = {
            "city": city_name,
            "timestamp": timestamp,
            "weather": weather,
            "sbb_delay": sbb,
            "traffic": traffic,
            "scores": {
                "weather_score": round(w_score, 3) if w_score else None,
                "sbb_score": round(s_score, 3) if s_score else None,
                "traffic_score": round(t_score, 3) if t_score else None,
                "mood_score": round(m_score, 3) if m_score else None
            }
        }
        
        results.append(result)
        time.sleep(0.5)
    
    print(f"\n✅ Local test complete!\n", file=sys.stderr)
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))

if __name__ == "__main__":
    run_local_test()
