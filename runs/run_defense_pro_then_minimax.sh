#!/usr/bin/env bash
# Clean defense re-run on the prompt-fixed referee: pro first, then minimax queued.
set -u; cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
: "${OPENROUTER_API_KEY:?}"; export OPENROUTER_API_KEY
echo "=== PRO defense (prompt-fixed) $(date -u +%FT%TZ) ==="
bash runs/run_defense_sweep.sh deepseek_v4_pro 15 3 docs/benchmark/defense-pro-15min-20260714-fixed
echo "=== PRO done; queued MINIMAX defense $(date -u +%FT%TZ) ==="
bash runs/run_defense_sweep.sh minimax_m3 15 3 docs/benchmark/defense-minimax-15min-20260714
echo "PRO_MINIMAX_DEFENSE_DONE $(date -u +%FT%TZ)"
