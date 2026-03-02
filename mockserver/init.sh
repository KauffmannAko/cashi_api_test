#!/bin/sh
set -eu

echo "[mockserver-init] Waiting for MockServer to be ready..."
max_attempts=60
attempt=1

until wget -qO- http://localhost:1080/mockserver/status >/dev/null 2>&1; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "[mockserver-init] MockServer did not become ready in time"
    exit 1
  fi
  attempt=$((attempt + 1))
  sleep 1
done

echo "[mockserver-init] Seeding expectations..."
for expectation in /config/expectations/*.json; do
  echo "[mockserver-init] Loading ${expectation}"
  wget -qO- \
    --method=PUT \
    --header="Content-Type: application/json" \
    --body-file="${expectation}" \
    http://localhost:1080/mockserver/expectation >/dev/null 2>&1
done

echo "[mockserver-init] Expectations loaded"
