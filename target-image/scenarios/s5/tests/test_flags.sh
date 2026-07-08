#!/usr/bin/env bash
# S5/Spring Boot FinLedger — pre/post-patch smoke test
#
# Usage:
#   SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
#   SCENARIO_DIR=$(dirname "$SCRIPT_DIR")
#   cd "$SCENARIO_DIR"
#   docker build -t finledger-s5 .
#   docker run -d --name finledger-test \
#     -e FLAG_1=FLAG{11111111111111111111111111111111} \
#     -e FLAG_2=FLAG{22222222222222222222222222222222} \
#     -e FLAG_3=FLAG{33333333333333333333333333333333} \
#     -e FLAG_4=FLAG{44444444444444444444444444444444} \
#     -e FLAG_5=FLAG{55555555555555555555555555555555} \
#     -p 3000:3000 finledger-s5
#   bash tests/test_flags.sh
#   docker rm -f finledger-test
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCENARIO_DIR="$(dirname "$SCRIPT_DIR")"

BASE_URL="${BASE_URL:-http://localhost:3000}"
ORACLE="${ORACLE:-$SCENARIO_DIR/oracle_exploit.py}"
REFEREE_URL="${REFEREE_URL:-http://localhost:9999}"
MATCH_ID="${MATCH_ID:-test}"
CONTAINER="${CONTAINER:-finledger-test}"
TARGET_PORT="${TARGET_PORT:-3000}"

echo "[test] Waiting for /health (Spring Boot takes ~60s to start)..."
for i in $(seq 1 60); do
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
  --budget-seconds 180 2>&1 || true)
echo "$OUTPUT"

CAPTURED=$(echo "$OUTPUT" | python3 -c "
import json, sys, re
lines = sys.stdin.read()
m = re.search(r'\{.*\}', lines, re.DOTALL)
print(len(json.loads(m.group(0)).get('flags_captured', [])) if m else 0)
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
  --target-port "$TARGET_PORT" \
  --referee-url "$REFEREE_URL" \
  --match-id "$MATCH_ID" \
  --attacker-id 0 \
  --victim-id 1 \
  --budget-seconds 180 2>&1 || true)
echo "$OUTPUT"

CAPTURED=$(echo "$OUTPUT" | python3 -c "
import json, sys, re
lines = sys.stdin.read()
m = re.search(r'\{.*\}', lines, re.DOTALL)
print(len(json.loads(m.group(0)).get('flags_captured', [])) if m else 0)
")
[ "$CAPTURED" -eq 0 ] || { echo "[FAIL] Expected 0, got $CAPTURED"; exit 1; }
echo "[PASS] Patched: $CAPTURED/5 captured."

echo "[test] Verifying diagnostics no longer leak FLAG_2..."
DIAG=$(curl -sf "$BASE_URL/api/diagnostics")
if echo "$DIAG" | grep -q 'FLAG_2'; then
  echo "[FAIL] /api/diagnostics still leaks FLAG_2 after patch"
  exit 1
fi
echo "[PASS] /api/diagnostics no longer leaks FLAG_2."

echo "[test] Verifying patched profile does not serialize password hashes..."
COOKIE_JAR=$(mktemp)
curl -sf -c "$COOKIE_JAR" -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"finance","password":"S5Finance-5kR8-Books!"}' >/dev/null
PROFILE=$(curl -sf -b "$COOKIE_JAR" "$BASE_URL/api/users/profile?username=analyst")
rm -f "$COOKIE_JAR"
echo "$PROFILE" | grep -q '"username":"finance"' || { echo "[FAIL] Patched finance login/profile failed"; exit 1; }
if echo "$PROFILE" | grep -q 'passwordHash'; then
  echo "[FAIL] /api/users/profile still exposes passwordHash after patch"
  exit 1
fi
echo "[PASS] Patched profile hides passwordHash."

echo "[PASS] All tests passed."
