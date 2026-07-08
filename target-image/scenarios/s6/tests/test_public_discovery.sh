#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DISCOVERY="$ROOT/app/controllers/discovery_controller.rb"

[ -f "$DISCOVERY" ] || { echo "[FAIL] missing $DISCOVERY"; exit 1; }

for route in '"/"' '"/status"' '"/help"' '"/about"' '"/api"'; do
  grep -Fq "$route" "$ROOT/config/routes.rb" || { echo "[FAIL] missing route $route"; exit 1; }
done

for text in "ContentHub" "service_areas" "authentication" "content" "operations"; do
  grep -Fq "$text" "$DISCOVERY" || { echo "[FAIL] missing discovery copy: $text"; exit 1; }
done

for leak in "flag_" "FLAG_" "/admin/settings" "/debug/runtime" "/profile/vault" "/profile/token" "SQL" "MD5" "brute"; do
  if grep -Fq "$leak" "$DISCOVERY"; then
    echo "[FAIL] discovery source leaks: $leak"
    exit 1
  fi
done

if [ -n "${BASE_URL:-}" ]; then
  for endpoint in / /status /help /about /api; do
    curl -fsS "$BASE_URL$endpoint" >/dev/null
  done
fi

echo "[PASS] S6 public discovery surfaces are present and non-spoiling."
