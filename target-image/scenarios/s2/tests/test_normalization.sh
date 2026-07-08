#!/usr/bin/env bash
set -euo pipefail

VIEWS="${VIEWS:-hr/views.py}"
URLS="${URLS:-peopleops/urls.py}"
HR_URLS="${HR_URLS:-hr/urls.py}"
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

need_text "$VIEWS" 'def diagnostics_info('
need_text "$URLS" 'path("api/diagnostics/", hr_views.diagnostics_info'
need_text "$VIEWS" 'def employee_search_api('
need_text "$HR_URLS" 'path("api/search/",      views.employee_search_api'
need_text "$VIEWS" 'request.user.username != "jdoe"'
need_text "$ORACLE" 'exploit_flag2_diagnostics_endpoint'
need_text "$ORACLE" 'exploit_flag3_hash_leak'

need_absent "$URLS" '__debug__/info/'
need_absent "$VIEWS" 'password123'
need_absent "$ORACLE" 'hrmanager2024'

echo "[PASS] S2 normalization source checks passed."
