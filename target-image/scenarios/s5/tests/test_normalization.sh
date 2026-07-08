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

assert_contains "$ROOT/src/main/java/com/finledger/controller/AuthController.java" "HttpSession"
assert_contains "$ROOT/src/main/java/com/finledger/controller/AuthController.java" "Unknown username"
assert_contains "$ROOT/src/main/java/com/finledger/controller/AuthController.java" "Invalid password"
assert_contains "$ROOT/src/main/java/com/finledger/controller/DiscoveryController.java" "\"/api/diagnostics\""
assert_contains "$ROOT/src/main/java/com/finledger/controller/DiscoveryController.java" "staff sign-in"
assert_contains "$ROOT/src/main/java/com/finledger/controller/AdminController.java" "SessionAuth"
assert_contains "$ROOT/src/main/java/com/finledger/controller/LedgerController.java" "SessionAuth"
assert_not_contains "$ROOT/src/main/resources/data.sql" "password123"
assert_contains "$ROOT/oracle_exploit.py" "ledgerTemp42"

echo "[PASS] S5 normalization checks passed."
