#!/usr/bin/env python3
"""
Local Standalone Test for Mood City Aggregator
Tests API calls and scoring without any database
"""

import json
import sys
import time
from datetime import datetime
from typing import Dict, Tuple, Optional

import requests


# ============================================================================
# CONFIG
# ============================================================================

CITIES: Dict[str, Tuple[float, float]] = {
    "Zürich": (47.3769, 8.5417),
    "Luzern": (47.0502, 8.3093),
    "Lausanne": (46.5197, 6.6323),
    "Bern": (46.9480, 7.4474),
    "Basel": (47.5596, 7.5886),
}

CITIES_SBB = {
    "Zürich": "Zuerich HB",
    "Luzern": "Luzern",
    "Lausanne": "Lausanne",
    "Bern": "Bern",
    "Basel": "Basel SBB",
}

TOMTOM_API_KEY = "DrcD6yGnXculh2SBJtSCIXHBUKr13wE0"

# ============================================================================
# SCORING FUNCTIONS
# ============================================================================

def calculate_weather_score(weathercode: int) -> float:
    """Calculate weather score from WMO weather code."""
    return max(0.0, min(1.0, 1.0 - (weathercode / 100.0)))

def calculate_sbb_score(delay_count: int) -> float:
    """Calculate SBB score from delay count."""
    estimated_total_delay = delay_count * 3
    return max(0.0, min(1.0, 1.0 - (estimated_total_delay / 300.0)))

def calculate_traffic_score(current_speed: float, free_flow_speed: float) -> float:
    """Calculate traffic score from speed ratio."""
    if free_flow_speed == 0:
        return 0.5
    ratio = current_speed / free_flow_speed
    return max(0.0, min(1.0, ratio))

def calculate_mood_score(weather_score: float, sbb_score: float, traffic_score: float) -> float:
    """Calculate combined mood score: 0.4*weather + 0.3*sbb + 0.3*traffic"""
    mood = (0.4 * weather_score) + (0.3 * sbb_score) + (0.3 * traffic_score)
    return max(0.0, min(1.0, mood))

# ============================================================================
# API FUNCTIONS
# ============================================================================

def fetch_weather(lat: float, lon: float, city: str) -> Optional[dict]:
    """Fetch weather from Open-Meteo."""
    try:
        params = {"latitude": lat, "longitude": lon, "current_weather": True}
        r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
        
        if r.status_code != 200:
            return None
        
        data = r.json()
        current = data.get("current_weather", {})
        weather_code = current.get("weathercode")
        
        if weather_code is None:
            return None
        
        return {
            "lat": round(lat, 4),
            "lon": round(lon, 4),
            "time": current.get("time", ""),
            "weathercode": weather_code,
            "city": city
        }
    except Exception as e:
        print(f"  ❌ Weather API error: {e}", file=sys.stderr)
        return None

def fetch_sbb_delay(city: str) -> Optional[dict]:
    """Fetch SBB delays."""
    sbb_city = CITIES_SBB.get(city)
    if not sbb_city:
        return None
    
    try:
        params = {"station": sbb_city, "limit": 50}
        r = requests.get("https://transport.opendata.ch/v1/stationboard", params=params, timeout=10)
        
        if r.status_code != 200:
            return None
        
        data = r.json()
        stationboard = data.get("stationboard", [])
        
        delay_count = 0
        for row in stationboard:
            stop = row.get("stop", {})
            delay = stop.get("delay", 0)
            if not delay:
                prog = stop.get("prognosis") or {}
                delay = prog.get("delay", 0)
            if delay and delay > 0:
                delay_count += 1
        
        return {"city": city, "delay": delay_count}
    except Exception as e:
        print(f"  ❌ SBB API error: {e}", file=sys.stderr)
        return None

def fetch_traffic(lat: float, lon: float, city: str) -> Optional[dict]:
    """Fetch traffic from TomTom."""
    try:
        params = {
            "key": TOMTOM_API_KEY,
            "point": f"{lat},{lon}",
            "unit": "kmph"
        }
        r = requests.get("https://api.tomtom.com/traffic/services/4/flowSegmentData/relative/12/json", 
                        params=params, timeout=10)
        
        if r.status_code != 200:
            return None
        
        data = r.json()
        flow_segment = data.get("flowSegmentData", {})
        
        current_speed = flow_segment.get("currentSpeed")
        free_flow_speed = flow_segment.get("freeFlowSpeed")
        
        if current_speed is None or free_flow_speed is None:
            return None
        
        return {
            "lat": round(lat, 4),
            "lon": round(lon, 4),
            "currentSpeed": float(current_speed),
            "freeFlowSpeed": float(free_flow_speed),
            "city": city
        }
    except Exception as e:
        print(f"  ❌ Traffic API error: {e}", file=sys.stderr)
        return None

# ============================================================================
# MAIN TEST
# ============================================================================

def run_test():
    """Run local test."""
    print(f"\n{'='*80}", file=sys.stderr)
    print(f"🧪 LOCAL TEST: Mood City Scoring & APIs", file=sys.stderr)
    print(f"{'='*80}\n", file=sys.stderr)
    
    results = []
    
    for city, (lat, lon) in list(CITIES.items())[:2]:  # Test first 2 cities
        print(f"  📍 {city}...", file=sys.stderr)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        weather = fetch_weather(lat, lon, city)
        sbb = fetch_sbb_delay(city)
        traffic = fetch_traffic(lat, lon, city)
        
        w_score = calculate_weather_score(weather["weathercode"]) if weather else None
        s_score = calculate_sbb_score(sbb["delay"]) if sbb else None
        t_score = calculate_traffic_score(traffic["currentSpeed"], traffic["freeFlowSpeed"]) if traffic else None
        m_score = calculate_mood_score(w_score, s_score, t_score) if all(s is not None for s in [w_score, s_score, t_score]) else None
        
        result = {
            "city": city,
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
    
    print(f"\n✅ Test complete!\n", file=sys.stderr)
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    run_test()
