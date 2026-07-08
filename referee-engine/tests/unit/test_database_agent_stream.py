import importlib
from datetime import datetime


def test_delete_match_removes_match_events_and_submissions(tmp_path, monkeypatch):
    database = importlib.import_module("database")
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "openclaw.db"))

    database._init_db_sync()
    database._save_match_sync("match_delete_me", "finished", {"players": [{"id": 1}]}, datetime(2026, 1, 1))
    database._save_event_sync("match_delete_me", "STATUS", {"status": "finished"}, datetime(2026, 1, 1))
    database._save_submission_sync(
        "match_delete_me",
        {
            "attacker_id": 1,
            "victim_id": 2,
            "flag": "FLAG{redacted}",
            "success": True,
            "reason": "success",
            "points": 100,
            "timestamp": "2026-01-01T00:00:00",
        },
    )

    assert database._delete_match_sync("match_delete_me") is True
    assert database._list_matches_summary_sync() == []
    assert database._load_submissions_sync("match_delete_me") == []
    assert database._delete_match_sync("match_delete_me") is False


def test_s1_runtime_flag_mode_depends_on_target_image():
    main = importlib.import_module("main")

    nexus = main.MatchConfig(
        players=[{"id": 1, "name": "P1"}],
        scenario_id="S1",
        target_image="nexusbi-s1:latest",
    )
    legacy = main.MatchConfig(
        players=[{"id": 1, "name": "P1"}],
        scenario_id="S1",
        target_image="openclaw/ctf-target:v1",
    )

    assert main.RefereeEngine._uses_legacy_s1_runtime_flags(nexus) is False
    assert main.RefereeEngine._target_maintenance_username(nexus) == "root"
    assert main.RefereeEngine._uses_legacy_s1_runtime_flags(legacy) is True
    assert main.RefereeEngine._target_maintenance_username(legacy) == "defender"
