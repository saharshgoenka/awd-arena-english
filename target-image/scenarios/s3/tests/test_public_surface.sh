#!/usr/bin/env bash
# Lightweight source smoke test for public, non-secret discovery affordances.
set -euo pipefail

APP="${APP:-app.js}"

need_route() {
  local route="$1"
  grep -F "app.get('$route'" "$APP" >/dev/null || {
    echo "[FAIL] Missing public route: $route"
    exit 1
  }
}

need_text() {
  local text="$1"
  grep -F "$text" "$APP" >/dev/null || {
    echo "[FAIL] Missing public surface text: $text"
    exit 1
  }
}

need_route "/"
need_route "/about"
need_route "/help"
need_route "/status"
need_route "/api"
need_route "/api/docs"

need_text "TaskFlow"
need_text "API discovery"
need_text "Task search"

if [ "${RUN_LIVE:-0}" = "1" ]; then
  BASE_URL="${BASE_URL:-http://localhost:3000}"
  for path in / /about /help /status /api /api/docs; do
    body="$(curl -fsS "$BASE_URL$path")"
    if printf '%s' "$body" | grep -E 'FLAG\{|FLAG_[0-9]|TaskFlow2025!|shipit7' >/dev/null; then
      echo "[FAIL] Public route leaked sensitive training material: $path"
      exit 1
    fi
  done
fi

echo "[PASS] S3 public discovery surface is present."
