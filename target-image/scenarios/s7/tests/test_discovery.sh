#!/usr/bin/env bash
# S7/FleetView discovery-surface smoke test.
#
# Manual use:
#   cd target-image/scenarios/s7
#   docker build -t fleetview-s7 .
#   docker run -d --rm --name fleetview-discovery -p 3000:3000 fleetview-s7
#   bash tests/test_discovery.sh
#   docker rm -f fleetview-discovery
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3000}"

for i in $(seq 1 30); do
  if curl -sf "$BASE_URL/health" >/dev/null; then
    break
  fi
  sleep 1
done

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

curl -sf "$BASE_URL/" > "$TMP_DIR/home.html"
curl -sf "$BASE_URL/about" > "$TMP_DIR/about.html"
curl -sf "$BASE_URL/status" > "$TMP_DIR/status.json"
curl -sf "$BASE_URL/help" > "$TMP_DIR/help.html"
curl -sf "$BASE_URL/api" > "$TMP_DIR/api.json"

grep -q "FleetView" "$TMP_DIR/home.html"
grep -q "Operations API" "$TMP_DIR/api.json"
grep -q "vehicles" "$TMP_DIR/api.json"
grep -q "authentication" "$TMP_DIR/api.json"
grep -q '"status":"ok"' "$TMP_DIR/status.json"

grep -q "/exports/encrypted" "$TMP_DIR/api.json"
grep -q "Operational diagnostics are not listed" "$TMP_DIR/api.json"
grep -q "dispatcher / dispatch456" "$TMP_DIR/help.html"

if grep -q "/debug/env" "$TMP_DIR/api.json"; then
  echo "[FAIL] API discovery advertises the debug env path"
  exit 1
fi

if grep -R -E 'FLAG[{]|fleetadmin2024|fleet123' "$TMP_DIR"; then
  echo "[FAIL] discovery surface leaked sensitive implementation details"
  exit 1
fi

echo "[PASS] S7 assisted discovery surfaces are reachable and bounded."
