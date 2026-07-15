#!/usr/bin/env bash
set -u; cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
ART="docs/benchmark/official-run-20260710-postflag3fix"
: "${OPENROUTER_API_KEY:?}"; export OPENROUTER_API_KEY
echo "=== glm then codestral $(date -u +%FT%TZ) ==="
bash runs/run_sweep.sh glm_4_5_air    10 "$ART" 2>&1 | tee "$ART/sweep_glm.out"
echo "=== glm done; starting codestral $(date -u +%FT%TZ) ==="
bash runs/run_sweep.sh codestral_2508 10 "$ART" 2>&1 | tee "$ART/sweep_codestral.out"
python3 - "$ART" > "$ART/summary.md" <<'PY'
import json,sys,glob,os
art=sys.argv[1]; scens=[f"S{i}" for i in range(1,10)]; slots=[f"flag_{i}" for i in range(1,6)]
data={}
for sc in sorted(glob.glob(os.path.join(art,"matches","*","scoring.jsonl"))):
    try:d=json.load(open(sc))
    except:continue
    m=os.path.basename(os.path.dirname(sc)).split("__")[0]; s=d.get("scenario_id","?")
    data.setdefault(m,{})[s]={x["flag_slot"] for x in d.get("submissions",[]) if x.get("success") and x.get("flag_slot")}
print("# Post-flag3-fix run — attack-only (10 min, k=1)\n\n## Capture by scenario\n")
print("| model | "+" | ".join(scens)+" | total |"); print("|---|"+"---|"*(len(scens)+1))
for m in sorted(data,key=lambda x:-sum(len(v) for v in data[x].values())):
    c=[str(len(data[m].get(s,set()))) for s in scens]; tot=sum(len(data[m].get(s,set())) for s in scens)
    print(f"| {m} | "+" | ".join(c)+f" | **{tot}/45** |")
lbl={"flag_1":"A01","flag_2":"A05","flag_3":"A02 keystream","flag_4":"A03","flag_5":"A07"}
print("\n## Per-vuln-class (of 9)\n"); print("| model | "+" | ".join(f"{f} {lbl[f]}" for f in slots)+" |"); print("|---|"+"---|"*len(slots))
for m in sorted(data,key=lambda x:-sum(len(v) for v in data[x].values())):
    print(f"| {m} | "+" | ".join(f"{sum(1 for s in scens if f in data[m].get(s,set()))}/9" for f in slots)+" |")
PY
KEYVAL="$OPENROUTER_API_KEY"
grep -rIl -e "$KEYVAL" "$ART" 2>/dev/null | while read -r f; do [ -n "$f" ] && perl -pi -e "s/\Q$KEYVAL\E/sk-or-v1-REDACTED/g" "$f"; done
echo "GLM_CODESTRAL_DONE $(date -u +%FT%TZ)"
