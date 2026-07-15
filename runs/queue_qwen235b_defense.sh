#!/usr/bin/env bash
set -u; cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
: "${OPENROUTER_API_KEY:?}"; export OPENROUTER_API_KEY
ATK=docs/benchmark/official-run-20260710-postflag3fix/qwen_attack.log
echo "=== qwen235b defense queued; waiting for attack to finish $(date -u +%FT%TZ) ==="
while ! grep -q 'QWEN_ATTACK_DONE' "$ATK" 2>/dev/null; do sleep 30; done
sleep 10
echo "=== attack done; starting qwen235b defense $(date -u +%FT%TZ) ==="
bash runs/run_defense_sweep.sh qwen3_235b 15 3 docs/benchmark/defense-qwen235b-15min-20260714
echo "QWEN235B_DEFENSE_DONE $(date -u +%FT%TZ)"
