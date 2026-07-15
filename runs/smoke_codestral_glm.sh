#!/usr/bin/env bash
set -u; cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
SM="docs/benchmark/smoke-codestral-glm-20260710"; MAN="$SM/manifest.tsv"; : > "$MAN"
: "${OPENROUTER_API_KEY:?}"; export OPENROUTER_API_KEY
RUNID="smoke-codestral-glm-$(date +%Y%m%d-%H%M%S)"
# S1 (easiest) + S3 (mid) so a total tool-call failure is unambiguous
for spec in "codestral_2508 S1" "codestral_2508 S3" "glm_4_5_air S1" "glm_4_5_air S3"; do
  set -- $spec; MODEL=$1; SC=$2
  mid=$(python3 referee-engine/sample_runner.py "$SC" --mode attack_only --model-a "$MODEL" \
        --defense-minutes 0 --attack-minutes 8 --bench-run-id "$RUNID" | sed -n 's/^match_id=//p')
  [ -n "$mid" ] && { printf '%s\t%s\t%s\n' "$SC" "$MODEL" "$mid" >> "$MAN"; echo "launched $MODEL $SC -> $mid"; }
  sleep 6
done
echo "waiting..."; while [ "$(docker ps --format '{{.Names}}'|grep -c '^claw_match_')" -gt 0 ]; do sleep 20; done
python3 referee-engine/collect_match_logs.py "$MAN" --out "$SM/matches"
echo "SMOKE_DONE $RUNID"
