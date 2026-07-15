#!/usr/bin/env bash
# Rerun DeepSeek Pro then Flash across S1-S9 with the flag_2 fix, then print a per-flag summary.
set -u
cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
bash runs/run_sweep.sh deepseek_v4_pro 10
bash runs/run_sweep.sh deepseek_v4_flash 10
echo "================ POST-FIX SUMMARY ================"
docker exec openclaw-referee sh -c 'for f in /app/data/runs/v1/matches/*.jsonl; do cat "$f"; echo; done' 2>/dev/null \
  > /tmp/rerun_matches.jsonl
python3 - <<'PY'
import json
from collections import defaultdict
per=defaultdict(dict)
for ln in open("/tmp/rerun_matches.jsonl"):
    ln=ln.strip()
    if not ln.startswith("{"): continue
    d=json.loads(ln)
    rid=str(d.get("bench_run_id",""))
    if not (rid.startswith("sweep-deepseek_v4_pro") or rid.startswith("sweep-deepseek_v4_flash")): continue
    model=d["players"][0]["model"].split("/")[-1]
    sid=d["scenario_id"]
    ok=sorted((s["flag_slot"] for s in d.get("submissions",[]) if s.get("success")), key=lambda x:int(x.split("_")[1]))
    per[(model,rid)][sid]=(d["player_metrics"]["1"]["flags_captured"], ok)
for (model,rid),rows in sorted(per.items()):
    tot=sum(c for c,_ in rows.values())
    f2=sum(1 for _,ok in rows.values() if "flag_2" in ok)
    print(f"\n### {model}  ({rid})  total={tot}/{len(rows)*5}  flag_2={f2}/{len(rows)}")
    for sid in sorted(rows, key=lambda s:int(s[1:])):
        c,ok=rows[sid]; print(f"  {sid}: {c}/5  {ok}")
PY
echo "RERUN_BOTH_DONE"
