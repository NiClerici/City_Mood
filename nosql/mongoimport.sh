#!/usr/bin/env bash
# ============================================================
# mongoimport.sh  –  Load raw MySQL exports into MongoDB
#
# Prerequisites:
#   1. Run export_mysql_to_json.py first
#   2. MongoDB running and accessible
#   3. mongoimport installed (mongodb-database-tools)
#
# Usage:
#   bash mongoimport.sh [--host HOST] [--port PORT] [--db DB]
#                       [--user USER] [--password PASS]
#
# Defaults match the .env defaults of the project.
# ============================================================

MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-city_mood}"
MONGO_USER="${MONGO_USER:-}"
MONGO_PASS="${MONGO_PASS:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Build auth flags only when credentials are set
AUTH_FLAGS=""
if [ -n "$MONGO_USER" ] && [ -n "$MONGO_PASS" ]; then
    AUTH_FLAGS="--username $MONGO_USER --password $MONGO_PASS --authenticationDatabase admin"
fi

BASE_FLAGS="--host $MONGO_HOST --port $MONGO_PORT --db $MONGO_DB $AUTH_FLAGS --jsonArray --drop"

echo "=========================================="
echo "  mongoimport  →  $MONGO_DB @ $MONGO_HOST:$MONGO_PORT"
echo "=========================================="

import_collection() {
    local COLLECTION=$1
    local FILE="$SCRIPT_DIR/$2"

    if [ ! -f "$FILE" ]; then
        echo "  [SKIP] $FILE not found – run export_mysql_to_json.py first"
        return 1
    fi

    echo -n "  Importing $COLLECTION ... "
    mongoimport $BASE_FLAGS \
        --collection "$COLLECTION" \
        --file "$FILE"
}

import_collection "cities"      "cities.json"
import_collection "weather"     "weather.json"
import_collection "sbb"         "sbb.json"
import_collection "traffic"     "traffic.json"
import_collection "mood_scores" "mood_scores.json"

echo ""
echo "Import complete. Run mongo_transform_pipeline.js next:"
echo "  mongosh $MONGO_DB mongo_transform_pipeline.js"
