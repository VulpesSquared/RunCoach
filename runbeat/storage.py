from __future__ import annotations

import sqlite3
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .run_parser import ParsedRun


DEFAULT_DB_PATH = Path("data/runbeat.db")


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                source TEXT NOT NULL,
                distance_miles REAL,
                duration_seconds INTEGER,
                avg_pace_seconds INTEGER,
                avg_cadence INTEGER NOT NULL,
                avg_heart_rate INTEGER,
                max_heart_rate INTEGER,
                elevation_gain_ft REAL,
                temperature_f REAL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_run(run: ParsedRun, db_path: str | Path = DEFAULT_DB_PATH) -> int:
    initialize_database(db_path)
    values = asdict(run)
    columns = list(values)
    placeholders = ", ".join("?" for _ in columns)
    with connect(db_path) as connection:
        cursor = connection.execute(
            f"INSERT INTO runs ({', '.join(columns)}) VALUES ({placeholders})",
            [values[column] for column in columns],
        )
        return int(cursor.lastrowid)


def list_runs(db_path: str | Path = DEFAULT_DB_PATH, limit: int = 100) -> pd.DataFrame:
    initialize_database(db_path)
    with connect(db_path) as connection:
        return pd.read_sql_query(
            "SELECT * FROM runs ORDER BY run_date DESC, id DESC LIMIT ?",
            connection,
            params=(limit,),
        )


def latest_cadence(db_path: str | Path = DEFAULT_DB_PATH, fallback: int = 160) -> int:
    initialize_database(db_path)
    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT avg_cadence FROM runs ORDER BY run_date DESC, id DESC LIMIT 1"
        ).fetchone()
    return fallback if row is None else int(row["avg_cadence"])
