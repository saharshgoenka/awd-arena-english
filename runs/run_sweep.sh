#!/usr/bin/env bash
# run_sweep.sh <model_id> [attack_minutes] — launch <model> across S1-S9 attack_only,
# <=3 concurrent, then AUTO-COLLECT a per-match log folder for every match.
# Per-match folders land in docs/benchmark/matches/<model>__<scenario>__match_<id>/.
set -u
cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
MODEL="${1:?usage: run_sweep.sh <model_id> [attack_minutes] [artifact_dir]}"
ATKMIN="${2:-10}"
ARTDIR="${3:-}"                       # optional: self-contained artifact dir
if [ -n "$ARTDIR" ]; then
  mkdir -p "$ARTDIR/matches"
  MANIFEST="$ARTDIR/${MODEL}.tsv"; OUT="$ARTDIR/matches"; AGG="$ARTDIR"
else
  mkdir -p runs docs/benchmark/matches
  MANIFEST="runs/${MODEL}.tsv"; OUT="docs/benchmark/matches"; AGG="docs/benchmark"
fi
: > "$MANIFEST"
RUNID="sweep-${MODEL}-$(date +%Y%m%d-%H%M%S)"
echo "bench_run_id=$RUNID  model=$MODEL  attack_minutes=$ATKMIN"
for n in $(seq 1 9); do
  while [ "$(docker ps --format '{{.Names}}' | grep -c '^claw_match_')" -ge 3 ]; do sleep 20; done
  mid=$(python3 referee-engine/sample_runner.py "S$n" --mode attack_only --model-a "$MODEL" \
        --defense-minutes 0 --attack-minutes "$ATKMIN" --bench-run-id "$RUNID" \
        | sed -n 's/^match_id=//p')
  if [ -n "$mid" ]; then
    printf 'S%s\t%s\t%s\n' "$n" "$MODEL" "$mid" >> "$MANIFEST"
    echo "launched S$n -> $mid"
  else
    echo "WARN: S$n produced no match_id"
  fi
  sleep 8
done
echo "all launched; waiting for matches to finish..."
while [ "$(docker ps --format '{{.Names}}' | grep -c '^claw_match_')" -gt 0 ]; do sleep 20; done
# leaked-container cleanup
while IFS=$'\t' read -r s m mid; do
  [ -n "$mid" ] && docker rm -f "claw_match_${mid}_1" "target_match_${mid}_1" "target_match_${mid}_2" >/dev/null 2>&1
done < "$MANIFEST"
# AUTO per-match log folders (untruncated events + agent trajectory + scoring + bundle)
echo "collecting per-match log folders..."
python3 referee-engine/collect_match_logs.py "$MANIFEST" --out "$OUT"
# aggregate results JSON too
python3 referee-engine/collect_results.py "$MANIFEST" --out "$AGG" 2>/dev/null || true
echo "SWEEP_COMPLETE $RUNID"
