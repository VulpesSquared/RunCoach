from __future__ import annotations

import math

import pandas as pd

from .models import WorkoutPlan
from .planner import target_curve


REQUIRED_COLUMNS = {"track_name", "artist", "spotify_uri", "effective_bpm", "duration_ms"}


def validate_catalog(catalog: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(catalog.columns)
    if missing:
        raise ValueError(f"Song catalog is missing: {', '.join(sorted(missing))}")


def select_tracks(
    catalog: pd.DataFrame,
    plan: WorkoutPlan,
    *,
    tolerance: int = 5,
    avoid_recent: bool = True,
) -> pd.DataFrame:
    validate_catalog(catalog)
    work = catalog.copy()
    work["effective_bpm"] = pd.to_numeric(work["effective_bpm"], errors="coerce")
    work["duration_ms"] = pd.to_numeric(work["duration_ms"], errors="coerce")
    work = work.dropna(subset=["effective_bpm", "duration_ms", "spotify_uri"])
    work = work.drop_duplicates(subset=["spotify_uri"])
    if work.empty:
        return work

    average_duration = max(120_000, int(work["duration_ms"].median()))
    track_count = max(1, math.ceil(plan.duration_minutes * 60_000 / average_duration))
    targets = target_curve(plan, track_count)

    selected_rows = []
    remaining = work.copy()
    for position, target in enumerate(targets, start=1):
        candidates = remaining.assign(
            bpm_distance=(remaining["effective_bpm"] - target).abs(),
            recent_penalty=(remaining.get("recently_used", False).astype(int) * 3)
            if "recently_used" in remaining.columns and avoid_recent
            else 0,
            preference_bonus=pd.to_numeric(remaining.get("rating", 0), errors="coerce").fillna(0)
            if "rating" in remaining.columns
            else 0,
        )
        candidates["score"] = (
            candidates["bpm_distance"]
            + candidates["recent_penalty"]
            - candidates["preference_bonus"] * 0.5
        )
        candidates = candidates.sort_values(["score", "bpm_distance", "track_name"])
        within = candidates[candidates["bpm_distance"] <= tolerance]
        choice = within.iloc[0] if not within.empty else candidates.iloc[0]
        row = choice.to_dict()
        row["position"] = position
        row["target_bpm"] = target
        row["bpm_delta"] = int(round(row["effective_bpm"] - target))
        selected_rows.append(row)
        remaining = remaining[remaining["spotify_uri"] != row["spotify_uri"]]
        if remaining.empty:
            break

    return pd.DataFrame(selected_rows)
