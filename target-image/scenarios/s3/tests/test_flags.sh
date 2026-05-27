#!/usr/bin/env bash
# S3/Express TaskFlow — pre/post-patch smoke test
#
# Usage:
#   docker build -t taskflow-s3 .
#   docker run -d --name taskflow-test \
#     -e FLAG_1=FLAG{11111111111111111111111111111111} \
#     -e FLAG_2=FLAG{22222222222222222222222222222222} \
#     -e FLAG_3=FLAG{33333333333333333333333333333333} \
#     -e FLAG_4=FLAG{44444444444444444444444444444444} \
#     -e FLAG_5=FLAG{55555555555555555555555555555555} \
#     -p 3000:3000 taskflow-s3
#   bash tests/test_flags.sh
#   docker rm -f taskflow-test
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3000}"
ORACLE="${ORACLE:-./oracle_exploit.py}"
REFEREE_URL="${REFEREE_URL:-http://localhost:9999}"
MATCH_ID="${MATCH_ID:-test}"

echo "[test] Waiting for /health..."
for i in $(seq 1 45); do
  if curl -sf "$BASE_URL/health" | grep -q '"ok"'; then
    echo "[test] App is up."
    break
  fi
  sleep 3
done

echo "[test] === Phase 1: unpatched — expecting 5/5 ==="
OUTPUT=$(python3 "$ORACLE" \
  --target-host "${TARGET_HOST:-localhost}" \
  --target-port 3000 \
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
docker exec -i taskflow-test bash -c "cd /app && patch -p1" < oracle_patch.diff

echo "[test] Restarting app..."
docker exec taskflow-test supervisorctl restart app
sleep 8

echo "[test] Waiting for /health after restart..."
for i in $(seq 1 20); do
  curl -sf "$BASE_URL/health" | grep -q '"ok"' && break || sleep 2
done

echo "[test] === Phase 2: patched — expecting 0/5 ==="
OUTPUT=$(python3 "$ORACLE" \
  --target-host "${TARGET_HOST:-localhost}" \
  --target-port 3000 \
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
echo "[PASS] All tests passed."
