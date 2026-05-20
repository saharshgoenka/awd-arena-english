"""
Per-match JSONL writer — RESEARCH_PLAN.md §6.2 R4.

Writes one file per match at $REFEREE_RUNS_DIR/matches/<match_id>.jsonl. The
schema is intentionally flat: one match → one file containing a single JSON
object per line (always one line in practice, kept as JSONL for easy appending
of post-hoc annotations later). The analysis pipeline (§6.3 A1) globs over
this directory.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("referee.run_writer")

DEFAULT_RUNS_DIR = os.environ.get("REFEREE_RUNS_DIR", "/app/data/runs/v1")


def _safe_isoformat(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _flag_slot_inventory(match) -> Dict[int, Dict[str, str]]:
    """Snapshot the latest active flag set per player at end-of-match."""
    inventory: Dict[int, Dict[str, str]] = {}
    fm = getattr(match, "flag_manager", None)
    active = getattr(fm, "active_flags", {}) if fm else {}
    for pid, slots in active.items():
        if isinstance(slots, dict):
            inventory[pid] = dict(slots)
    return inventory


def _summarize_submissions(match) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for sub in getattr(match, "persisted_submissions", []) or []:
        out.append({
            "attacker_id": sub.get("attacker_id"),
            "victim_id": sub.get("victim_id"),
            "flag_slot": sub.get("flag_slot"),
            "flag_index": sub.get("flag_index"),
            "success": bool(sub.get("success")),
            "reason": sub.get("reason"),
            "timestamp": sub.get("timestamp"),
            "points": sub.get("points"),
        })
    return out


def _per_player_metrics(match) -> Dict[int, Dict[str, Any]]:
    metrics: Dict[int, Dict[str, Any]] = {}
    for pid, player in (match.players or {}).items():
        metrics[pid] = {
            "score": getattr(player, "score", 0),
            "attack_score": getattr(player, "attack_score", 0),
            "defense_score": getattr(player, "defense_score", 0),
            "sla_score": getattr(player, "sla_score", 0),
            "sla_up": bool(getattr(player, "sla_up", True)),
            "sla_down_minutes": getattr(player, "sla_down_minutes", 0),
            "flags_captured": getattr(player, "flags_captured", 0),
            "flags_lost": getattr(player, "flags_lost", 0),
        }
    return metrics


def _time_to_first_flag(match) -> Optional[float]:
    """Seconds from attack_started_at to the first successful FLAG_SUBMISSION event."""
    attack_started = getattr(match, "attack_started_at", None)
    if attack_started is None:
        return None
    for sub in match.persisted_submissions or []:
        if sub.get("success"):
            ts = sub.get("timestamp")
            if not ts:
                continue
            try:
                t = datetime.fromisoformat(ts)
            except Exception:
                continue
            return max(0.0, (t - attack_started).total_seconds())
    return None


def _token_usage(match) -> Dict[str, int]:
    usage = getattr(match, "token_usage", None) or {}
    return {
        "input_tokens": int(usage.get("input_tokens", 0)),
        "output_tokens": int(usage.get("output_tokens", 0)),
        "messages": int(usage.get("messages", 0)),
        "budget_exceeded": bool(usage.get("budget_exceeded", False)),
    }


def build_match_record(match) -> Dict[str, Any]:
    """Build the dict that gets written as one JSON line per match."""
    config = match.config
    record = {
        "schema_version": "1",
        "match_id": match.match_id,
        "bench_run_id": getattr(config, "bench_run_id", None),
        "scenario_id": getattr(config, "scenario_id", "S1"),
        "mode": getattr(config, "mode", "hvh"),
        "target_image": getattr(config, "target_image", None),
        "agent_image": getattr(config, "agent_image", None),
        "oracle_image": getattr(config, "oracle_image", None),
        "decoding_temp": getattr(config, "decoding_temp", None),
        "phases": {
            "defense_seconds": config.match.phases.defense,
            "attack_seconds": config.match.phases.attack,
        },
        "token_budget": {
            "input": getattr(config, "token_budget_input", None),
            "output": getattr(config, "token_budget_output", None),
        },
        "token_usage": _token_usage(match),
        "dnf": bool(getattr(match, "dnf", False)),
        "dnf_reason": getattr(match, "dnf_reason", None),
        "timestamps": {
            "created_at": _safe_isoformat(match.created_at),
            "started_at": _safe_isoformat(match.started_at),
            "defense_started_at": _safe_isoformat(match.defense_started_at),
            "attack_started_at": _safe_isoformat(match.attack_started_at),
            "finished_at": _safe_isoformat(match.finished_at),
        },
        "duration_seconds": (
            (match.finished_at - match.started_at).total_seconds()
            if match.started_at and match.finished_at else None
        ),
        "time_to_first_flag_seconds": _time_to_first_flag(match),
        "players": [
            {
                "player_id": p.id,
                "name": p.name,
                "model": p.model,
                "is_agent": getattr(p, "is_agent", True),
                "openrouter_slug": getattr(p, "openrouter_slug", None),
            }
            for p in config.players
        ],
        "player_metrics": _per_player_metrics(match),
        "flag_slot_inventory": _flag_slot_inventory(match),
        "submissions": _summarize_submissions(match),
        "oracle_summary": getattr(match, "oracle_summary", None),
        "status_at_finish": match.status,
    }
    return record


def write_match_jsonl(match, runs_dir: Optional[str] = None) -> Optional[str]:
    """Write the match summary as a one-line JSONL file. Returns the path on success."""
    runs_dir = runs_dir or getattr(match.config, "runs_dir", None) or DEFAULT_RUNS_DIR
    matches_dir = os.path.join(runs_dir, "matches")
    try:
        os.makedirs(matches_dir, exist_ok=True)
    except OSError as e:
        logger.error(f"[{match.match_id}] could not create runs dir {matches_dir}: {e}")
        return None

    path = os.path.join(matches_dir, f"{match.match_id}.jsonl")
    try:
        record = build_match_record(match)
    except Exception as e:
        logger.exception(f"[{match.match_id}] failed to build match record: {e}")
        return None

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        logger.info(f"[{match.match_id}] wrote run record to {path}")
        return path
    except OSError as e:
        logger.error(f"[{match.match_id}] could not write {path}: {e}")
        return None
