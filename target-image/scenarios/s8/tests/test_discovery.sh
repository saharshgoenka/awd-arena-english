#!/usr/bin/env bash
# S8/GridPulse discovery-surface smoke test.
#
# Manual use:
#   cd target-image/scenarios/s8
#   docker build -t gridpulse-s8 .
#   docker run -d --rm --name gridpulse-discovery -p 3000:3000 gridpulse-s8
#   bash tests/test_discovery.sh
#   docker rm -f gridpulse-discovery
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

grep -q "GridPulse" "$TMP_DIR/home.html"
grep -q "Operations API" "$TMP_DIR/api.json"
grep -q "meters" "$TMP_DIR/api.json"
grep -q "bearer" "$TMP_DIR/api.json"
grep -q '"status":"ok"' "$TMP_DIR/status.json"

if grep -R -E 'FLAG[{]|gridpulse-admin-2024|operator789|view123|/debug/vars|/admin/settings|/profile/vault' "$TMP_DIR"; then
  echo "[FAIL] discovery surface leaked sensitive implementation details"
  exit 1
fi

echo "[PASS] S8 discovery surfaces are reachable and non-spoiling."
