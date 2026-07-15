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

assert_contains "$ROOT/app/controllers/posts_controller.rb" "before_action :require_login"
assert_not_contains "$ROOT/app/controllers/posts_controller.rb" "except: [:search]"
assert_contains "$ROOT/config/routes.rb" 'get "/reports/mine",      to: "reports#mine"'
assert_contains "$ROOT/config/routes.rb" 'get "/reports/:id",       to: "reports#show"'
assert_contains "$ROOT/config/routes.rb" 'get "/exports/encrypted", to: "exports#encrypted"'
assert_not_contains "$ROOT/db/seeds.rb" "password123"
assert_contains "$ROOT/app/controllers/debug_controller.rb" '"PAYROLL_SYNC_TOKEN" => ENV.fetch("FLAG_2", "FLAG{missing}")'
assert_contains "$ROOT/app/controllers/exports_controller.rb" 'KEYSTREAM = (Digest::SHA256.digest("contenthub-export-key-2024") * 8).bytes.freeze'
assert_contains "$ROOT/app/lib/token_lite.rb" 'if header["alg"] == "none"'
assert_contains "$ROOT/oracle_exploit.py" "PAYROLL_SYNC_TOKEN"
assert_contains "$ROOT/oracle_exploit.py" "exploit_flag3_keystream_reuse"
assert_contains "$ROOT/config/environments/production.rb" "config.consider_all_requests_local = false"

echo "[PASS] S6 normalization checks passed."
