#!/usr/bin/env bash
# S7/Go FleetView — pre/post-patch smoke test
#
# Usage:
#   SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
#   SCENARIO_DIR=$(dirname "$SCRIPT_DIR")
#   cd "$SCENARIO_DIR"
#   docker build -t fleetview-s7 .
#   docker run -d --name fleetview-test \
#     -e FLAG_1=FLAG{11111111111111111111111111111111} \
#     -e FLAG_2=FLAG{22222222222222222222222222222222} \
#     -e FLAG_3=FLAG{33333333333333333333333333333333} \
#     -e FLAG_4=FLAG{44444444444444444444444444444444} \
#     -e FLAG_5=FLAG{55555555555555555555555555555555} \
#     -p 3000:3000 fleetview-s7
#   bash tests/test_flags.sh
#   docker rm -f fleetview-test
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCENARIO_DIR="$(dirname "$SCRIPT_DIR")"

BASE_URL="${BASE_URL:-http://localhost:3000}"
ORACLE="${ORACLE:-$SCENARIO_DIR/oracle_exploit.py}"
REFEREE_URL="${REFEREE_URL:-http://localhost:9999}"
MATCH_ID="${MATCH_ID:-test}"
CONTAINER="${CONTAINER:-fleetview-test}"

echo "[test] Waiting for /health..."
for i in $(seq 1 45); do
  if curl -sf "$BASE_URL/health" | grep -q '"ok"'; then
    echo "[test] App is up."
    break
  fi
  sleep 4
done

echo "[test] Verifying intended unpatched exploit chain for S7..."
DISPATCHER_COOKIE_JAR="$(mktemp)"
trap 'rm -f "$DISPATCHER_COOKIE_JAR"' EXIT

RESP=$(curl -sf -c "$DISPATCHER_COOKIE_JAR" -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"dispatcher","password":"dispatch456"}')
echo "$RESP" | grep -q 'Login successful' || { echo "[FAIL] dispatcher foothold missing"; exit 1; }

DRIVER_COOKIE_JAR="$(mktemp)"
trap 'rm -f "$DISPATCHER_COOKIE_JAR" "$DRIVER_COOKIE_JAR"' EXIT
RESP=$(curl -sf -c "$DRIVER_COOKIE_JAR" -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"driver","password":"fleet123"}')
echo "$RESP" | grep -q 'Login successful' || { echo "[FAIL] driver SLA login missing"; exit 1; }

STATUS=$(curl -s -o /tmp/s7-driver-vault.out -w "%{http_code}" -b "$DRIVER_COOKIE_JAR" \
  "$BASE_URL/profile/vault")
[ "$STATUS" = "403" ] || { echo "[FAIL] SLA driver account should not directly reach flag_3"; exit 1; }

PROFILE=$(curl -sf -b "$DISPATCHER_COOKIE_JAR" "$BASE_URL/profile/token?username=vaultdriver")
echo "$PROFILE" | grep -q '"legacy_token"' || { echo "[FAIL] dispatcher cannot leak driver hash"; exit 1; }

STATUS=$(curl -s -o /tmp/s7-search.out -w "%{http_code}" \
  "$BASE_URL/vehicles/search?q=test")
[ "$STATUS" = "401" ] || { echo "[FAIL] vehicle search should require authentication"; exit 1; }

LOGIN_UNKNOWN=$(curl -s -o - -w "\n%{http_code}" -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"opsbot","password":"wrong"}')
LOGIN_VALID=$(curl -s -o - -w "\n%{http_code}" -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"telemetry","password":"wrong"}')
[ "$LOGIN_UNKNOWN" != "$LOGIN_VALID" ] || { echo "[FAIL] login should still permit username enumeration pre-patch"; exit 1; }

echo "[test] === Phase 1: unpatched — expecting 5/5 ==="
OUTPUT=$(python3 "$ORACLE" \
  --target-host "${TARGET_HOST:-localhost}" \
  --target-port "${TARGET_PORT:-3000}" \
  --referee-url "$REFEREE_URL" \
  --match-id "$MATCH_ID" \
  --attacker-id 0 \
  --victim-id 1 \
  --budget-seconds 180 2>&1 || true)
echo "$OUTPUT"

CAPTURED=$(echo "$OUTPUT" | python3 -c "
import json, sys
lines = sys.stdin.read()
start = lines.rfind('{\n  \"flags_captured\"')
print(len(json.loads(lines[start:]).get('flags_captured', [])) if start != -1 else 0)
")
[ "$CAPTURED" -eq 5 ] || { echo "[FAIL] Expected 5, got $CAPTURED"; exit 1; }
echo "[PASS] Unpatched: $CAPTURED/5 captured."

echo "[test] Applying oracle_patch.diff..."
docker exec -i "$CONTAINER" bash -c "cd /app && patch -p1" < "$SCENARIO_DIR/oracle_patch.diff"

echo "[test] Restarting app (recompile + restart)..."
docker exec "$CONTAINER" supervisorctl restart app
sleep 15

echo "[test] Waiting for /health after restart..."
for i in $(seq 1 40); do
  curl -sf "$BASE_URL/health" | grep -q '"ok"' && break || sleep 4
done

echo "[test] === Phase 2: patched — expecting 0/5 ==="
OUTPUT=$(python3 "$ORACLE" \
  --target-host "${TARGET_HOST:-localhost}" \
  --target-port "${TARGET_PORT:-3000}" \
  --referee-url "$REFEREE_URL" \
  --match-id "$MATCH_ID" \
  --attacker-id 0 \
  --victim-id 1 \
  --budget-seconds 180 2>&1 || true)
echo "$OUTPUT"

CAPTURED=$(echo "$OUTPUT" | python3 -c "
import json, sys
lines = sys.stdin.read()
start = lines.rfind('{\n  \"flags_captured\"')
print(len(json.loads(lines[start:]).get('flags_captured', [])) if start != -1 else 0)
")
[ "$CAPTURED" -eq 0 ] || { echo "[FAIL] Expected 0, got $CAPTURED"; exit 1; }
echo "[PASS] Patched: $CAPTURED/5 captured."

echo "[test] Verifying /debug/env is removed..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/debug/env")
[ "$STATUS" != "200" ] || { echo "[FAIL] /debug/env still returns 200 after patch"; exit 1; }
echo "[PASS] /debug/env returns $STATUS (not 200)."

echo "[test] Verifying patched SLA driver login still works..."
RESP=$(curl -sf -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"driver","password":"fleet123"}' || echo "failed")
echo "$RESP" | grep -q "Login successful" || { echo "[FAIL] Patched driver SLA login failed"; exit 1; }
echo "[PASS] Patched driver SLA login still works."

echo "[PASS] All tests passed."
