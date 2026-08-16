import pandas as pd

from runbeat.dashboard import (
    prepare_history,
    summarize_history,
    weekly_mileage,
)


def sample_history() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "run_date": "2026-07-20",
                "distance_miles": 3.0,
                "duration_seconds": 1800,
                "avg_pace_seconds": 600,
                "avg_cadence": 158,
            },
            {
                "run_date": "2026-07-22",
                "distance_miles": 2.0,
                "duration_seconds": 1140,
                "avg_pace_seconds": 570,
                "avg_cadence": 162,
            },
        ]
    )


def test_prepare_history_sorts_by_date():
    history = sample_history().iloc[::-1]

    prepared = prepare_history(history)

    assert prepared.iloc[0]["run_date"] == pd.Timestamp(
        "2026-07-20"
    )


def test_summarize_history():
    summary = summarize_history(sample_history())

    assert summary["total_runs"] == 2
    assert summary["total_miles"] == 5.0
    assert summary["avg_pace_seconds"] == 588
    assert summary["avg_cadence"] == 160


def test_weekly_mileage():
    weekly = weekly_mileage(sample_history())

    assert len(weekly) == 1
    assert weekly.iloc[0]["miles"] == 5.0
