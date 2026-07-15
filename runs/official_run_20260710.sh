#!/usr/bin/env bash
# official_run_20260710.sh — DeepSeek Pro + Flash attack-only sweep across S1-S9,
# collected into a self-contained artifact folder. Key is read from $OPENROUTER_API_KEY
# (never written to disk); artifacts are scrubbed of the key value before finishing.
set -u
cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
ART="docs/benchmark/official-run-20260710"
ATKMIN=10
: "${OPENROUTER_API_KEY:?export OPENROUTER_API_KEY before running}"
export OPENROUTER_API_KEY

echo "=== OFFICIAL RUN $(date -u +%FT%TZ) === pro then flash, attack_only ${ATKMIN}min into $ART"
bash runs/run_sweep.sh deepseek_v4_pro   "$ATKMIN" "$ART" 2>&1 | tee "$ART/sweep_pro.out"
bash runs/run_sweep.sh deepseek_v4_flash "$ATKMIN" "$ART" 2>&1 | tee "$ART/sweep_flash.out"

echo "=== per-flag summary ==="
python3 - "$ART" <<'PY' | tee "$ART/summary.md"
import json, sys, glob, os
art = sys.argv[1]
print("# Official run 2026-07-10 — attack-only per-flag summary\n")
rows = {}
for mj in sorted(glob.glob(os.path.join(art, "matches", "*", "match.json"))):
    d = os.path.dirname(mj)
    sub = os.path.join(d, "submissions.json")
    try:
        m = json.load(open(mj)); subs = json.load(open(sub)) if os.path.exists(sub) else []
    except Exception:
        continue
    name = os.path.basename(d)               # model__Sx__match_...
    model = name.split("__")[0]; scen = name.split("__")[1] if "__" in name else "?"
    ok = sorted({s.get("flag_slot") for s in subs if s.get("success")},
                key=lambda x: int(x.split("_")[1]) if x and "_" in x else 99)
    rows.setdefault(model, {})[scen] = ok
for model in sorted(rows):
    tot = sum(len(v) for v in rows[model].values())
    n = len(rows[model])
    print(f"\n## {model}  total={tot}/{n*5}")
    for scen in sorted(rows[model]):
        ok = rows[model][scen]
        print(f"- {scen}: {len(ok)}/5  {ok}")
PY

echo "=== key-scrub pass (never publish the key) ==="
KEYVAL="$OPENROUTER_API_KEY"
# 1) plaintext files
hits=$(grep -rIl -e "$KEYVAL" "$ART" 2>/dev/null || true)
if [ -n "$hits" ]; then
  echo "REDACTING plaintext key in:"; echo "$hits"
  echo "$hits" | while read -r f; do
    [ -n "$f" ] && perl -pi -e "s/\Q$KEYVAL\E/sk-or-v1-REDACTED/g" "$f"
  done
fi
# 2) inside bundle.zip archives — extract-scan; loud warning if present
zhit=0
for z in "$ART"/matches/*/bundle.zip; do
  [ -f "$z" ] || continue
  if unzip -p "$z" 2>/dev/null | grep -qa -e "$KEYVAL"; then
    echo "WARNING: key value present inside $z — handle before publishing"; zhit=1
  fi
done
[ "$zhit" = 0 ] && echo "bundles clean of key value"
echo "OFFICIAL_RUN_DONE $(date -u +%FT%TZ)"
