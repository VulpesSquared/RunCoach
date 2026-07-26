import pandas as pd

from runbeat.planner import WORKOUTS
from runbeat.selector import select_tracks


def test_selector_orders_playlist_and_avoids_duplicates():
    catalog = pd.DataFrame(
        {
            "track_name": ["a", "b", "c", "d"],
            "artist": ["x"] * 4,
            "spotify_uri": [f"spotify:track:{i}" for i in range(4)],
            "effective_bpm": [156, 160, 164, 168],
            "duration_ms": [300000] * 4,
        }
    )
    result = select_tracks(catalog, WORKOUTS["Progression"])
    assert result["spotify_uri"].is_unique
    assert result["position"].tolist() == list(range(1, len(result) + 1))
