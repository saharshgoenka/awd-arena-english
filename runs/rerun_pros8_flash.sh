#!/usr/bin/env bash
set -u; cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
: "${OPENROUTER_API_KEY:?}"; export OPENROUTER_API_KEY
PRO=docs/benchmark/defense-pro-15min-20260714-fixed
# ---- 1. Pro S8 clean rerun (replace the spurious 0/5) ----
echo "=== Pro S8 rerun $(date -u +%FT%TZ) ==="
rm -rf "$PRO"/matches/deepseek_v4_pro__S8__*
mid=$(python3 referee-engine/sample_runner.py S8 --mode defense_only --model-a deepseek_v4_pro \
      --defense-minutes 15 --attack-minutes 3 --bench-run-id defense-pro-s8-rerun | sed -n 's/^match_id=//p')
echo "S8 rerun match=$mid"; printf 'S8\tdeepseek_v4_pro\t%s\n' "$mid" > "$PRO/s8_rerun.tsv"
while [ "$(docker ps --format '{{.Names}}'|grep -c '^claw_match_')" -gt 0 ]; do sleep 20; done
sleep 5
python3 referee-engine/collect_match_logs.py "$PRO/s8_rerun.tsv" --out "$PRO/matches"
# regen pro summary
python3 - "$PRO" > "$PRO/summary.md" <<'PY'
import json,sys,glob,os
art=sys.argv[1]; scens=[f"S{i}" for i in range(1,10)]; rows={}
for sc in sorted(glob.glob(os.path.join(art,"matches","*","scoring.jsonl"))):
    d=json.load(open(sc)); s=d.get("scenario_id"); pm=d.get("player_metrics",{}).get("1",{})
    rows[s]={"p":5-(pm.get("flags_lost",5) or 0),"sla":pm.get("sla_up"),"down":pm.get("sla_down_minutes")}
print("# Pro defense (prompt-fixed, S8 rerun) — 15min+3min k=1\n\n| scenario | protected/5 | SLA | down |\n|---|---|---|---|")
tot=0
for s in scens:
    r=rows.get(s,{}); tot+=r.get("p",0)
    print(f"| {s} | {r.get('p','?')}/5 | {'UP' if r.get('sla') else 'DOWN'} | {r.get('down','?')} |")
print(f"\n**Total protected: {tot}/45**")
PY
echo "=== Pro table after S8 rerun ==="; grep -E '^\| S8|Total' "$PRO/summary.md"
# ---- 2. Flash full defense on fixed prompt ----
echo "=== Flash defense (fixed prompt) $(date -u +%FT%TZ) ==="
bash runs/run_defense_sweep.sh deepseek_v4_flash 15 3 docs/benchmark/defense-flash-15min-20260714-fixed
echo "RERUN_S8_FLASH_DONE $(date -u +%FT%TZ)"
