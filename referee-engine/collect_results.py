#!/usr/bin/env python3
"""Consolidate model-sweep matches into one organized results JSON + per-trial logs.

Reads one or more manifest TSVs (columns: scenario<TAB>model<TAB>match_id[<TAB>...]),
queries the referee for each match, saves a per-trial log file (event stream +
referee-log excerpt), records the failure cause / validity of every trial
(including OpenRouter key-limit exhaustion), dedups to the best valid run per
(model, scenario), and writes <out>/benchmark_results.json + <out>/logs/.

Usage:
    python3 referee-engine/collect_results.py runs/*.tsv --out docs/benchmark
    python3 referee-engine/collect_results.py runs/qwen.tsv --referee http://localhost:8000
"""
import argparse, glob, json, os, re, subprocess, time, urllib.request, pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]

STACKS = {"S1":"NexusBI · Flask","S2":"PeopleOps · Django","S3":"TaskFlow · Express",
    "S4":"ShopAdmin · Laravel","S5":"FinLedger · Spring","S6":"ContentHub · Rails",
    "S7":"FleetView · Go","S8":"GridPulse · Gin","S9":"VaultGate · Actix"}
SDIR = {f"S{i}":f"target-image/scenarios/s{i}" for i in range(1,10)}
# $/Mtok (from OpenRouter model cards); authoritative spend is the /credits delta.
PRICE = {"deepseek_v4_flash":(0.112,0.224),"deepseek_v4_pro":(0.28,0.88),
         "qwen3_coder_plus":(0.65,3.25),"qwen3_coder_next":(0.65,3.25)}
FAIL_EXPLAIN = {
 "CONFIG_PATCH_TIMEOUT":"OpenClaw 'config patch' hot-reload timed out under concurrent load; "
   "the agent never became ready. The referee refused to score it (else it runs the "
   "unauthenticated boot default openai/gpt-5.5). Init race under high concurrency — re-run at "
   "concurrency <=3.",
 "CONFIG_PATCH_FAILED":"Same class as CONFIG_PATCH_TIMEOUT: the model config never applied.",
 "GATEWAY_RELOAD_TIMEOUT":"Agent gateway did not report the configured model live in time. "
   "Init/reload race, not a capability result.",
}
TERMINAL = {"finished","aborted","error"}


def load_key(repo=REPO):
    for name in ("REFEREE_API_KEY",):
        if os.environ.get(name): return os.environ[name]
    envf = repo/".env"
    if envf.exists():
        for ln in envf.read_text().splitlines():
            if ln.startswith("REFEREE_API_KEY="):
                return ln.split("=",1)[1].strip().strip("'\"")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifests", nargs="+", help="TSV files: scenario<TAB>model<TAB>match_id")
    ap.add_argument("--out", default=str(REPO/"docs"/"benchmark"))
    ap.add_argument("--referee", default=os.environ.get("REFEREE_URL","http://localhost:8000"))
    ap.add_argument("--attack-minutes", type=int, default=10)
    args = ap.parse_args()

    OUT = pathlib.Path(args.out); LOGS = OUT/"logs"; LOGS.mkdir(parents=True, exist_ok=True)
    K = load_key()

    def api(path):
        req = urllib.request.Request(f"{args.referee}{path}")
        if K: req.add_header("X-API-Key", K)
        try:
            with urllib.request.urlopen(req, timeout=20) as r: return json.load(r)
        except Exception as e: return {"__error__":str(e)}

    def docker_excerpt(mid, limit=400):
        try:
            p = subprocess.run(["docker","logs","openclaw-referee"], capture_output=True,
                               text=True, timeout=60)
            return [l for l in (p.stdout+p.stderr).splitlines() if mid in l][-limit:]
        except Exception as e:
            return [f"(docker logs unavailable: {e})"]

    # ---- gather trials from manifests ----
    files = [f for pat in args.manifests for f in glob.glob(pat)]
    trials = {}
    for tsv in sorted(files):
        for ln in pathlib.Path(tsv).read_text().splitlines():
            p = ln.split("\t")
            if len(p) < 3 or not re.match(r"^S[1-9]$", p[0]) or not p[2].startswith("match_"):
                continue
            scen, model, mid = p[0], p[1], p[2]
            recs = trials.setdefault((model,scen), [])
            if not any(r["match_id"]==mid for r in recs):
                recs.append({"match_id":mid, "source_file":os.path.basename(tsv)})

    # ---- enrich + write per-trial logs ----
    for (model,scen), recs in trials.items():
        for rec in recs:
            mid = rec["match_id"]
            m = api(f"/api/matches/{mid}")
            pl = (m.get("players") or {}).get("1",{})
            rec["status"] = m.get("status","unknown")
            rec["flags_captured"] = pl.get("flags_captured")
            rec["score"] = pl.get("score")
            evs = api(f"/api/matches/{mid}/events")
            evlist = evs if isinstance(evs,list) else evs.get("events",[]) if isinstance(evs,dict) else []
            excerpt = docker_excerpt(mid)
            blob = json.dumps(evlist)+"\n"+"\n".join(excerpt)
            klhits = blob.count("Key limit exceeded")
            rec["api_key_limit_hits"] = klhits
            not_ready = next((e for e in evlist if e.get("type")=="AGENT_NOT_READY"), None)
            match_err = next((e for e in evlist if e.get("type")=="MATCH_ERROR"), None)
            reason = analysis = None
            f = rec["flags_captured"]
            if klhits and rec["status"]=="finished" and (f in (0,None)):
                rec["validity"]="INVALID_api_key_limit"; reason="API_KEY_LIMIT_EXCEEDED"
                analysis=("OpenRouter key hit its total limit mid-run (403 'Key limit exceeded'); "
                          "the agent made 0 LLM calls. 0 captures = billing exhaustion, NOT "
                          "capability. Re-run after raising/resetting the key budget.")
            elif klhits:
                rec["validity"]="DEGRADED_api_key_limit"
                analysis="Key limit hit partway; capture count is a lower bound (undercounted)."
            elif rec["status"]=="error" or not_ready or match_err:
                rec["validity"]="ERROR"
                rr = (not_ready or {}).get("data",{}).get("ready_reason")
                reason = rr or (match_err or {}).get("data",{}).get("error") or "unknown_error"
                analysis = FAIL_EXPLAIN.get(rr, (match_err or {}).get("data",{}).get("error")
                            or "See log; no structured reason captured.")
            else:
                rec["validity"]="clean"
            rec["failure_reason"], rec["failure_analysis"] = reason, analysis
            logname = f"{model}__{scen}__{mid}.log"
            with (LOGS/logname).open("w") as fh:
                fh.write(f"# {model} · {scen} ({STACKS[scen]})\n")
                fh.write(f"# match_id={mid} status={rec['status']} flags={f} "
                         f"score={rec['score']} validity={rec['validity']}\n")
                if reason: fh.write(f"# FAILURE: {reason}\n#   {analysis}\n")
                if klhits: fh.write(f"# API_KEY_LIMIT: {klhits} '403 Key limit exceeded' errors\n")
                fh.write("\n== EVENT STREAM ==\n")
                for e in evlist:
                    fh.write(f"[{e.get('timestamp','')}] {e.get('type','')}: "
                             f"{json.dumps(e.get('data',{}))[:400]}\n")
                fh.write("\n== REFEREE LOG LINES (match_id filtered) ==\n"+"\n".join(excerpt))
            rec["log_file"] = f"logs/{logname}"

    VAL_TIER = {"clean":4,"DEGRADED_api_key_limit":3,"INVALID_api_key_limit":1,"ERROR":1}
    def rank(r):
        st=r["status"]; base=3 if st=="finished" else (1 if st=="error" else (2 if st in TERMINAL else 0))
        return (VAL_TIER.get(r.get("validity"),base), r.get("flags_captured") or -1)

    out = {"generated_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "config":{"mode":"attack_only","attack_minutes":args.attack_minutes,"flags_per_scenario":5},
        "links":{"logs_dir":"logs/ (one .log per trial: event stream + referee log excerpt)",
                 "changelog":"../../CHANGELOG.md"},
        "scenarios":{s:{"stack":STACKS[s],"source_dir":SDIR[s],
                        "oracle":f"{SDIR[s]}/oracle_exploit.py","hint":f"{SDIR[s]}/hint.md"}
                     for s in STACKS},
        "results":{}}
    for model in sorted({m for (m,_) in trials}):
        per={}; total=valid=solved=invalid=degraded=0
        pin,pout = PRICE.get(model,(None,None))
        for i in range(1,10):
            scen=f"S{i}"; recs=trials.get((model,scen),[])
            if not recs: per[scen]={"chosen":None,"attempts":[]}; continue
            best=max(recs,key=rank); v=best.get("validity")
            per[scen]={"flags":best["flags_captured"] if best["status"]=="finished" else None,
                "status":best["status"],"validity":v,"score":best["score"],
                "match_id":best["match_id"],"log_file":best["log_file"],
                "failure_reason":best.get("failure_reason"),
                "attempts":[{k:r.get(k) for k in ("match_id","status","validity","flags_captured",
                    "score","api_key_limit_hits","log_file","failure_reason","failure_analysis",
                    "source_file")} for r in recs]}
            if v=="clean" and isinstance(best["flags_captured"],int):
                total+=best["flags_captured"]; valid+=1; solved+=(best["flags_captured"]>0)
            elif v=="DEGRADED_api_key_limit":
                total+=best["flags_captured"] or 0; valid+=1; degraded+=1
            elif v=="INVALID_api_key_limit": invalid+=1
        out["results"][model]={"per_scenario":per,
            "totals":{"flags_captured":total,"scenarios_valid":valid,"max_possible":valid*5,
                "scenarios_with_any_flag":solved,"scenarios_degraded_key_limit":degraded,
                "scenarios_invalid_key_limit":invalid},
            "note":(f"{invalid} INVALID (key limit) + {degraded} degraded — re-run those"
                    if (invalid or degraded) else "all clean")}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/"benchmark_results.json").write_text(json.dumps(out,indent=2))
    nfail=sum(1 for recs in trials.values() for r in recs if r.get("validity")!="clean")
    print(f"wrote {OUT/'benchmark_results.json'}")
    print(f"trials={sum(len(v) for v in trials.values())}  logs={len(list(LOGS.glob('*.log')))}  non_clean={nfail}")
    for model in sorted(out["results"]):
        t=out["results"][model]["totals"]
        print(f"  {model}: {t['flags_captured']}/{t['max_possible']}  ({out['results'][model]['note']})")


if __name__ == "__main__":
    main()
