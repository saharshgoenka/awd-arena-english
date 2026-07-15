#!/usr/bin/env bash
# DeepSeek Pro sweep across S1-S9, attack_only, <=3 concurrent. Records manifest, waits, cleans up.
set -u
cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
MODEL=deepseek_v4_pro
mkdir -p runs
MANIFEST=runs/${MODEL}.tsv; : > "$MANIFEST"
RUNID=sweep-deepseek-pro-$(date +%Y%m%d-%H%M%S)
echo "bench_run_id=$RUNID"
for n in $(seq 1 9); do
  # concurrency gate: keep <=3 live agent matches
  while [ "$(docker ps --format '{{.Names}}' | grep -c '^claw_match_')" -ge 3 ]; do sleep 20; done
  mid=$(python3 referee-engine/sample_runner.py S$n --mode attack_only --model-a "$MODEL" \
        --defense-minutes 0 --attack-minutes 10 --bench-run-id "$RUNID" \
        | sed -n 's/^match_id=//p')
  if [ -n "$mid" ]; then
    printf 'S%s\t%s\t%s\n' "$n" "$MODEL" "$mid" >> "$MANIFEST"
    echo "launched S$n -> $mid"
  else
    echo "WARN: S$n launch produced no match_id"
  fi
  sleep 8
done
echo "all launched; waiting for matches to finish..."
while [ "$(docker ps --format '{{.Names}}' | grep -c '^claw_match_')" -gt 0 ]; do sleep 20; done
# cleanup any leaked target/agent containers for these matches
while IFS=$'\t' read -r s m mid; do
  [ -n "$mid" ] && docker rm -f "claw_match_${mid}_1" "target_match_${mid}_1" "target_match_${mid}_2" >/dev/null 2>&1
done < "$MANIFEST"
echo "SWEEP_COMPLETE $RUNID"
