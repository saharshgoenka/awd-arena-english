#!/usr/bin/env python3
"""
Per-match log collector — one folder per match with EVERYTHING, untruncated.

For each match id it creates <out>/<model>__<scenario>__<match_id>/ containing:
  - match.json            referee match record (/api/matches/<id>)
  - submissions.json      per-flag submissions with success/reason/points
  - events.jsonl          FULL event stream, untruncated (collect_results caps at 400 chars)
  - referee.log           referee container log lines filtered to this match_id
  - scoring.jsonl         referee run record (player_metrics, flag_slot_inventory, submissions)
  - agent_trajectory.jsonl  the agent's full openclaw reasoning/tool trace (untruncated)
  - bundle.zip            the full player_code_export bundle (target code, agent session, summaries)
  - summary.md            human-readable per-flag capture summary

Usage:
  python3 referee-engine/collect_match_logs.py <match_id> [<match_id> ...] --out docs/benchmark/matches
  python3 referee-engine/collect_match_logs.py runs/deepseek_v4_pro.tsv --out docs/benchmark/matches
  # (a .tsv manifest is scenario<TAB>model<TAB>match_id per line)
"""
import argparse, json, os, subprocess, sys, urllib.request, zipfile, io
from pathlib import Path

REF_CONTAINER = os.environ.get("REFEREE_CONTAINER", "openclaw-referee")
REF_URL = os.environ.get("REFEREE_URL", "http://localhost:8000")


def api(path):
    try:
        req = urllib.request.Request(f"{REF_URL}{path}")
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except Exception as e:
        return {"_error": str(e)}


def ref_exec(cmd):
    """Run a shell command inside the referee container; return (stdout_bytes, ok)."""
    p = subprocess.run(["docker", "exec", REF_CONTAINER, "sh", "-c", cmd],
                       capture_output=True)
    return p.stdout, p.returncode == 0


def ref_cp(src, dst):
    p = subprocess.run(["docker", "cp", f"{REF_CONTAINER}:{src}", str(dst)],
                       capture_output=True)
    return p.returncode == 0


def referee_log_lines(mid, limit=5000):
    p = subprocess.run(["docker", "logs", REF_CONTAINER], capture_output=True)
    out = (p.stdout + p.stderr).decode("utf-8", "replace").splitlines()
    return [l for l in out if mid in l][-limit:]


def trajectory_from_bundle(zip_path):
    """Pull player_1's agent_session.log (the full openclaw trajectory) out of the bundle."""
    try:
        with zipfile.ZipFile(zip_path) as z:
            for n in z.namelist():
                if n.endswith("player_1/logs/agent_session.log"):
                    return z.read(n).decode("utf-8", "replace")
    except Exception:
        pass
    return None


def flag_summary(scoring):
    """Build a per-flag capture summary from the scoring run record."""
    try:
        pm = scoring["player_metrics"]["1"]
        subs = scoring.get("submissions", [])
        ok = [s["flag_slot"] for s in subs if s.get("success")]
        bad = [(s.get("flag_slot"), s.get("reason")) for s in subs if not s.get("success")]
        return pm.get("flags_captured"), ok, bad, scoring.get("time_to_first_flag_seconds")
    except Exception:
        return None, [], [], None


def collect_one(mid, scen, model, outroot: Path):
    match = api(f"/api/matches/{mid}")
    subs = api(f"/api/matches/{mid}/submissions")
    evs = api(f"/api/matches/{mid}/events")
    evlist = evs if isinstance(evs, list) else evs.get("events", []) if isinstance(evs, dict) else []

    # scoring run record from inside the referee
    scoring = {}
    raw, ok = ref_exec(f"cat /app/data/runs/v1/matches/match_{mid}.jsonl 2>/dev/null")
    if ok and raw.strip():
        try:
            scoring = json.loads(raw.decode("utf-8", "replace").strip().splitlines()[0])
        except Exception:
            pass
    scen = scen or scoring.get("scenario_id") or "S?"
    model = model or (scoring.get("players", [{}])[0].get("model") or "model").split("/")[-1]

    d = outroot / f"{model}__{scen}__match_{mid}"
    d.mkdir(parents=True, exist_ok=True)

    (d / "match.json").write_text(json.dumps(match, indent=2))
    (d / "submissions.json").write_text(json.dumps(subs, indent=2))
    with (d / "events.jsonl").open("w") as fh:
        for e in evlist:
            fh.write(json.dumps(e) + "\n")   # FULL event, no [:400] truncation
    (d / "referee.log").write_text("\n".join(referee_log_lines(mid)))
    if scoring:
        (d / "scoring.jsonl").write_text(json.dumps(scoring, indent=2))

    # bundle + agent trajectory
    bundle_dir = f"/app/data/exports/match_{mid}"
    listing, ok = ref_exec(f"ls {bundle_dir}/*.zip 2>/dev/null")
    if ok and listing.strip():
        zpath = listing.decode().strip().splitlines()[0]
        if ref_cp(zpath, d / "bundle.zip"):
            traj = trajectory_from_bundle(d / "bundle.zip")
            if traj:
                (d / "agent_trajectory.jsonl").write_text(traj)

    # human-readable summary
    cap, okslots, badslots, ttff = flag_summary(scoring)
    lines = [f"# {model} · {scen} · match_{mid}", ""]
    if scoring:
        lines += [f"- captured: **{cap}/5**", f"- flags: {okslots or '(none)'}",
                  f"- failed submissions: {badslots or '(none)'}",
                  f"- time to first flag: {ttff}s",
                  f"- mode: {scoring.get('mode')}  attack_seconds: {scoring.get('phases',{}).get('attack_seconds')}"]
    else:
        lines += ["- (no scoring record found — match may not have finished)"]
    lines += ["", "## files",
              "- events.jsonl — full untruncated event stream",
              "- agent_trajectory.jsonl — agent reasoning + tool calls (openclaw trace)",
              "- scoring.jsonl — player_metrics, submissions, flag_slot_inventory",
              "- referee.log / match.json / submissions.json / bundle.zip"]
    (d / "summary.md").write_text("\n".join(lines))
    print(f"{scen} match_{mid}: {cap if scoring else '?'}/5  -> {d}")
    return d


def parse_targets(items):
    """Each item is either a match_id or a .tsv manifest (scenario<TAB>model<TAB>match_id)."""
    out = []
    for it in items:
        p = Path(it)
        if p.suffix == ".tsv" and p.exists():
            for ln in p.read_text().splitlines():
                parts = ln.rstrip("\n").split("\t")
                if len(parts) >= 3 and parts[2].strip():
                    out.append((parts[2].strip().replace("match_", ""), parts[0], parts[1]))
        else:
            out.append((it.replace("match_", ""), None, None))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+", help="match_ids and/or .tsv manifests")
    ap.add_argument("--out", default="docs/benchmark/matches")
    args = ap.parse_args()
    outroot = Path(args.out)
    outroot.mkdir(parents=True, exist_ok=True)
    for mid, scen, model in parse_targets(args.targets):
        try:
            collect_one(mid, scen, model, outroot)
        except Exception as e:
            print(f"match {mid}: ERROR {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
