#!/usr/bin/env bash
# run_defense_sweep.sh <model> <defense_min> <attack_min> <artdir>
# defense_only across S1-S9, <=3 concurrent, then collect + a defense summary.
set -u; cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
MODEL="${1:?}"; DEF="${2:-15}"; ATK="${3:-3}"; ART="${4:?}"
: "${OPENROUTER_API_KEY:?}"; export OPENROUTER_API_KEY
mkdir -p "$ART/matches"; MAN="$ART/${MODEL}.tsv"; : > "$MAN"
RUNID="defense-${MODEL}-$(date +%Y%m%d-%H%M%S)"
echo "=== $MODEL defense_only ${DEF}min+${ATK}min across S1-S9  run_id=$RUNID ==="
for n in $(seq 1 9); do
  while [ "$(docker ps --format '{{.Names}}'|grep -c '^claw_match_')" -ge 3 ]; do sleep 20; done
  mid=$(python3 referee-engine/sample_runner.py "S$n" --mode defense_only --model-a "$MODEL" \
        --defense-minutes "$DEF" --attack-minutes "$ATK" --bench-run-id "$RUNID" | sed -n 's/^match_id=//p')
  [ -n "$mid" ] && { printf 'S%s\t%s\t%s\n' "$n" "$MODEL" "$mid" >> "$MAN"; echo "launched S$n -> $mid"; }
  sleep 8
done
echo "all launched; waiting..."
while [ "$(docker ps --format '{{.Names}}'|grep -c '^claw_match_')" -gt 0 ]; do sleep 20; done
sleep 5
python3 referee-engine/collect_match_logs.py "$MAN" --out "$ART/matches"
# defense summary
python3 - "$ART" > "$ART/summary.md" <<'PY'
import json,sys,glob,os
art=sys.argv[1]; scens=[f"S{i}" for i in range(1,10)]
rows={}
for sc in sorted(glob.glob(os.path.join(art,"matches","*","scoring.jsonl"))):
    d=json.load(open(sc)); s=d.get("scenario_id"); pm=d.get("player_metrics",{}).get("1",{})
    osum=d.get("oracle_summary") or {}; res=(osum.get("results") or {})
    brittle=[]
    for r in res.values():
        brittle += (r.get("brittle_block_slots") or [])
    lost=pm.get("flags_lost",5); prot=5-(lost or 0)
    rows[s]={"protected":prot,"lost":lost,"sla_up":pm.get("sla_up"),"sla_down":pm.get("sla_down_minutes"),
             "def_score":pm.get("defense_score"),"brittle":sorted(set(brittle))}
print("# Defense sweep — flash 15min+3min, defense_only (k=1)\n")
print("| scenario | protected/5 | SLA up | sla_down_min | brittle_blocks | defense_score |")
print("|---|---|---|---|---|---|")
tot=0
for s in scens:
    r=rows.get(s)
    if not r: print(f"| {s} | – | – | – | – | – |"); continue
    tot+=r["protected"]
    print(f"| {s} | {r['protected']}/5 | {'yes' if r['sla_up'] else 'NO'} | {r['sla_down']} | {r['brittle'] or '—'} | {r['def_score']} |")
print(f"\n**Total protected: {tot}/45**")
PY
cat "$ART/summary.md"
KEYVAL="$OPENROUTER_API_KEY"
grep -rIl -e "$KEYVAL" "$ART" 2>/dev/null | while read -r f; do [ -n "$f" ] && perl -pi -e "s/\Q$KEYVAL\E/sk-or-v1-REDACTED/g" "$f"; done
echo "DEFENSE_SWEEP_DONE $RUNID"
