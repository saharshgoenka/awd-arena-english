import importlib.util
import sys
from pathlib import Path

import httpx
import pytest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_main_module(module_name: str):
    main_path = ROOT / "main.py"
    spec = importlib.util.spec_from_file_location(module_name, main_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _match_payload(name: str, scenario_id: str = "S1", mode: str = "defense_only"):
    players = [
        {
            "id": 1,
            "name": "DeepSeek V4 Flash",
            "model": "deepseek/deepseek-v4-flash",
            "apiKey": None,
            "gatewayPort": 18789,
            "is_agent": True,
        }
    ]
    if mode == "attack_only":
        players.append(
            {
                "id": 2,
                "name": "Unpatched victim",
                "model": None,
                "apiKey": None,
                "gatewayPort": 18790,
                "is_agent": False,
            }
        )

    return {
        "match": {
            "name": name,
            "duration": 1200,
            "phases": {"defense": 600, "attack": 600},
        },
        "llm": {
            "provider": "openai-completions",
            "baseUrl": "https://example.test/v1",
            "apiKey": "test-key",
            "model": "deepseek/deepseek-v4-flash",
        },
        "players": players,
        "scoring": {"attackSuccess": 100, "defenseFailure": -50, "slaViolation": -10},
        "flags": {"refreshInterval": 60, "format": "FLAG{{{hash}}}"},
        "target_image": f"{scenario_id.lower()}-target:latest",
        "agent_image": "openclaw/awd-openclaw-agent:latest",
        "mode": mode,
        "scenario_id": scenario_id,
        "token_budget_input": 10_000_000,
        "token_budget_output": 250_000,
    }


@pytest.mark.asyncio
async def test_staggered_run_endpoint_starts_first_match_only(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENCLAW_DB_PATH", str(tmp_path / "staggered-start.db"))
    module = _load_main_module("test_main_staggered_endpoint")

    started_names = []

    async def fake_start_match(config):
        started_names.append(config.match.name)
        return {"match_id": f"match_{len(started_names)}", "status": "initializing"}

    async def fake_wait_for_match_to_clear(match_id):
        return None

    monkeypatch.setattr(module.referee, "start_match", fake_start_match)
    monkeypatch.setattr(module.referee, "_wait_for_staggered_match_to_clear", fake_wait_for_match_to_clear)

    transport = httpx.ASGITransport(app=module.app)
    async with module.app.router.lifespan_context(module.app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/staggered-runs/start",
                json={
                    "name": "DeepSeek all samples",
                    "matches": [
                        _match_payload("DeepSeek V4 Flash - S1 Defense", "S1", "defense_only"),
                        _match_payload("DeepSeek V4 Flash - S1 Attack", "S1", "attack_only"),
                    ],
                },
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["run_id"].startswith("staggered_")
            assert payload["status"] == "running"
            assert payload["total_matches"] == 2
            assert payload["current_index"] == 1
            assert payload["current_match_id"] == "match_1"
            assert payload["match_ids"] == ["match_1"]
            assert started_names == ["DeepSeek V4 Flash - S1 Defense"]


@pytest.mark.asyncio
async def test_staggered_worker_starts_next_match_after_previous_clears(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENCLAW_DB_PATH", str(tmp_path / "staggered-worker.db"))
    module = _load_main_module("test_main_staggered_worker")

    started_names = []
    clear_events = []

    async def fake_start_match(config):
        started_names.append(config.match.name)
        return {"match_id": f"match_{len(started_names)}", "status": "initializing"}

    async def fake_wait_for_match_to_clear(match_id):
        clear_events.append(match_id)

    monkeypatch.setattr(module.referee, "start_match", fake_start_match)
    monkeypatch.setattr(module.referee, "_wait_for_staggered_match_to_clear", fake_wait_for_match_to_clear)

    configs = [
        module.MatchConfig(**_match_payload("DeepSeek V4 Flash - S1 Defense", "S1", "defense_only")),
        module.MatchConfig(**_match_payload("DeepSeek V4 Flash - S1 Attack", "S1", "attack_only")),
        module.MatchConfig(**_match_payload("DeepSeek V4 Flash - S2 Defense", "S2", "defense_only")),
    ]

    run = await module.referee.start_staggered_run(module.StaggeredRunConfig(name="DeepSeek sweep", matches=configs))
    run_id = run["run_id"]
    await module.referee.staggered_runs[run_id]["task"]

    assert started_names == [
        "DeepSeek V4 Flash - S1 Defense",
        "DeepSeek V4 Flash - S1 Attack",
        "DeepSeek V4 Flash - S2 Defense",
    ]
    assert clear_events == ["match_1", "match_2", "match_3"]
    state = module.referee.staggered_runs[run_id]
    assert state["status"] == "completed"
    assert state["current_index"] == 3
    assert state["match_ids"] == ["match_1", "match_2", "match_3"]
