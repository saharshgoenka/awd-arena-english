import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_sample_runner():
    path = ROOT / "sample_runner.py"
    spec = importlib.util.spec_from_file_location("test_sample_runner_module", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sample_registry():
    return {
        "defaults": {
            "llm": {
                "provider": "openai-completions",
                "baseUrl": "https://openrouter.ai/api/v1",
                "proxy": "",
            },
            "match": {"duration": 600, "phases": {"defense": 300, "attack": 300}},
            "scoring": {"attackSuccess": 100, "defenseFailure": -50, "slaViolation": -10},
            "flags": {"refreshInterval": 60, "format": "FLAG{{{hash}}}"},
            "token_budget_input": 1000000,
            "token_budget_output": 100000,
        },
        "scenarios": {
            "S1": {
                "target_image": "openclaw/ctf-target:v1",
                "oracle_image": "openclaw/oracle-s1:v1",
            }
        },
        "models": [
            {"id": "deepseek_v4_flash", "openrouter_slug": "deepseek/deepseek-v4-flash", "label": "DeepSeek V4 Flash"},
            {"id": "llama_4_scout", "openrouter_slug": "meta-llama/llama-4-scout", "label": "Llama 4 Scout"},
        ],
    }


def test_build_head_to_head_sample_body_uses_duration_overrides():
    sample_runner = _load_sample_runner()

    args = sample_runner.SampleArgs(
        scenario="S1",
        mode="head_to_head",
        model_a="deepseek_v4_flash",
        model_b="llama_4_scout",
        defense_minutes=10,
        attack_minutes=10,
        bench_run_id="manual-sample",
    )

    body = sample_runner.build_sample_body(_sample_registry(), args, api_key="secret-key")

    assert body["mode"] == "head_to_head"
    assert body["scenario_id"] == "S1"
    assert body["match"] == {"duration": 1200, "phases": {"defense": 600, "attack": 600}}
    assert body["target_image"] == "openclaw/ctf-target:v1"
    assert body["oracle_image"] == "openclaw/oracle-s1:v1"
    assert body["llm"]["apiKey"] == "secret-key"
    assert body["players"] == [
        {"id": 1, "name": "DeepSeek V4 Flash", "model": "deepseek/deepseek-v4-flash", "is_agent": True},
        {"id": 2, "name": "Llama 4 Scout", "model": "meta-llama/llama-4-scout", "is_agent": True},
    ]


def test_build_attack_only_sample_body_adds_unpatched_victim():
    sample_runner = _load_sample_runner()

    args = sample_runner.SampleArgs(
        scenario="S1",
        mode="attack_only",
        model_a="llama_4_scout",
        model_b=None,
        defense_minutes=0,
        attack_minutes=3,
        bench_run_id="manual-sample",
    )

    body = sample_runner.build_sample_body(_sample_registry(), args, api_key="secret-key")

    assert body["mode"] == "attack_only"
    assert body["match"] == {"duration": 180, "phases": {"defense": 0, "attack": 180}}
    assert body["players"] == [
        {"id": 1, "name": "Llama 4 Scout", "model": "meta-llama/llama-4-scout", "is_agent": True},
        {"id": 2, "name": "unpatched-victim", "model": None, "is_agent": False},
    ]


def test_load_openrouter_key_prefers_environment_then_dotenv(tmp_path, monkeypatch):
    sample_runner = _load_sample_runner()
    dotenv = tmp_path / ".env"
    dotenv.write_text("openrouter=from-dotenv\n", encoding="utf-8")

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("openrouter", raising=False)
    assert sample_runner.load_openrouter_key(tmp_path) == "from-dotenv"

    monkeypatch.setenv("OPENROUTER_API_KEY", "from-env")
    assert sample_runner.load_openrouter_key(tmp_path) == "from-env"


def test_redact_api_key_hides_llm_secret():
    sample_runner = _load_sample_runner()
    body = {"llm": {"apiKey": "secret-key", "model": "x"}, "players": []}

    redacted = sample_runner.redact_api_key(body)

    assert redacted["llm"]["apiKey"] == "***"
    assert body["llm"]["apiKey"] == "secret-key"
