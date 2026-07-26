from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from io import BytesIO
from typing import BinaryIO

import pandas as pd


COLUMN_ALIASES = {
    "distance_miles": ("distance_miles", "distance", "distance mi", "miles"),
    "duration_seconds": ("duration_seconds", "elapsed_time", "moving_time", "time"),
    "avg_cadence": ("avg_cadence", "cadence", "spm", "average cadence"),
    "avg_heart_rate": ("avg_heart_rate", "average heart rate", "avg hr", "heart rate"),
    "max_heart_rate": ("max_heart_rate", "maximum heart rate", "max hr"),
    "elevation_gain_ft": ("elevation_gain_ft", "elevation gain", "total ascent"),
    "temperature_f": ("temperature_f", "temperature", "temp"),
}


@dataclass(frozen=True)
class ParsedRun:
    run_date: str
    source: str
    distance_miles: float | None
    duration_seconds: int | None
    avg_pace_seconds: int | None
    avg_cadence: int
    avg_heart_rate: int | None
    max_heart_rate: int | None
    elevation_gain_ft: float | None
    temperature_f: float | None
    notes: str = ""


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]
    rename_map: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized.columns:
                rename_map[alias] = canonical
                break
    return normalized.rename(columns=rename_map)


def _first_numeric(frame: pd.DataFrame, column: str) -> float | None:
    if column not in frame.columns:
        return None
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    return None if values.empty else float(values.mean())


def _parse_duration(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    parts = text.split(":")
    try:
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(float(hours) * 3600 + float(minutes) * 60 + float(seconds))
        if len(parts) == 2:
            minutes, seconds = parts
            return int(float(minutes) * 60 + float(seconds))
        return int(float(text))
    except ValueError:
        return None


def parse_run_csv(
    file: BinaryIO | BytesIO,
    *,
    source: str = "CSV upload",
    run_date: date | None = None,
    notes: str = "",
    fallback_cadence: int = 160,
) -> tuple[ParsedRun, pd.DataFrame]:
    frame = _normalize_columns(pd.read_csv(file))
    if frame.empty:
        raise ValueError("The uploaded CSV did not contain any run rows.")

    distance = _first_numeric(frame, "distance_miles")
    if "distance_miles" in frame.columns and len(frame) > 1:
        distance_values = pd.to_numeric(frame["distance_miles"], errors="coerce").dropna()
        if not distance_values.empty:
            distance = float(distance_values.sum())
    cadence = _first_numeric(frame, "avg_cadence")
    avg_hr = _first_numeric(frame, "avg_heart_rate")
    max_hr = _first_numeric(frame, "max_heart_rate")
    elevation = _first_numeric(frame, "elevation_gain_ft")
    temperature = _first_numeric(frame, "temperature_f")

    duration = None
    if "duration_seconds" in frame.columns:
        durations = [_parse_duration(value) for value in frame["duration_seconds"]]
        valid = [value for value in durations if value is not None]
        if valid:
            duration = int(sum(valid) if len(valid) > 1 else valid[0])

    pace = None
    if distance and duration and distance > 0:
        pace = int(round(duration / distance))

    parsed = ParsedRun(
        run_date=(run_date or date.today()).isoformat(),
        source=source,
        distance_miles=round(distance, 3) if distance is not None else None,
        duration_seconds=duration,
        avg_pace_seconds=pace,
        avg_cadence=int(round(cadence)) if cadence is not None else fallback_cadence,
        avg_heart_rate=int(round(avg_hr)) if avg_hr is not None else None,
        max_heart_rate=int(round(max_hr)) if max_hr is not None else None,
        elevation_gain_ft=round(elevation, 1) if elevation is not None else None,
        temperature_f=round(temperature, 1) if temperature is not None else None,
        notes=notes.strip(),
    )
    return parsed, frame


def format_pace(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    minutes, remainder = divmod(int(seconds), 60)
    return f"{minutes}:{remainder:02d}/mi"
