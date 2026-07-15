#!/usr/bin/env bash
set -u; cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
: "${OPENROUTER_API_KEY:?}"; export OPENROUTER_API_KEY
FF=docs/benchmark/defense-flash-15min-20260714-fixed
echo "=== qwen queued; waiting for flash-fixed to finish $(date -u +%FT%TZ) ==="
while ! grep -q 'RERUN_S8_FLASH_DONE' "$FF/driver.log" 2>/dev/null; do sleep 30; done
sleep 10
echo "=== flash done; starting qwen defense $(date -u +%FT%TZ) ==="
bash runs/run_defense_sweep.sh qwen3_coder_next 15 3 docs/benchmark/defense-qwen-15min-20260714
echo "QWEN_DEFENSE_DONE $(date -u +%FT%TZ)"
