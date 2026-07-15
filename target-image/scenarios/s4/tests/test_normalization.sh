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

assert_contains "$ROOT/routes/web.php" "Route::get('/debug/phpinfo', [DebugController::class, 'phpinfo']);"
assert_contains "$ROOT/routes/web.php" "Route::get('/reports/mine',  [ReportController::class, 'mine']);"
assert_contains "$ROOT/routes/web.php" "Route::get('/reports/{id}',  [ReportController::class, 'show']);"
assert_contains "$ROOT/routes/web.php" "Route::get('/exports/encrypted', [ExportController::class, 'encrypted'])->middleware('auth');"
assert_contains "$ROOT/routes/web.php" "Route::get('/admin/orders/report', [AdminController::class, 'ordersReport']);"
assert_not_contains "$ROOT/Dockerfile" "cp /app/.env /app/public/.env"
assert_not_contains "$ROOT/start.sh" "cp /app/.env /app/public/.env"
assert_not_contains "$ROOT/database/seeders/DatabaseSeeder.php" "password123"
assert_contains "$ROOT/app/Http/Controllers/DebugController.php" "'PAYROLL_SYNC_TOKEN'      => getenv('FLAG_2')"
assert_contains "$ROOT/app/Http/Controllers/ExportController.php" "private function keystream(): string"
assert_contains "$ROOT/app/Support/ApiToken.php" "if ((\$header['alg'] ?? '') === 'none')"
assert_contains "$ROOT/oracle_exploit.py" "PAYROLL_SYNC_TOKEN"
assert_contains "$ROOT/oracle_exploit.py" "exploit_flag3_keystream_reuse"
assert_not_contains "$ROOT/oracle_exploit.py" "_crack_legacy_hash"

echo "[PASS] S4 normalization checks passed."
