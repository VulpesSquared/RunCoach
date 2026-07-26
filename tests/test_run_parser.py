from io import BytesIO

from runbeat.run_parser import format_pace, parse_run_csv


def test_parse_summary_csv():
    csv = BytesIO(
        b"distance_miles,time,cadence,avg hr,max hr,elevation gain,temperature\n"
        b"3.1,28:59,161,154,173,82,78\n"
    )
    parsed, frame = parse_run_csv(csv)

    assert len(frame) == 1
    assert parsed.distance_miles == 3.1
    assert parsed.duration_seconds == 1739
    assert parsed.avg_cadence == 161
    assert parsed.avg_heart_rate == 154
    assert parsed.max_heart_rate == 173
    assert format_pace(parsed.avg_pace_seconds) == "9:21/mi"


def test_parse_split_rows_sums_duration_and_averages_cadence():
    csv = BytesIO(
        b"distance,time,spm\n"
        b"1,09:10,158\n"
        b"1,09:00,160\n"
        b"1,08:50,162\n"
    )
    parsed, _ = parse_run_csv(csv)

    assert parsed.distance_miles == 3.0
    assert parsed.duration_seconds == 1620
    assert parsed.avg_cadence == 160
