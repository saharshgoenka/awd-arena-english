"""
Batch runner — RESEARCH_PLAN.md §6.2 R5.

Reads a bench config (bench/v1.yaml), enumerates the (phase × model × scenario × mode × k)
grid, and dispatches each cell as a MatchConfig POST to the referee HTTP API. Polls until
the referee writes a per-match JSONL file (handled by run_writer.write_match_jsonl in
end_match), then moves on.

Usage:
    OPENROUTER_API_KEY=... python -m bench --config bench/v1.yaml

Notes:
  - The referee must already be running (docker compose up referee-engine).
  - The cumulative-budget cap is enforced by skipping remaining cells once the
    measured spend (from the JSONL token_usage + a per-model $/Mtok price table)
    crosses the cap. For free-tier OpenRouter models the price is $0; if a free
    model rate-limits and the runner sees DNFs piling up, it slows the dispatch.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # PyYAML
except ImportError:
    print("PyYAML is required: pip install pyyaml", file=sys.stderr)
    raise

logging.basicConfig(
    level=os.environ.get("BENCH_LOG_LEVEL", "INFO"),
    format="[bench] %(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("bench")


# Per-Mtoken pricing for OpenRouter slugs used in Phase A/B. Numbers are pulled
# from OpenRouter's model pages (verified 2026-05-21 — see docs/results.md §2.6).
# Cached-read pricing is not yet applied: the bench summary is an estimate to
# compare against OpenRouter `/auth/key` (which is authoritative). Cache savings
# can subtract 10–20% for DeepSeek; this estimate is an upper bound.
#
# Keyed by **paid slug** because bench yamls now reference paid endpoints
# directly (the :free variants 429-rate-limited mid-match during Phase A smoke).
# :free keys are kept as aliases so older bench yamls still resolve.
PRICES = {
    # DeepSeek-V4-Flash — paid. Cached read is $0.022/M but applied only on
    # repeated prompts; this estimate treats input as fully uncached.
    "deepseek/deepseek-v4-flash":      {"in_per_mtok": 0.112, "out_per_mtok": 0.224},
    "deepseek/deepseek-chat":          {"in_per_mtok": 0.27,  "out_per_mtok": 1.10},
    # Qwen3-235B-A22B-2507 — 235B/22B-active MoE, used as the Phase A 2nd model.
    "qwen/qwen3-235b-a22b-2507":       {"in_per_mtok": 0.071, "out_per_mtok": 0.10},
    # Qwen3-Coder (480B/A35B) — used briefly during Phase A cost calibration
    # then swapped out for the cheaper 235B-A22B (docs/results.md §2.6).
    "qwen/qwen3-coder":                {"in_per_mtok": 0.22,  "out_per_mtok": 1.80},
    "qwen/qwen-2.5-coder-32b-instruct":{"in_per_mtok": 0.18,  "out_per_mtok": 0.18},
    # Llama-3.3-70B-Instruct — paid OpenRouter pricing verified 2026-05-22.
    # (Earlier $0.25 / $0.65 placeholder was a guess; real prices much lower.)
    "meta-llama/llama-3.3-70b-instruct":{"in_per_mtok": 0.10, "out_per_mtok": 0.32},
    # Llama 4 Scout — cheaper second-model replacement for Qwen in one-off samples.
    "meta-llama/llama-4-scout":        {"in_per_mtok": 0.08,  "out_per_mtok": 0.30},
    # Current sample_runner / bench/samples.yaml roster. Prices are ESTIMATES
    # (pro tier > flash; coder-next mirrors qwen3-coder) pending confirmation
    # against OpenRouter /models — the authoritative spend is the /credits delta
    # in fetch_openrouter_total_usage; this table is only the pre-flight estimate.
    "deepseek/deepseek-v4-pro":        {"in_per_mtok": 0.28,  "out_per_mtok": 0.88},
    "qwen/qwen3-coder-next":           {"in_per_mtok": 0.22,  "out_per_mtok": 1.80},
}

# Conservative fallback for a slug missing from PRICES: the most expensive
# per-token rates in the table. Used so an unpriced/typo'd slug over-estimates
# rather than silently reporting $0 and slipping past the cumulative cost cap.
_FALLBACK_PRICE = {
    "in_per_mtok": max(p["in_per_mtok"] for p in PRICES.values()),
    "out_per_mtok": max(p["out_per_mtok"] for p in PRICES.values()),
}

# Older bench yamls may still pass :free slugs; resolve them to the paid entry.
_FREE_TO_PAID = {
    "deepseek/deepseek-chat:free":            "deepseek/deepseek-chat",
    "qwen/qwen-2.5-coder-32b-instruct:free":  "qwen/qwen-2.5-coder-32b-instruct",
    "meta-llama/llama-3.3-70b-instruct:free": "meta-llama/llama-3.3-70b-instruct",
}

# Backwards-compat alias for older imports.
PAID_FALLBACK_PRICES = PRICES


@dataclass
class BenchCell:
    phase_name: str
    model_id: str
    openrouter_slug: str
    model_label: str
    scenario_id: str
    mode: str
    k_index: int
    k_total: int
    # head_to_head only: the second agent in the match.
    opponent_id: Optional[str] = None
    opponent_slug: Optional[str] = None
    opponent_label: Optional[str] = None

    @property
    def cell_label(self) -> str:
        suffix = f"vs{self.opponent_id}" if self.opponent_id else ""
        return f"{self.phase_name}/{self.model_id}{suffix}/{self.scenario_id}/{self.mode}/k{self.k_index}"


@dataclass
class BenchState:
    cells_planned: int = 0
    cells_dispatched: int = 0
    cells_completed: int = 0
    cells_dnf: int = 0
    estimated_spend_usd: float = 0.0
    per_match_records: List[Dict[str, Any]] = field(default_factory=list)


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def enumerate_cells(cfg: Dict[str, Any]) -> List[BenchCell]:
    models_by_id = {m["id"]: m for m in cfg["models"]}
    cells: List[BenchCell] = []
    for phase in cfg.get("phases", []):
        grid = phase.get("grid", {})
        k_total = int(grid.get("k", 1))
        modes = grid.get("modes", [])
        scenarios = grid.get("scenarios", [])

        # Solo-mode iteration (defense_only / attack_only): one cell per
        # (model, scenario, mode, k). HVH iteration is below — `pairs:` field.
        for model_id in grid.get("models", []):
            m = models_by_id[model_id]
            for scenario_id in scenarios:
                for mode in modes:
                    if mode in ("head_to_head", "hvh"):
                        continue  # HVH cells come from `pairs:`, not `models:`
                    for k_index in range(1, k_total + 1):
                        cells.append(BenchCell(
                            phase_name=phase["name"],
                            model_id=model_id,
                            openrouter_slug=m["openrouter_slug"],
                            model_label=m["label"],
                            scenario_id=scenario_id,
                            mode=mode,
                            k_index=k_index,
                            k_total=k_total,
                        ))

        # HVH iteration: each pair `[model_a, model_b]` produces one cell per
        # (scenario, k). Only fires when one of the modes is head_to_head/hvh.
        if any(mode in ("head_to_head", "hvh") for mode in modes):
            for pair in grid.get("pairs", []) or []:
                a_id, b_id = pair["a"], pair["b"]
                a, b = models_by_id[a_id], models_by_id[b_id]
                for scenario_id in scenarios:
                    for mode in modes:
                        if mode not in ("head_to_head", "hvh"):
                            continue
                        for k_index in range(1, k_total + 1):
                            cells.append(BenchCell(
                                phase_name=phase["name"],
                                model_id=a_id,
                                openrouter_slug=a["openrouter_slug"],
                                model_label=a["label"],
                                scenario_id=scenario_id,
                                mode=mode,
                                k_index=k_index,
                                k_total=k_total,
                                opponent_id=b_id,
                                opponent_slug=b["openrouter_slug"],
                                opponent_label=b["label"],
                            ))
    return cells


def build_match_config(
    cell: BenchCell,
    cfg: Dict[str, Any],
    api_key: str,
) -> Dict[str, Any]:
    """Compose the JSON body posted to /api/matches/start."""
    defaults = cfg.get("defaults", {})
    scenario = cfg["scenarios"][cell.scenario_id]
    bench_run_id = cfg.get("bench_run_id")

    # Player roster depends on mode (see RESEARCH_PLAN.md §4.2 + referee changes for R3):
    #   - hvh:           2+ agent players, one defender slot per player.
    #   - defense_only:  1 agent player (defends own target); referee runs the
    #                    oracle exploit during the attack window.
    #   - attack_only:   1 agent player (attacker) + 1 non-agent "victim" player
    #                    that owns a target but never patches; the agent attacks it.
    if cell.mode == "defense_only":
        players = [{
            "id": 1,
            "name": cell.model_label,
            "model": cell.openrouter_slug,
            "is_agent": True,
        }]
    elif cell.mode == "attack_only":
        players = [
            {
                "id": 1,
                "name": cell.model_label,
                "model": cell.openrouter_slug,
                "is_agent": True,
            },
            {
                "id": 2,
                "name": "unpatched-victim",
                "model": None,
                "is_agent": False,
            },
        ]
    elif cell.mode == "head_to_head" or cell.mode == "hvh":
        # HVH cells specify a pair via `hvh.opponent_slug` / `hvh.opponent_label`
        # in the yaml's phase-grid (so the bench grid can enumerate pairs without
        # the model-set field exploding combinatorially). The cell's primary
        # model is player 1, the opponent is player 2.
        opp_slug = getattr(cell, "opponent_slug", None)
        opp_label = getattr(cell, "opponent_label", None) or "opponent"
        if not opp_slug:
            raise ValueError(
                f"head_to_head cell {cell.cell_label} missing opponent_slug; "
                f"add `opponent: {{slug, label}}` under the phase grid."
            )
        players = [
            {
                "id": 1,
                "name": cell.model_label,
                "model": cell.openrouter_slug,
                "is_agent": True,
            },
            {
                "id": 2,
                "name": opp_label,
                "model": opp_slug,
                "is_agent": True,
            },
        ]
    else:
        raise ValueError(f"Bench runner does not yet build configs for mode={cell.mode}")

    body = {
        "match": defaults.get("match", {}),
        "llm": {
            **defaults.get("llm", {}),
            "apiKey": api_key,
            "model": cell.openrouter_slug,
        },
        "players": players,
        "scoring": defaults.get("scoring", {}),
        "flags": defaults.get("flags", {}),
        "target_image": scenario["target_image"],
        "oracle_image": scenario.get("oracle_image"),
        "mode": cell.mode,
        "scenario_id": cell.scenario_id,
        "bench_run_id": bench_run_id,
        "token_budget_input": defaults.get("token_budget_input", 100_000),
        "token_budget_output": defaults.get("token_budget_output", 25_000),
        "runs_dir": cfg.get("runs_dir", "referee-engine/runs/v1"),
    }
    return body


def post_match(referee_url: str, body: Dict[str, Any], api_key_header: Optional[str]) -> str:
    url = referee_url.rstrip("/") + "/api/matches/start"
    headers = {"Content-Type": "application/json"}
    if api_key_header:
        headers["X-API-Key"] = api_key_header
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["match_id"]


def poll_match_jsonl(matches_dir: Path, match_id: str, total_timeout_s: int) -> Optional[Dict[str, Any]]:
    """Block until the referee writes runs/v1/matches/<match_id>.jsonl, or timeout."""
    path = matches_dir / f"{match_id}.jsonl"
    deadline = time.time() + total_timeout_s
    while time.time() < deadline:
        if path.exists() and path.stat().st_size > 0:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    line = f.readline()
                return json.loads(line)
            except (OSError, json.JSONDecodeError) as e:
                log.warning(f"[{match_id}] partial JSONL read ({e}); retrying")
        time.sleep(5)
    return None


_unpriced_slugs_warned: set = set()


def fetch_openrouter_total_usage(api_key: str) -> Optional[float]:
    """Return the OpenRouter account's cumulative spend in USD.

    Used to bracket each match with a before/after delta — gives us the exact
    spend per match even when OpenClaw's session log omits usage data (which
    it does for defense_only matches, where the trajectory schema carries no
    token counts). Returns None on any HTTP / parse failure so the caller can
    fall back to the token-based estimate.
    """
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/credits",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return float((payload.get("data") or {}).get("total_usage"))
    except Exception as exc:
        log.warning(f"fetch_openrouter_total_usage failed: {exc}")
        return None


def estimate_match_cost(record: Dict[str, Any], openrouter_slug: str) -> float:
    """Convert token_usage into $ using the PRICES table.

    Resolves :free → paid alias for older yamls. Logs once per unknown slug so
    the warning isn't lost in the per-match summary stream.
    """
    usage = record.get("token_usage") or {}
    slug = _FREE_TO_PAID.get(openrouter_slug, openrouter_slug)
    price = PRICES.get(slug)
    if not price:
        if openrouter_slug not in _unpriced_slugs_warned:
            log.warning(
                f"estimate_match_cost: no price entry for slug '{openrouter_slug}'; "
                f"using conservative fallback rates. Add it to bench.PRICES with "
                f"values from OpenRouter for an accurate estimate."
            )
            _unpriced_slugs_warned.add(openrouter_slug)
        price = _FALLBACK_PRICE
    in_tok = usage.get("input_tokens", 0) or 0
    out_tok = usage.get("output_tokens", 0) or 0
    return (in_tok / 1_000_000) * price["in_per_mtok"] + (out_tok / 1_000_000) * price["out_per_mtok"]


def run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    cells = enumerate_cells(cfg)
    if not cells:
        log.error("No cells to run. Check bench config phases[].grid")
        return 2

    runs_dir = Path(cfg.get("runs_dir", "referee-engine/runs/v1"))
    matches_dir = runs_dir / "matches"
    matches_dir.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("openrouter")
    if not api_key:
        log.error("OPENROUTER_API_KEY (or 'openrouter') env var is not set")
        return 2
    referee_api_key = os.environ.get("REFEREE_API_KEY")

    state = BenchState(cells_planned=len(cells))
    budget_cap = float(cfg.get("budget_cap_usd", 5.0))

    log.info(f"Bench plan: {len(cells)} matches across phases "
             f"{sorted({c.phase_name for c in cells})}. Budget cap ${budget_cap:.2f}.")

    for cell in cells:
        if state.estimated_spend_usd >= budget_cap:
            log.error(f"Budget cap ${budget_cap:.2f} reached; skipping {cell.cell_label}")
            break

        body = build_match_config(cell, cfg, api_key)
        log.info(f"=== Dispatching {cell.cell_label} ===")
        if args.dry_run:
            log.info(f"DRY RUN — would POST: {json.dumps({k: v for k, v in body.items() if k != 'llm'})}")
            state.cells_dispatched += 1
            continue

        # Snapshot OpenRouter cumulative spend right before dispatch so we can
        # back-compute exact per-match spend regardless of whether the session
        # log carries usage data. defense_only matches in particular need this
        # because OpenClaw's trajectory schema omits token counts entirely.
        spend_before = fetch_openrouter_total_usage(api_key)

        try:
            match_id = post_match(args.referee_url, body, referee_api_key)
        except urllib.error.HTTPError as e:
            log.error(f"[{cell.cell_label}] referee rejected: {e.code} {e.read()[:300] if e.fp else ''}")
            state.cells_dnf += 1
            continue
        except Exception as e:
            log.exception(f"[{cell.cell_label}] dispatch failed: {e}")
            state.cells_dnf += 1
            continue

        state.cells_dispatched += 1
        log.info(f"[{cell.cell_label}] match_id={match_id}; polling for completion")

        # Total per-match timeout: 3× declared (defense + attack) + 5min slack.
        # Matches occasionally over-run their declared phase length (observed
        # 2026-05-21: a 10-min match spent 36 min in defense phase). The 3×
        # multiplier absorbs that without unbounded waits; if we hit it, we
        # actively end the match via the referee API so it stops spending.
        phases = cfg.get("defaults", {}).get("match", {}).get("phases", {})
        declared_total = int(phases.get("defense", 900)) + int(phases.get("attack", 1500))
        match_total = declared_total * 3 + 300
        record = poll_match_jsonl(matches_dir, match_id, total_timeout_s=match_total)
        if record is None:
            log.error(f"[{cell.cell_label}] JSONL never appeared within {match_total}s; "
                      f"force-ending match to stop spend")
            try:
                end_url = args.referee_url.rstrip("/") + f"/api/matches/{match_id}/end"
                req = urllib.request.Request(end_url, method="POST")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    log.warning(f"[{cell.cell_label}] force-end response: {resp.status}")
                # Give the referee a moment to write the JSONL after end_match
                record = poll_match_jsonl(matches_dir, match_id, total_timeout_s=60)
            except Exception as e:
                log.error(f"[{cell.cell_label}] force-end failed: {e}")
            if record is None:
                state.cells_dnf += 1
                continue

        if record.get("dnf"):
            state.cells_dnf += 1
            log.warning(f"[{cell.cell_label}] DNF: {record.get('dnf_reason')}")
        else:
            state.cells_completed += 1

        # Token-based estimate (works for atk-only / HVH; reports $0 for def-only
        # because OpenClaw's trajectory schema omits usage data).
        cost_est = estimate_match_cost(record, cell.openrouter_slug)

        # OpenRouter-measured spend delta (works for every mode, captures oracle
        # path costs too). Wait a beat so OpenRouter has flushed billing for any
        # in-flight requests this match made.
        time.sleep(3)
        spend_after = fetch_openrouter_total_usage(api_key)
        if spend_before is not None and spend_after is not None:
            cost_measured = max(0.0, spend_after - spend_before)
        else:
            cost_measured = None

        # Prefer the measured delta when available; fall back to the token-based
        # estimate so the cumulative-spend gate still works if OpenRouter's API
        # is briefly unreachable.
        cost = cost_measured if cost_measured is not None else cost_est
        state.estimated_spend_usd += cost
        state.per_match_records.append({
            "cell": cell.cell_label,
            "match_id": match_id,
            "dnf": record.get("dnf"),
            "estimated_cost_usd": round(cost_est, 5),
            "measured_cost_usd": round(cost_measured, 5) if cost_measured is not None else None,
        })
        if cost_measured is not None:
            log.info(
                f"[{cell.cell_label}] done; measured ${cost_measured:.5f} "
                f"(est ${cost_est:.5f}); cumulative ${state.estimated_spend_usd:.4f}"
            )
        else:
            log.info(f"[{cell.cell_label}] done; est cost ${cost_est:.5f}; cumulative ${state.estimated_spend_usd:.4f}")

    summary_path = runs_dir / f"bench_summary_{cfg.get('bench_run_id', 'run')}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "bench_run_id": cfg.get("bench_run_id"),
            "cells_planned": state.cells_planned,
            "cells_dispatched": state.cells_dispatched,
            "cells_completed": state.cells_completed,
            "cells_dnf": state.cells_dnf,
            "estimated_spend_usd": round(state.estimated_spend_usd, 4),
            "budget_cap_usd": budget_cap,
            "matches": state.per_match_records,
        }, f, indent=2)
    log.info(f"Wrote bench summary to {summary_path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to bench yaml (e.g. bench/v1.yaml)")
    ap.add_argument("--referee-url", default=os.environ.get("REFEREE_URL", "http://localhost:8000"))
    ap.add_argument("--dry-run", action="store_true",
                    help="Enumerate the grid and log what would be dispatched, but do not POST")
    return run(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())
