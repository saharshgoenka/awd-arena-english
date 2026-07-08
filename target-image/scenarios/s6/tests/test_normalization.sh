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
assert_contains "$ROOT/app/controllers/profile_controller.rb" "params[:username]"
assert_not_contains "$ROOT/db/seeds.rb" "password123"
assert_contains "$ROOT/oracle_exploit.py" "storyDraft2024"
assert_contains "$ROOT/config/environments/production.rb" "config.consider_all_requests_local = false"

echo "[PASS] S6 normalization checks passed."
