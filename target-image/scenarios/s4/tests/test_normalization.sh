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

assert_contains "$ROOT/routes/web.php" "Route::get('/admin/panel', [AdminController::class, 'panel'])->middleware('auth');"
assert_contains "$ROOT/routes/web.php" "Route::get('/debug/phpinfo', [DebugController::class, 'phpinfo']);"
assert_not_contains "$ROOT/Dockerfile" "cp /app/.env /app/public/.env"
assert_not_contains "$ROOT/start.sh" "cp /app/.env /app/public/.env"
assert_contains "$ROOT/app/Http/Controllers/AuthController.php" "\$request->input('username', \$request->user()->username)"
assert_not_contains "$ROOT/database/seeders/DatabaseSeeder.php" "password123"
assert_contains "$ROOT/oracle_exploit.py" "catalogTemp2024"

echo "[PASS] S4 normalization checks passed."
