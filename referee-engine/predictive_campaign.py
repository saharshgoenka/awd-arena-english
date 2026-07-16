"""Plan and launch the pre-registered AAAI-27 isolated k=3 campaign.

The exploratory k=1 grid selected the models. This runner creates the two
fresh repetitions that take every selected model/scenario/mode cell to k=3,
without putting the selection run into the primary predictor. It deliberately
requires the central S1/S5/S7 predictor inputs to finish before broader runs
can be launched.

Examples:
  python predictive_campaign.py --prepare
  python predictive_campaign.py --launch --stage central
  python predictive_campaign.py --launch --stage broader \
      --predictor-freeze-file path/to/predictor-freeze.json
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sample_runner import (
    DEFAULT_CONFIG as SAMPLE_CONFIG,
    SampleArgs,
    build_sample_body,
    load_config as load_sample_config,
    load_openrouter_key,
    post_match,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_DIR = REPO_ROOT / "bench" / "manifests"
CAMPAIGN_ID = "aaai27-predictive-k3"
SELECTED_MODELS = (
    "minimax_m3",
    "deepseek_v4_pro",
    "deepseek_v4_flash",
    "glm_4_5_air",
)
CENTRAL_SCENARIOS = ("S1", "S5", "S7")
BROADER_SCENARIOS = ("S2", "S3", "S4", "S6", "S8", "S9")
MODES = ("attack_only", "defense_only")
TERMINAL_STATUSES = {"finished", "error", "aborted"}


def _make_jobs(stage: str, scenarios: Tuple[str, ...], seed: int) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    for model_id in SELECTED_MODELS:
        for scenario in scenarios:
            for mode in MODES:
                for fresh_repeat, confirmatory_k in ((1, 2), (2, 3)):
                    jobs.append({
                        "stage": stage,
                        "model_id": model_id,
                        "scenario": scenario,
                        "mode": mode,
                        "fresh_repeat": fresh_repeat,
                        "confirmatory_k": confirmatory_k,
                        "predictor_input": stage == "central_isolated",
                        "defense_minutes": 0 if mode == "attack_only" else 15,
                        "attack_minutes": 10 if mode == "attack_only" else 3,
                    })
    random.Random(seed).shuffle(jobs)
    for index, job in enumerate(jobs, start=1):
        job["job_id"] = f"{stage}-{index:03d}"
    return jobs


def build_campaign_jobs(seed: int = 20260716) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return deterministic, randomized central and broader isolated jobs."""
    return (
        _make_jobs("central_isolated", CENTRAL_SCENARIOS, seed),
        _make_jobs("broader_isolated", BROADER_SCENARIOS, seed + 1),
    )


def _manifest_path(output_dir: Path) -> Path:
    return output_dir / f"{CAMPAIGN_ID}-manifest.json"


def write_campaign_manifest(output_dir: Path, seed: int = 20260716) -> Path:
    """Create the frozen plan; this function never contacts a model or referee."""
    central, broader = build_campaign_jobs(seed)
    manifest = {
        "campaign": CAMPAIGN_ID,
        "status": "planned_not_started",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "selection_note": (
            "Exploratory k=1 selected the models. These are the two fresh "
            "repetitions used for primary predictor estimation."
        ),
        "launch_policy": {
            "central_must_finish_before_awd": True,
            "broader_requires_predictor_freeze": True,
            "max_concurrency": 3,
            "retry_only_invalid_runs": True,
        },
        "stages": {
            "central_isolated": central,
            "broader_isolated": broader,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    path = _manifest_path(output_dir)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def read_manifest(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def build_job_body(job: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """Build a scored isolated match from one frozen manifest job."""
    config = load_sample_config(SAMPLE_CONFIG)
    body = build_sample_body(
        config,
        SampleArgs(
            scenario=job["scenario"],
            mode=job["mode"],
            model_a=job["model_id"],
            model_b=None,
            defense_minutes=job["defense_minutes"],
            attack_minutes=job["attack_minutes"],
            bench_run_id=f"{CAMPAIGN_ID}-{job['stage'].replace('_', '-')}",
        ),
        api_key,
    )
    body["match"] = copy.deepcopy(body["match"])
    body["match"]["name"] = f"{CAMPAIGN_ID}/{job['job_id']}"
    return body


def _status_url(referee_url: str, match_id: str) -> str:
    return referee_url.rstrip("/") + f"/api/matches/{match_id}"


def _get_match_status(referee_url: str, match_id: str) -> Dict[str, Any]:
    headers = {}
    if os.environ.get("REFEREE_API_KEY"):
        headers["X-API-Key"] = os.environ["REFEREE_API_KEY"]
    request = urllib.request.Request(_status_url(referee_url, match_id), headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_terminal_match(
    referee_url: str,
    match_id: str,
    timeout_seconds: int,
    poll_seconds: int = 20,
) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    latest: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = _get_match_status(referee_url, match_id)
        if latest.get("status") in TERMINAL_STATUSES:
            return latest
        time.sleep(poll_seconds)
    latest["status"] = "timeout"
    latest["timeout_seconds"] = timeout_seconds
    return latest


def _run_job(job: Dict[str, Any], api_key: str, referee_url: str) -> Dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        match_id = post_match(referee_url, build_job_body(job, api_key))
        declared_seconds = (job["defense_minutes"] + job["attack_minutes"]) * 60
        status = _wait_for_terminal_match(
            referee_url,
            match_id,
            timeout_seconds=declared_seconds * 3 + 300,
        )
        return {
            **job,
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "match_id": match_id,
            "status": status.get("status"),
            "match_status": status,
        }
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError, OSError) as exc:
        return {
            **job,
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": "dispatch_error",
            "error": str(exc),
        }


def launch_stage(
    manifest_path: Path,
    stage: str,
    referee_url: str,
    output_dir: Path,
    max_concurrency: int = 3,
) -> Path:
    """Launch one frozen stage and persist an append-only result ledger."""
    manifest = read_manifest(manifest_path)
    stage_name = f"{stage}_isolated"
    jobs = manifest["stages"][stage_name]
    api_key = load_openrouter_key()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY/openrouter is not configured in the environment or .env")

    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = output_dir / f"{CAMPAIGN_ID}-{stage_name}-ledger.json"
    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_concurrency) as pool:
        futures = [pool.submit(_run_job, job, api_key, referee_url) for job in jobs]
        for future in as_completed(futures):
            results.append(future.result())
            ledger_path.write_text(
                json.dumps({
                    "campaign": CAMPAIGN_ID,
                    "stage": stage_name,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "results": results,
                }, indent=2) + "\n",
                encoding="utf-8",
            )
    return ledger_path


def _parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--seed", type=int, default=20260716)
    parser.add_argument("--prepare", action="store_true", help="Write the frozen manifest only (default).")
    parser.add_argument("--launch", action="store_true", help="Launch the chosen stage (explicit opt-in).")
    parser.add_argument("--stage", choices=("central", "broader"), default="central")
    parser.add_argument("--referee-url", default=os.environ.get("REFEREE_URL", "http://localhost:8000"))
    parser.add_argument("--runs-dir", type=Path, default=REPO_ROOT / "referee-engine" / "runs" / CAMPAIGN_ID)
    parser.add_argument(
        "--predictor-freeze-file",
        type=Path,
        help="Required to launch broader isolated coverage after central predictor inputs are frozen.",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = _parse_args(argv)
    path = write_campaign_manifest(args.manifest_dir, args.seed)
    manifest = read_manifest(path)
    central_count = len(manifest["stages"]["central_isolated"])
    broader_count = len(manifest["stages"]["broader_isolated"])
    print(f"manifest={path}")
    print(f"central_jobs={central_count}")
    print(f"broader_jobs={broader_count}")

    if args.launch:
        if args.stage == "broader" and not args.predictor_freeze_file:
            print("Refusing broader launch: --predictor-freeze-file is required.", file=sys.stderr)
            return 2
        if args.stage == "broader" and not args.predictor_freeze_file.exists():
            print("Refusing broader launch: predictor freeze file does not exist.", file=sys.stderr)
            return 2
        try:
            ledger = launch_stage(path, args.stage, args.referee_url, args.runs_dir)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(f"ledger={ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
