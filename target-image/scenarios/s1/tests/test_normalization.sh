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
need_text "$APP" 'if "username" not in session:'
need_text "$ORACLE" 'exploit_flag2_support_diagnostics'
need_text "$ORACLE" 'exploit_flag3_hash_leak'

need_absent "$APP" '@app.route("/debug/config")'
need_absent "$APP" 'password123'
need_absent "$ORACLE" 'nexusadmin2024'

echo "[PASS] S1 normalization source checks passed."
