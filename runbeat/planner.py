from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from .models import WorkoutPlan


WORKOUTS = {
    "Easy": WorkoutPlan("Easy", 35, 154, 158, 160, "Relaxed aerobic running with a gentle finish."),
    "Steady": WorkoutPlan("Steady", 35, 156, 160, 164, "Controlled running with a modest progression."),
    "Progression": WorkoutPlan("Progression", 35, 156, 162, 168, "Begin controlled and finish fast."),
    "5K Simulation": WorkoutPlan("5K Simulation", 30, 160, 164, 170, "Race-specific build with a hard final segment."),
}


def infer_cadence(run_df: pd.DataFrame, fallback: int = 160) -> int:
    for column in ("cadence", "avg_cadence", "spm"):
        if column in run_df.columns:
            values = pd.to_numeric(run_df[column], errors="coerce").dropna()
            if not values.empty:
                return int(round(values.mean()))
    return fallback


def personalize_plan(plan: WorkoutPlan, observed_cadence: int) -> WorkoutPlan:
    adjustment = max(-4, min(4, observed_cadence - 160))
    return WorkoutPlan(
        name=plan.name,
        duration_minutes=plan.duration_minutes,
        start_bpm=plan.start_bpm + adjustment,
        middle_bpm=plan.middle_bpm + adjustment,
        finish_bpm=plan.finish_bpm + adjustment,
        description=plan.description,
    )


def target_curve(plan: WorkoutPlan, track_count: int) -> list[int]:
    if track_count <= 0:
        return []
    if track_count == 1:
        return [plan.middle_bpm]

    targets: list[int] = []
    midpoint = max(1, track_count // 2)
    for index in range(track_count):
        if index < midpoint:
            fraction = index / midpoint
            bpm = plan.start_bpm + fraction * (plan.middle_bpm - plan.start_bpm)
        else:
            denominator = max(1, track_count - midpoint - 1)
            fraction = (index - midpoint) / denominator
            bpm = plan.middle_bpm + fraction * (plan.finish_bpm - plan.middle_bpm)
        targets.append(int(round(bpm)))
    return targets


def plan_summary(plan: WorkoutPlan) -> dict[str, object]:
    return asdict(plan)
