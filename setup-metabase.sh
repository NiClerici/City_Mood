#!/bin/sh
set -eu

echo "⏳ Metabase init: waiting for health endpoint..."
for i in $(seq 1 40); do
  if curl -fsS http://metabase:3000/api/health >/dev/null 2>&1; then
    echo "✅ Metabase is healthy. No automated setup configured; skipping."
    exit 0
  fi
  sleep 5
done

echo "⚠️ Metabase did not become healthy in time; skipping init step."
exit 0
