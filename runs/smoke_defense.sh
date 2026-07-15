#!/usr/bin/env bash
set -u; cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
SM="docs/benchmark/smoke-defense-flash-s1"; MAN="$SM/manifest.tsv"; : > "$MAN"
: "${OPENROUTER_API_KEY:?}"; export OPENROUTER_API_KEY
RUNID="smoke-defense-flash-s1-$(date +%Y%m%d-%H%M%S)"
echo "=== flash DEFENSE_ONLY on S1: 15min defense + 3min oracle attack ==="
mid=$(python3 referee-engine/sample_runner.py S1 --mode defense_only --model-a deepseek_v4_flash \
      --defense-minutes 15 --attack-minutes 3 --bench-run-id "$RUNID" | sed -n 's/^match_id=//p')
echo "match_id=$mid"; printf 'S1\tdeepseek_v4_flash\t%s\n' "$mid" >> "$MAN"
while [ "$(docker ps --format '{{.Names}}'|grep -c '^claw_match_')" -gt 0 ]; do sleep 20; done
sleep 5
python3 referee-engine/collect_match_logs.py "$MAN" --out "$SM/matches"
echo "DEFENSE_SMOKE_DONE $mid"
