#!/usr/bin/env bash
# S6/Rails ContentHub — pre/post-patch smoke test
#
# Usage:
#   SCENARIO_DIR=$(cd "$(dirname "$0")/.." && pwd)
#   docker build -t contenthub-s6 "$SCENARIO_DIR"
#   docker run -d --name contenthub-test \
#     -e FLAG_1=FLAG{11111111111111111111111111111111} \
#     -e FLAG_2=FLAG{22222222222222222222222222222222} \
#     -e FLAG_3=FLAG{33333333333333333333333333333333} \
#     -e FLAG_4=FLAG{44444444444444444444444444444444} \
#     -e FLAG_5=FLAG{55555555555555555555555555555555} \
#     -p 3000:3000 contenthub-s6
#   bash tests/test_flags.sh
#   docker rm -f contenthub-test
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCENARIO_DIR="$(dirname "$SCRIPT_DIR")"

BASE_URL="${BASE_URL:-http://localhost:3000}"
ORACLE="${ORACLE:-$SCENARIO_DIR/oracle_exploit.py}"
REFEREE_URL="${REFEREE_URL:-http://localhost:9999}"
MATCH_ID="${MATCH_ID:-test}"
CONTAINER="${CONTAINER:-contenthub-test}"
TARGET_PORT="${TARGET_PORT:-3000}"

echo "[test] Waiting for /health..."
for i in $(seq 1 30); do
  if curl -sf "$BASE_URL/health" | grep -q '"ok"'; then
    echo "[test] App is up."
    break
  fi
  sleep 4
done

echo "[test] === Phase 1: unpatched — expecting 5/5 ==="
OUTPUT=$(python3 "$ORACLE" \
  --target-host "${TARGET_HOST:-localhost}" \
  --target-port "$TARGET_PORT" \
  --referee-url "$REFEREE_URL" \
  --match-id "$MATCH_ID" \
  --attacker-id 0 \
  --victim-id 1 \
  --budget-seconds 120 2>&1 || true)
echo "$OUTPUT"

CAPTURED=$(echo "$OUTPUT" | python3 -c "
import json, sys, re
lines = sys.stdin.read()
start = lines.rfind('{\n  \"flags_captured\"')
print(len(json.loads(lines[start:]).get('flags_captured', [])) if start != -1 else 0)
")
[ "$CAPTURED" -eq 5 ] || { echo "[FAIL] Expected 5, got $CAPTURED"; exit 1; }
echo "[PASS] Unpatched: $CAPTURED/5 captured."

echo "[test] Applying oracle_patch.diff..."
docker exec -i "$CONTAINER" bash -c "cd /app && patch -p1" < "$SCENARIO_DIR/oracle_patch.diff"

echo "[test] Restarting app..."
docker exec "$CONTAINER" supervisorctl restart app
sleep 10

echo "[test] Waiting for /health after restart..."
for i in $(seq 1 20); do
  curl -sf "$BASE_URL/health" | grep -q '"ok"' && break || sleep 3
done

echo "[test] === Phase 2: patched — expecting 0/5 ==="
OUTPUT=$(python3 "$ORACLE" \
  --target-host "${TARGET_HOST:-localhost}" \
  --target-port "$TARGET_PORT" \
  --referee-url "$REFEREE_URL" \
  --match-id "$MATCH_ID" \
  --attacker-id 0 \
  --victim-id 1 \
  --budget-seconds 120 2>&1 || true)
echo "$OUTPUT"

CAPTURED=$(echo "$OUTPUT" | python3 -c "
import json, sys, re
lines = sys.stdin.read()
start = lines.rfind('{\n  \"flags_captured\"')
print(len(json.loads(lines[start:]).get('flags_captured', [])) if start != -1 else 0)
")
[ "$CAPTURED" -eq 0 ] || { echo "[FAIL] Expected 0, got $CAPTURED"; exit 1; }
echo "[PASS] Patched: $CAPTURED/5 captured."

echo "[test] Verifying /debug/runtime is removed..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/debug/runtime")
[ "$STATUS" != "200" ] || { echo "[FAIL] /debug/runtime still returns 200 after patch"; exit 1; }
echo "[PASS] /debug/runtime returns $STATUS (not 200)."

echo "[test] Verifying patched editor still logs in and cannot use alg:none admin token..."
COOKIE_JAR=$(mktemp)
RESP=$(curl -sf -c "$COOKIE_JAR" -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"editor","password":"editor456"}' || echo "failed")
echo "$RESP" | grep -q "Login successful" || { echo "[FAIL] Patched editor login failed"; exit 1; }
TOKEN=$(python3 - <<'PY' "$RESP"
import base64, json, sys
real = json.loads(sys.argv[1]).get("token", "")
try:
    claims = json.loads(base64.urlsafe_b64decode(real.split(".")[1] + "=" * (-len(real.split(".")[1]) % 4)))
except Exception:
    claims = {"username": "editor"}
claims["role"] = "admin"
def enc(obj):
    return base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode()).rstrip(b"=").decode()
print(f"{enc({'alg':'none','typ':'JWT'})}.{enc(claims)}.")
PY
)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -b "$COOKIE_JAR" -H "Authorization: Bearer $TOKEN" "$BASE_URL/admin/analytics")
[ "$STATUS" != "200" ] || { echo "[FAIL] Expected forged alg:none token to fail, got $STATUS"; exit 1; }
echo "[PASS] Patched alg:none admin token returns $STATUS (not 200)."

echo "[test] Verifying patched BOLA owner check blocks cross-user report reads..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -b "$COOKIE_JAR" "$BASE_URL/reports/4021")
rm -f "$COOKIE_JAR"
[ "$STATUS" = "404" ] || { echo "[FAIL] Expected editor /reports/4021 to return 404, got $STATUS"; exit 1; }
echo "[PASS] Patched editor cannot read admin escalation report."

echo "[PASS] All tests passed."
