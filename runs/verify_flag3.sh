#!/usr/bin/env bash
# verify_flag3.sh <scenario> <image_tag> — build, boot with injected flags, run oracle, print captures.
set -u; cd /Users/niranjanj/Desktop/ucla/awd-arena-english || exit 1
s="$1"; tag="$2"
F1="FLAG{$(openssl rand -hex 16)}"; F2="FLAG{$(openssl rand -hex 16)}"; F3="FLAG{$(openssl rand -hex 16)}"
F4="FLAG{$(openssl rand -hex 16)}"; F5="FLAG{$(openssl rand -hex 16)}"
echo "[$s] building $tag ..."
if ! docker build -q -t "$tag" "target-image/scenarios/$s" >/tmp/build_$s.log 2>&1; then
  echo "[$s] BUILD FAIL"; tail -5 /tmp/build_$s.log; exit 2; fi
cid=$(docker run -d -P -e FLAG_1="$F1" -e FLAG_2="$F2" -e FLAG_3="$F3" -e FLAG_4="$F4" -e FLAG_5="$F5" "$tag")
hp=$(docker port "$cid" 3000/tcp | head -1 | sed 's/.*://')
echo "[$s] container $cid on host port $hp; waiting for boot ..."
for i in $(seq 1 90); do curl -s -o /dev/null "localhost:$hp/" && break; sleep 2; done
sleep 4
out=$(python3 "target-image/scenarios/$s/oracle_exploit.py" --target-host localhost --target-port "$hp" \
      --referee-url http://localhost:8000 --match-id verify-$s --attacker-id 0 --victim-id 0 \
      --budget-seconds 200 2>/tmp/oracle_$s.err)
echo "$out" | python3 -c "import sys,json
d=json.load(sys.stdin)
cap=[f['slot'] for f in d['flags_captured']]; miss=[f['slot'] for f in d['flags_missed']]
print(f\"[$s] captured={len(cap)}/5 {sorted(cap)}  missed={sorted(miss)}\")
print('[$s] FLAG3_OK' if 'flag_3' in cap else '[$s] FLAG3_FAIL')" || { echo "[$s] ORACLE PARSE FAIL"; echo "$out" | tail -5; tail -8 /tmp/oracle_$s.err; }
docker rm -f "$cid" >/dev/null 2>&1
