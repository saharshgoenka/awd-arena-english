import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_campaign_module():
    path = ROOT / "predictive_campaign.py"
    spec = importlib.util.spec_from_file_location("test_predictive_campaign_module", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_fresh_predictive_campaign_is_two_new_repeats_per_selected_isolated_cell():
    campaign = _load_campaign_module()

    central, broader = campaign.build_campaign_jobs(seed=17)
    jobs = central + broader

    assert len(central) == 48
    assert len(broader) == 96
    assert len(jobs) == 144
    assert {job["stage"] for job in central} == {"central_isolated"}
    assert {job["stage"] for job in broader} == {"broader_isolated"}
    assert {job["scenario"] for job in central} == {"S1", "S5", "S7"}
    assert {job["scenario"] for job in broader} == {"S2", "S3", "S4", "S6", "S8", "S9"}
    assert {job["mode"] for job in jobs} == {"attack_only", "defense_only"}
    assert {job["fresh_repeat"] for job in jobs} == {1, 2}
    assert {job["confirmatory_k"] for job in jobs} == {2, 3}

    cells = {(job["model_id"], job["scenario"], job["mode"]) for job in jobs}
    assert len(cells) == 4 * 9 * 2
    assert all(sum(1 for job in jobs if (job["model_id"], job["scenario"], job["mode"]) == cell) == 2 for cell in cells)


def test_campaign_manifest_marks_only_the_central_stage_as_predictor_inputs(tmp_path):
    campaign = _load_campaign_module()

    manifest_path = campaign.write_campaign_manifest(tmp_path, seed=17)
    manifest = campaign.read_manifest(manifest_path)

    assert manifest["campaign"] == "aaai27-predictive-k3"
    assert manifest["status"] == "planned_not_started"
    assert manifest["launch_policy"]["broader_requires_predictor_freeze"] is True
    assert len(manifest["stages"]["central_isolated"]) == 48
    assert len(manifest["stages"]["broader_isolated"]) == 96
    assert all(job["predictor_input"] for job in manifest["stages"]["central_isolated"])
    assert not any(job["predictor_input"] for job in manifest["stages"]["broader_isolated"])


def test_central_job_builds_the_frozen_isolated_match_contract():
    campaign = _load_campaign_module()
    central, _ = campaign.build_campaign_jobs(seed=17)
    job = next(job for job in central if job["mode"] == "defense_only")

    body = campaign.build_job_body(job, api_key="test-key")

    assert body["mode"] == "defense_only"
    assert body["scenario_id"] in {"S1", "S5", "S7"}
    assert body["bench_run_id"] == "aaai27-predictive-k3-central-isolated"
    assert body["match"]["phases"] == {"defense": 900, "attack": 180}
    assert body["scoring"] == {
        "attackSuccess": 100,
        "defenseFailure": -50,
        "defensePollFailure": -10,
        "finalSlaFailure": -50,
    }
    assert body["llm"]["apiKey"] == "test-key"
