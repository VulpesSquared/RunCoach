from runbeat.run_parser import ParsedRun
from runbeat.storage import latest_cadence, list_runs, save_run


def test_save_and_list_run(tmp_path):
    db_path = tmp_path / "runs.db"
    run = ParsedRun(
        run_date="2026-07-26",
        source="test",
        distance_miles=3.1,
        duration_seconds=1800,
        avg_pace_seconds=581,
        avg_cadence=162,
        avg_heart_rate=155,
        max_heart_rate=174,
        elevation_gain_ft=70.0,
        temperature_f=80.0,
        notes="Good finish",
    )

    run_id = save_run(run, db_path)
    history = list_runs(db_path)

    assert run_id == 1
    assert len(history) == 1
    assert history.iloc[0]["notes"] == "Good finish"
    assert latest_cadence(db_path) == 162
