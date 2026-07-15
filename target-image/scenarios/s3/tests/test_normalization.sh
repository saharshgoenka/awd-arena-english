#!/usr/bin/env bash
set -euo pipefail

APP="${APP:-app.js}"
ADMIN="${ADMIN:-routes/admin.js}"
AUTH_ROUTES="${AUTH_ROUTES:-routes/auth.js}"
AUTH_MW="${AUTH_MW:-middleware/auth.js}"
DEBUG_ROUTES="${DEBUG_ROUTES:-routes/debug.js}"
ORACLE="${ORACLE:-oracle_exploit.py}"
PATCH_FILE="${PATCH_FILE:-oracle_patch.diff}"

need_text() {
  local file="$1"
  local text="$2"
  grep -F "$text" "$file" >/dev/null || {
    echo "[FAIL] Missing expected text in $file: $text"
    exit 1
  }
}

need_absent() {
  local file="$1"
  local text="$2"
  if grep -F "$text" "$file" >/dev/null; then
    echo "[FAIL] Unexpected legacy text still present in $file: $text"
    exit 1
  fi
}

need_text "$APP" "express.static(path.join(__dirname, 'public'))"
need_text "$DEBUG_ROUTES" "router.get('/diagnostics'"
need_text "$ADMIN" "router.get('/config', requireAuth"
need_text "$AUTH_ROUTES" "return res.status(401).json({ error: 'Wrong password' });"
need_text "$AUTH_ROUTES" "return res.status(404).json({ error: 'Unknown user' });"
need_text "$ORACLE" "exploit_flag2_env_dump"
need_text "$ORACLE" "exploit_flag3_keystream_reuse"
need_text "$ORACLE" "exploit_flag5_jwt_none_forgery"
need_text "$PATCH_FILE" "nonce_hex"
need_text "$PATCH_FILE" "crypto.randomBytes"
need_text "$APP" "/api/projects/internal"

# flag_1 (A01 IDOR/BOLA): object route authenticates but omits the owner check.
need_text "$APP" "app.use('/api/reports', require('./routes/reports'))"
# flag_2 (A05): diagnostics path is NOT advertised in the /api discovery block.
need_absent "$APP" "path: '/api/debug/diagnostics'"
# flag_5 (A07): verifier honours alg:none; oracle forges an unsecured token.
need_text "$AUTH_MW" "header.alg === 'none'"
need_text "$ORACLE" "_forge_jwt_none"
need_absent "$ORACLE" "taskadmin99"

echo "[PASS] S3 normalization source checks passed."
