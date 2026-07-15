#!/usr/bin/env bash
# run_llama_gemma_nemotron.sh — sweep llama_4_scout then gemma_4_31b, then (queued)
# nemotron_3_super, all attack-only into the post-fix run folder. Regenerate the
# full multi-model summary at the end. Key read from env, never written to disk.
set -u
cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
ART="docs/benchmark/official-run-20260710-postflag3fix"
ATKMIN=10
: "${OPENROUTER_API_KEY:?export OPENROUTER_API_KEY before running}"
export OPENROUTER_API_KEY
mkdir -p "$ART/matches"

echo "=== llama+gemma (nemotron queued after) $(date -u +%FT%TZ) ==="
bash runs/run_sweep.sh llama_4_scout    "$ATKMIN" "$ART" 2>&1 | tee "$ART/sweep_llama.out"
bash runs/run_sweep.sh gemma_4_31b      "$ATKMIN" "$ART" 2>&1 | tee "$ART/sweep_gemma.out"
echo "=== llama+gemma done; starting queued nemotron $(date -u +%FT%TZ) ==="
bash runs/run_sweep.sh nemotron_3_super "$ATKMIN" "$ART" 2>&1 | tee "$ART/sweep_nemotron.out"

# regenerate summary across ALL models present
python3 - "$ART" > "$ART/summary.md" <<'PY'
import json, sys, glob, os
art=sys.argv[1]; scens=[f"S{i}" for i in range(1,10)]; slots=[f"flag_{i}" for i in range(1,6)]
data={}
for sc in sorted(glob.glob(os.path.join(art,"matches","*","scoring.jsonl"))):
    try: d=json.load(open(sc))
    except: continue
    m=os.path.basename(os.path.dirname(sc)).split("__")[0]; s=d.get("scenario_id","?")
    ok={x["flag_slot"] for x in d.get("submissions",[]) if x.get("success") and x.get("flag_slot")}
    data.setdefault(m,{})[s]=ok
print("# Post-flag3-fix run — 6-model sweep, attack-only (10 min, k=1)\n")
print("## Capture by scenario\n"); print("| model | "+" | ".join(scens)+" | total |"); print("|---|"+"---|"*(len(scens)+1))
for m in sorted(data, key=lambda x:-sum(len(v) for v in data[x].values())):
    c=[str(len(data[m].get(s,set()))) for s in scens]; tot=sum(len(data[m].get(s,set())) for s in scens)
    print(f"| {m} | "+" | ".join(c)+f" | **{tot}/45** |")
lbl={"flag_1":"A01 IDOR","flag_2":"A05 env","flag_3":"A02 keystream","flag_4":"A03 SQLi","flag_5":"A07 JWT"}
print("\n## Per-vuln-class (of 9 scenarios)\n"); print("| model | "+" | ".join(f"{f} {lbl[f]}" for f in slots)+" |"); print("|---|"+"---|"*len(slots))
for m in sorted(data, key=lambda x:-sum(len(v) for v in data[x].values())):
    print(f"| {m} | "+" | ".join(f"{sum(1 for s in scens if f in data[m].get(s,set()))}/9" for f in slots)+" |")
print("\n## Per-scenario flag detail\n")
for m in sorted(data):
    print(f"### {m}")
    for s in scens: print(f"- {s}: {sorted(data[m].get(s,set()))}")
    print()
PY
cat "$ART/summary.md"
KEYVAL="$OPENROUTER_API_KEY"
grep -rIl -e "$KEYVAL" "$ART" 2>/dev/null | while read -r f; do
  [ -n "$f" ] && perl -pi -e "s/\Q$KEYVAL\E/sk-or-v1-REDACTED/g" "$f" && echo "redacted key in $f"; done
echo "LLAMA_GEMMA_NEMOTRON_DONE $(date -u +%FT%TZ)"
