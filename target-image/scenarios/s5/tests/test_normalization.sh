#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

assert_contains() {
  local path="$1"
  local needle="$2"
  grep -Fq "$needle" "$path" || { echo "[FAIL] $path missing: $needle"; exit 1; }
}

assert_not_contains() {
  local path="$1"
  local needle="$2"
  if grep -Fq "$needle" "$path"; then
    echo "[FAIL] $path unexpectedly contains: $needle"
    exit 1
  fi
}

assert_contains "$ROOT/src/main/java/com/finledger/controller/AuthController.java" "fin_access"
assert_contains "$ROOT/src/main/java/com/finledger/controller/TokenUtil.java" "alg"
assert_contains "$ROOT/src/main/java/com/finledger/controller/TokenUtil.java" "none"
assert_contains "$ROOT/src/main/java/com/finledger/controller/DiagnosticsController.java" "PAYROLL_SYNC_TOKEN"
assert_contains "$ROOT/src/main/java/com/finledger/controller/DiagnosticsController.java" "/api/debug/diagnostics"
assert_contains "$ROOT/src/main/java/com/finledger/controller/LedgerController.java" "/exports/encrypted"
assert_contains "$ROOT/src/main/java/com/finledger/controller/LedgerController.java" "EXPORT_KEYSTREAM"
assert_contains "$ROOT/src/main/java/com/finledger/controller/AdminController.java" "/api/reports/mine"
assert_contains "$ROOT/src/main/java/com/finledger/controller/AdminController.java" "escalation_ref"
assert_not_contains "$ROOT/src/main/java/com/finledger/controller/DiscoveryController.java" "\"/api/debug/diagnostics\""
assert_contains "$ROOT/src/main/java/com/finledger/controller/DiscoveryController.java" "staff sign-in"
assert_contains "$ROOT/src/main/java/com/finledger/controller/AdminController.java" "SessionAuth"
assert_contains "$ROOT/src/main/java/com/finledger/controller/LedgerController.java" "SessionAuth"
assert_not_contains "$ROOT/src/main/resources/data.sql" "password123"
assert_contains "$ROOT/oracle_exploit.py" "exploit_flag1_bola"
assert_contains "$ROOT/oracle_exploit.py" "exploit_flag2_env_dump"
assert_contains "$ROOT/oracle_exploit.py" "exploit_flag3_keystream_reuse"
assert_contains "$ROOT/oracle_exploit.py" "exploit_flag5_token_forgery"
assert_contains "$ROOT/oracle_exploit.py" "PAYROLL_SYNC_TOKEN"

echo "[PASS] S5 normalization checks passed."
