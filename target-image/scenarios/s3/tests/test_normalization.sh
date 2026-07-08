#!/usr/bin/env bash
set -euo pipefail

APP="${APP:-app.js}"
ADMIN="${ADMIN:-routes/admin.js}"
AUTH_ROUTES="${AUTH_ROUTES:-routes/auth.js}"
AUTH_MW="${AUTH_MW:-middleware/auth.js}"
DEBUG_ROUTES="${DEBUG_ROUTES:-routes/debug.js}"
ORACLE="${ORACLE:-oracle_exploit.py}"

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
need_text "$ORACLE" "exploit_flag2_diagnostics_endpoint"
need_text "$ORACLE" "exploit_flag5_login_guess"

need_absent "$AUTH_MW" "rawHeader.alg === 'none'"
need_absent "$ORACLE" "_forge_jwt_none"
need_absent "$ORACLE" "taskadmin99"

echo "[PASS] S3 normalization source checks passed."
