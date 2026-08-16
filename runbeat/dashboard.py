from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from .run_parser import format_pace


def prepare_history(history: pd.DataFrame) -> pd.DataFrame:
    """Clean saved run history for summaries and charts."""
    if history.empty:
        return history.copy()

    prepared = history.copy()

    prepared["run_date"] = pd.to_datetime(
        prepared["run_date"],
        errors="coerce",
    )

    numeric_columns = [
        "distance_miles",
        "duration_seconds",
        "avg_pace_seconds",
        "avg_cadence",
        "avg_heart_rate",
        "temperature_f",
        "elevation_gain_ft",
    ]

    for column in numeric_columns:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(
                prepared[column],
                errors="coerce",
            )

    prepared = prepared.dropna(subset=["run_date"])
    prepared = prepared.sort_values("run_date")

    return prepared


def summarize_history(history: pd.DataFrame) -> dict[str, Any]:
    """Calculate headline training metrics."""
    prepared = prepare_history(history)

    if prepared.empty:
        return {
            "total_runs": 0,
            "total_miles": 0.0,
            "avg_pace_seconds": None,
            "avg_cadence": None,
            "latest_run": None,
        }

    total_miles = prepared["distance_miles"].fillna(0).sum()
    total_seconds = prepared["duration_seconds"].fillna(0).sum()

    if total_miles > 0 and total_seconds > 0:
        avg_pace_seconds = int(round(total_seconds / total_miles))
    else:
        valid_paces = prepared["avg_pace_seconds"].dropna()
        avg_pace_seconds = (
            int(round(valid_paces.mean()))
            if not valid_paces.empty
            else None
        )

    valid_cadence = prepared["avg_cadence"].dropna()
    avg_cadence = (
        int(round(valid_cadence.mean()))
        if not valid_cadence.empty
        else None
    )

    latest_run = prepared.iloc[-1].to_dict()

    return {
        "total_runs": len(prepared),
        "total_miles": float(total_miles),
        "avg_pace_seconds": avg_pace_seconds,
        "avg_cadence": avg_cadence,
        "latest_run": latest_run,
    }


def weekly_mileage(history: pd.DataFrame) -> pd.DataFrame:
    """Return mileage grouped by week."""
    prepared = prepare_history(history)

    if prepared.empty:
        return pd.DataFrame(columns=["week", "miles"])

    weekly = (
        prepared.assign(
            week=prepared["run_date"]
            .dt.to_period("W-SUN")
            .dt.start_time
        )
        .groupby("week", as_index=False)["distance_miles"]
        .sum()
        .rename(columns={"distance_miles": "miles"})
    )

    return weekly


def render_training_dashboard(history: pd.DataFrame) -> None:
    """Render the training dashboard in Streamlit."""
    st.subheader("Training dashboard")

    summary = summarize_history(history)

    if summary["total_runs"] == 0:
        st.info(
            "Your dashboard will appear after you save your first run."
        )
        return

    metric_columns = st.columns(4)

    metric_columns[0].metric(
        "Saved runs",
        summary["total_runs"],
    )

    metric_columns[1].metric(
        "Total mileage",
        f"{summary['total_miles']:.1f} mi",
    )

    metric_columns[2].metric(
        "Average pace",
        format_pace(summary["avg_pace_seconds"]),
    )

    metric_columns[3].metric(
        "Average cadence",
        (
            f"{summary['avg_cadence']} SPM"
            if summary["avg_cadence"]
            else "—"
        ),
    )

    latest = summary["latest_run"]

    if latest:
        latest_date = pd.Timestamp(
            latest["run_date"]
        ).strftime("%B %-d, %Y")

        latest_distance = latest.get("distance_miles")
        latest_pace = format_pace(
            latest.get("avg_pace_seconds")
        )
        latest_cadence = latest.get("avg_cadence")

        st.markdown(
            f"""
            **Latest run — {latest_date}**

            {latest_distance:.2f} miles ·
            {latest_pace} pace ·
            {int(latest_cadence)} SPM
            """
        )

    prepared = prepare_history(history)
    chart_left, chart_right = st.columns(2)

    with chart_left:
        st.markdown("#### Weekly mileage")

        weekly = weekly_mileage(prepared)

        if not weekly.empty:
            weekly_chart = weekly.set_index("week")
            st.bar_chart(
                weekly_chart,
                y="miles",
                use_container_width=True,
            )

    with chart_right:
        st.markdown("#### Cadence trend")

        cadence_data = (
            prepared[
                ["run_date", "avg_cadence"]
            ]
            .dropna()
            .set_index("run_date")
        )

        if cadence_data.empty:
            st.caption(
                "Cadence data will appear when it is available."
            )
        else:
            st.line_chart(
                cadence_data,
                y="avg_cadence",
                use_container_width=True,
            )

    st.markdown("#### Pace trend")

    pace_data = prepared[
        ["run_date", "avg_pace_seconds"]
    ].dropna()

    if pace_data.empty:
        st.caption(
            "Pace data will appear when it is available."
        )
    else:
        pace_data["pace_minutes_per_mile"] = (
            pace_data["avg_pace_seconds"] / 60
        )

        st.line_chart(
            pace_data.set_index("run_date"),
            y="pace_minutes_per_mile",
            use_container_width=True,
        )

        st.caption(
            "Lower values indicate a faster pace."
        )
