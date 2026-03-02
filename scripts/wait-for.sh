#!/usr/bin/env bash
set -euo pipefail

host="${1:?host required}"
port="${2:?port required}"
timeout_sec="${3:-60}"

start_ts="$(date +%s)"

echo "Waiting for ${host}:${port} (timeout ${timeout_sec}s)..."

while true; do
  if (echo > "/dev/tcp/${host}/${port}") >/dev/null 2>&1; then
    echo "${host}:${port} is available"
    exit 0
  fi

  now_ts="$(date +%s)"
  if (( now_ts - start_ts >= timeout_sec )); then
    echo "Timed out waiting for ${host}:${port}" >&2
    exit 1
  fi

  sleep 1
done
