#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/src/main/java/com/finledger/controller/DiscoveryController.java"

[ -f "$APP" ] || { echo "[FAIL] missing $APP"; exit 1; }

for mapping in '"/"' '"/status"' '"/help"' '"/about"' '"/api"'; do
  grep -Fq "$mapping" "$APP" || { echo "[FAIL] missing mapping $mapping"; exit 1; }
done

for text in "FinLedger" "serviceAreas" "authentication" "ledger" "operations"; do
  grep -Fq "$text" "$APP" || { echo "[FAIL] missing discovery copy: $text"; exit 1; }
done

for leak in "flag_" "FLAG_" "/api/admin/dashboard" "/actuator" "/api/ledger/secret" "SQL" "MD5" "brute"; do
  if grep -Fq "$leak" "$APP"; then
    echo "[FAIL] discovery source leaks: $leak"
    exit 1
  fi
done

if [ -n "${BASE_URL:-}" ]; then
  for endpoint in / /status /help /about /api; do
    curl -fsS "$BASE_URL$endpoint" >/dev/null
  done
fi

echo "[PASS] S5 public discovery surfaces are present and non-spoiling."
