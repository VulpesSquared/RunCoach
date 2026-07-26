from dataclasses import dataclass


@dataclass(frozen=True)
class WorkoutPlan:
    name: str
    duration_minutes: int
    start_bpm: int
    middle_bpm: int
    finish_bpm: int
    description: str
