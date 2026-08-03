from __future__ import annotations

import secrets
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from runbeat.planner import WORKOUTS, personalize_plan
from runbeat.run_parser import format_pace, parse_run_csv
from runbeat.selector import select_tracks
from runbeat.spotify import (
    authorization_url,
    create_pkce_pair,
    create_playlist,
    current_user,
    exchange_code,
    replace_playlist_items,
)
from runbeat.storage import initialize_database, latest_cadence, list_runs, save_run


st.set_page_config(
    page_title="RunBeat Coach",
    page_icon="🏃",
    layout="wide",
)

st.title("🏃 RunBeat Coach")
st.caption(
    "Turn your latest run into a BPM-shaped Spotify playlist "
    "for the next workout."
)

DATA_PATH = Path("data/song_catalog.csv")

initialize_database()


def load_catalog() -> pd.DataFrame:
    """Load the local song catalog."""
    return pd.read_csv(DATA_PATH)


def load_spotify_secret(name: str) -> Optional[str]:
    """
    Safely read a Streamlit secret.

    Returns None when secrets.toml does not exist or the requested
    value has not been configured.
    """
    try:
        value = st.secrets.get(name)
    except Exception:
        return None

    if value is None:
        return None

    value = str(value).strip()
    return value or None


SPOTIFY_CLIENT_ID = load_spotify_secret("SPOTIFY_CLIENT_ID")
SPOTIFY_REDIRECT_URI = load_spotify_secret("SPOTIFY_REDIRECT_URI")

spotify_configured = bool(
    SPOTIFY_CLIENT_ID
    and SPOTIFY_REDIRECT_URI
)


def handle_spotify_callback() -> None:
    """Handle Spotify's OAuth redirect after the user signs in."""
    if not spotify_configured:
        return

    code = st.query_params.get("code")
    state = st.query_params.get("state")

    if not code or "spotify_token" in st.session_state:
        return

    if state != st.session_state.get("oauth_state"):
        st.error("Spotify login state did not match. Please reconnect.")
        return

    verifier = st.session_state.get("pkce_verifier")

    if not verifier:
        st.error("Spotify login information expired. Please reconnect.")
        return

    try:
        token = exchange_code(
            SPOTIFY_CLIENT_ID,
            SPOTIFY_REDIRECT_URI,
            code,
            verifier,
        )

        access_token = token.get("access_token")

        if not access_token:
            raise ValueError("Spotify did not return an access token.")

        st.session_state["spotify_token"] = access_token
        st.query_params.clear()
        st.rerun()

    except Exception as exc:
        st.error(f"Spotify authorization failed: {exc}")


with st.sidebar:
    st.header("Spotify")

    if spotify_configured:
        handle_spotify_callback()

        if "spotify_token" not in st.session_state:
            if "pkce_verifier" not in st.session_state:
                verifier, challenge = create_pkce_pair()

                st.session_state["pkce_verifier"] = verifier
                st.session_state["pkce_challenge"] = challenge
                st.session_state["oauth_state"] = secrets.token_urlsafe(24)

            login_url = authorization_url(
                SPOTIFY_CLIENT_ID,
                SPOTIFY_REDIRECT_URI,
                st.session_state["pkce_challenge"],
                st.session_state["oauth_state"],
            )

            st.link_button(
                "Connect Spotify",
                login_url,
                use_container_width=True,
            )
        else:
            st.success("Spotify connected")

            if st.button(
                "Disconnect Spotify",
                use_container_width=True,
            ):
                st.session_state.pop("spotify_token", None)
                st.session_state.pop("pkce_verifier", None)
                st.session_state.pop("pkce_challenge", None)
                st.session_state.pop("oauth_state", None)
                st.rerun()
    else:
        st.info(
            "Spotify is optional. The app can still import runs and "
            "generate playlists without connecting to Spotify."
        )
        st.caption(
            "To enable Spotify, create `.streamlit/secrets.toml` "
            "and add your Spotify Client ID and redirect URI."
        )


st.subheader("1. Add your latest run")

run_file = st.file_uploader(
    "Run CSV",
    type=["csv"],
    help=(
        "Supports common Garmin/Strava-style names such as distance, "
        "time, cadence/SPM, average heart rate, elevation gain, "
        "and temperature."
    ),
)

parsed_run = None
run_df = pd.DataFrame()

if run_file:
    details_left, details_right = st.columns(2)

    with details_left:
        run_date = st.date_input("Run date")

    with details_right:
        source = st.selectbox(
            "Source",
            [
                "Garmin",
                "Strava",
                "Apple Health",
                "Manual CSV",
                "Other",
            ],
        )

    notes = st.text_area(
        "Run notes",
        placeholder=(
            "How did it feel? Any traffic stops, weather issues, "
            "fueling notes, or unusually good or bad songs?"
        ),
    )

    try:
        parsed_run, run_df = parse_run_csv(
            run_file,
            source=source,
            run_date=run_date,
            notes=notes,
        )

        metric_columns = st.columns(5)

        metric_columns[0].metric(
            "Distance",
            (
                f"{parsed_run.distance_miles:.2f} mi"
                if parsed_run.distance_miles
                else "—"
            ),
        )

        metric_columns[1].metric(
            "Duration",
            (
                f"{parsed_run.duration_seconds // 60}:"
                f"{parsed_run.duration_seconds % 60:02d}"
                if parsed_run.duration_seconds
                else "—"
            ),
        )

        metric_columns[2].metric(
            "Pace",
            format_pace(parsed_run.avg_pace_seconds),
        )

        metric_columns[3].metric(
            "Cadence",
            (
                f"{parsed_run.avg_cadence} SPM"
                if parsed_run.avg_cadence
                else "—"
            ),
        )

        metric_columns[4].metric(
            "Avg HR",
            str(parsed_run.avg_heart_rate or "—"),
        )

        with st.expander("Preview imported rows"):
            st.dataframe(
                run_df.head(50),
                use_container_width=True,
            )

        if st.button(
            "Save run to history",
            type="primary",
        ):
            save_run(parsed_run)
            st.success(
                "Run saved. It is now part of your training history."
            )
            st.rerun()

    except Exception as exc:
        st.error(f"Could not parse this run file: {exc}")


history = list_runs()

if not history.empty:
    with st.expander(
        f"Run history ({len(history)} saved)",
        expanded=False,
    ):
        history_display = history.copy()

        history_display["pace"] = history_display[
            "avg_pace_seconds"
        ].apply(format_pace)

        columns = [
            "run_date",
            "source",
            "distance_miles",
            "pace",
            "avg_cadence",
            "avg_heart_rate",
            "temperature_f",
            "notes",
        ]

        available_columns = [
            column
            for column in columns
            if column in history_display.columns
        ]

        st.dataframe(
            history_display[available_columns],
            hide_index=True,
            use_container_width=True,
        )
else:
    st.caption(
        "No runs saved yet. Upload your first CSV to begin "
        "building the model."
    )


observed_cadence = (
    parsed_run.avg_cadence
    if parsed_run and parsed_run.avg_cadence
    else latest_cadence()
)

if not observed_cadence:
    observed_cadence = 160


st.subheader("2. Choose the next workout")

left, middle, right = st.columns(3)

with left:
    workout_name = st.selectbox(
        "Workout",
        list(WORKOUTS),
    )

with middle:
    duration = st.slider(
        "Minutes",
        20,
        90,
        WORKOUTS[workout_name].duration_minutes,
        5,
    )

with right:
    tolerance = st.slider(
        "BPM tolerance",
        1,
        10,
        5,
    )


base_plan = WORKOUTS[workout_name]

base_plan = base_plan.__class__(
    base_plan.name,
    duration,
    base_plan.start_bpm,
    base_plan.middle_bpm,
    base_plan.finish_bpm,
    base_plan.description,
)

plan = personalize_plan(
    base_plan,
    observed_cadence,
)

st.info(
    f"Observed cadence: **{observed_cadence} SPM** · "
    f"Playlist arc: **{plan.start_bpm} → "
    f"{plan.middle_bpm} → {plan.finish_bpm} BPM**"
)


st.subheader("3. Review the generated playlist")

catalog = load_catalog()

playlist = select_tracks(
    catalog,
    plan,
    tolerance=tolerance,
)

if playlist.empty:
    st.warning(
        "Add songs to `data/song_catalog.csv` before "
        "generating a playlist."
    )
else:
    display_columns = [
        "position",
        "track_name",
        "artist",
        "effective_bpm",
        "target_bpm",
        "bpm_delta",
    ]

    st.dataframe(
        playlist[display_columns],
        hide_index=True,
        use_container_width=True,
    )

    total_minutes = playlist["duration_ms"].sum() / 60_000

    st.caption(
        f"{len(playlist)} tracks · "
        f"approximately {total_minutes:.1f} minutes"
    )

    playlist_name = st.text_input(
        "Spotify playlist name",
        (
            f"RunBeat · {plan.name} · "
            f"{plan.start_bpm}-{plan.finish_bpm} BPM"
        ),
    )

    create_disabled = (
        not spotify_configured
        or "spotify_token" not in st.session_state
    )

    if st.button(
        "Create Spotify playlist",
        type="primary",
        disabled=create_disabled,
    ):
        try:
            token = st.session_state["spotify_token"]

            current_user(token)

            created = create_playlist(
                token,
                playlist_name,
                (
                    "Generated by RunBeat Coach from an observed "
                    f"cadence of {observed_cadence} SPM."
                ),
            )

            replace_playlist_items(
                token,
                created["id"],
                playlist["spotify_uri"].dropna().tolist(),
            )

            st.success("Playlist created in Spotify.")

            spotify_url = (
                created.get("external_urls", {})
                .get("spotify")
            )

            if spotify_url:
                st.link_button(
                    "Open playlist",
                    spotify_url,
                )

        except Exception as exc:
            st.error(f"Could not create playlist: {exc}")


with st.expander("Song catalog format"):
    st.code(
        (
            "track_name,artist,spotify_uri,effective_bpm,"
            "duration_ms,rating,recently_used"
        ),
        language="text",
    )

    st.write(
        "`effective_bpm` may be the song's literal BPM "
        "or its useful double-time running BPM."
    )