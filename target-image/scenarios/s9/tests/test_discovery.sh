#!/usr/bin/env bash
# S9/VaultGate discovery-surface smoke test.
#
# Manual use:
#   cd target-image/scenarios/s9
#   docker build -t vaultgate-s9 .
#   docker run -d --rm --name vaultgate-discovery -p 3000:3000 vaultgate-s9
#   bash tests/test_discovery.sh
#   docker rm -f vaultgate-discovery
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

grep -q "VaultGate" "$TMP_DIR/home.html"
grep -q "Operations API" "$TMP_DIR/api.json"
grep -q "secrets" "$TMP_DIR/api.json"
grep -q "bearer" "$TMP_DIR/api.json"
grep -q '"status":"ok"' "$TMP_DIR/status.json"

if grep -R -E 'FLAG[{]|vaultadmin2024|password123|readonly789|/api/debug/config|/api/admin/keys|/api/secrets/vault|/api/secrets/private' "$TMP_DIR"; then
  echo "[FAIL] discovery surface leaked sensitive implementation details"
  exit 1
fi

echo "[PASS] S9 discovery surfaces are reachable and non-spoiling."
