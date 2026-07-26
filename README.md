# RunBeat Coach

RunBeat Coach turns an uploaded running CSV into a BPM-shaped Spotify playlist for the next workout.

## MVP features

- Upload run data as CSV
- Infer average cadence from `cadence`, `avg_cadence`, or `spm`
- Choose Easy, Steady, Progression, or 5K Simulation training
- Personalize a BPM arc from the observed cadence
- Rank songs from a personal catalog using effective running BPM
- Connect to Spotify with OAuth 2.0 Authorization Code + PKCE
- Create a private Spotify playlist and write tracks in workout order

## Why the app uses a local song catalog

New Spotify development applications do not have general access to Audio Features, Audio Analysis, or Recommendations. The catalog therefore stores `effective_bpm` explicitly. This can be literal tempo or a useful double-time cadence value.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```

Create a Spotify developer application and set its redirect URI to exactly the value in your Streamlit secrets. For local development, use:

```text
http://localhost:8501
```

Then replace the placeholder rows in `data/song_catalog.csv` with real Spotify track URIs and effective BPM values.

## Run CSV example

```csv
distance_miles,pace,cadence,heart_rate
1,9:12,158,154
2,9:06,160,160
3,9:01,162,166
```

Only cadence is required for personalization. Missing cadence falls back to 160 SPM.

## Test

```bash
pytest -q
```

## Deployment

The app can be deployed from GitHub to Streamlit Community Cloud. Add these secrets in the deployment settings rather than committing them:

```toml
SPOTIFY_CLIENT_ID = "..."
SPOTIFY_REDIRECT_URI = "https://your-app.streamlit.app"
```

Add that deployed URL to the Spotify app's allowed redirect URIs as well.
