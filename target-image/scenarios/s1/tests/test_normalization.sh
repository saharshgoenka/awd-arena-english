#!/usr/bin/env bash
set -euo pipefail

APP="${APP:-app.py}"
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

need_text "$APP" '@app.route("/support/diagnostics")'
need_text "$APP" '@app.route("/team/audit")'
need_text "$APP" 'PAYROLL_SYNC_TOKEN'
need_text "$APP" 'alg"'
need_text "$APP" 'none'
need_text "$APP" 'reviewer_report_id'
need_text "$APP" '@app.route("/exports/encrypted")'
need_text "$APP" 'if "username" not in session:'
need_text "$ORACLE" 'exploit_flag2_env_dump'
need_text "$ORACLE" 'exploit_flag3_keystream_reuse'
need_text "$ORACLE" 'exploit_flag1_bola'
need_text "$ORACLE" 'exploit_flag5_token_forgery'
need_text "$ORACLE" 'PAYROLL_SYNC_TOKEN'
need_text "$ORACLE" '/exports/encrypted?item=vault'

need_absent "$APP" '@app.route("/debug/config")'
need_absent "$APP" 'password123'
need_absent "$ORACLE" 'nexusadmin2024'

echo "[PASS] S1 normalization source checks passed."
