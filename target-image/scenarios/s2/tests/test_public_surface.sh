#!/usr/bin/env bash
# Lightweight source smoke test for public, non-secret discovery affordances.
set -euo pipefail

VIEWS="${VIEWS:-hr/views.py}"
URLS="${URLS:-peopleops/urls.py}"

need_view() {
  local name="$1"
  grep -F "def $name(" "$VIEWS" >/dev/null || {
    echo "[FAIL] Missing view: $name"
    exit 1
  }
}

need_url() {
  local route="$1"
  grep -F "path(\"$route\"" "$URLS" >/dev/null || {
    echo "[FAIL] Missing public route: /$route"
    exit 1
  }
}

need_text() {
  local text="$1"
  grep -F "$text" "$VIEWS" >/dev/null || {
    echo "[FAIL] Missing public surface text: $text"
    exit 1
  }
}

need_view "home"
need_view "about"
need_view "help_page"
need_view "status_page"
need_view "api_discovery"

need_url ""
need_url "about/"
need_url "help/"
need_url "status/"
need_url "api/"

need_text "PeopleOps"
need_text "API discovery"
need_text "Employee search"

if [ "${RUN_LIVE:-0}" = "1" ]; then
  BASE_URL="${BASE_URL:-http://localhost:3000}"
  for path in / /about/ /help/ /status/ /api/; do
    body="$(curl -fsS "$BASE_URL$path")"
    if printf '%s' "$body" | grep -E 'FLAG\{|FLAG_[0-9]|hrmanager2024|StaffSpring25!|employee1!|sunrise7|wilsonsec99' >/dev/null; then
      echo "[FAIL] Public route leaked sensitive training material: $path"
      exit 1
    fi
  done
fi

echo "[PASS] S2 public discovery surface is present."
