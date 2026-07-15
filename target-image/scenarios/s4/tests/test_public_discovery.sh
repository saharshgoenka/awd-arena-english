#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

assert_file() {
  local path="$1"
  [ -f "$path" ] || { echo "[FAIL] missing $path"; exit 1; }
}

assert_contains() {
  local path="$1"
  local needle="$2"
  grep -Fq "$needle" "$path" || { echo "[FAIL] $path missing: $needle"; exit 1; }
}

assert_not_contains() {
  local path="$1"
  local needle="$2"
  if grep -Fq "$needle" "$path"; then
    echo "[FAIL] $path leaks: $needle"
    exit 1
  fi
}

DISCOVERY="$ROOT/app/Http/Controllers/DiscoveryController.php"
HOME="$ROOT/resources/views/home.blade.php"

assert_file "$DISCOVERY"
assert_file "$HOME"

for route in "'/'" "'/status'" "'/help'" "'/about'" "'/api'"; do
  assert_contains "$ROOT/routes/web.php" "$route"
done

for text in "ShopAdmin" "status" "help" "about" "api"; do
  assert_contains "$HOME" "$text"
done

for assisted_route in \
  "/admin/orders/report" \
  "/products/search?q=term" \
  "/reports/mine" \
  "/reports/{id}" \
  "/exports/encrypted?item=<id|vault>"
do
  assert_contains "$DISCOVERY" "$assisted_route"
done

for path in "$DISCOVERY" "$HOME"; do
  assert_not_contains "$path" "flag_"
  assert_not_contains "$path" "FLAG_"
  assert_not_contains "$path" "legacy-token"
  assert_not_contains "$path" "SQL"
  assert_not_contains "$path" "MD5"
done

if [ -n "${BASE_URL:-}" ]; then
  for endpoint in / /status /help /about /api; do
    curl -fsS "$BASE_URL$endpoint" >/dev/null
  done
fi

echo "[PASS] S4 public discovery surfaces are present and non-spoiling."
