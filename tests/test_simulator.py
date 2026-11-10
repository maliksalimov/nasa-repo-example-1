from datetime import date

import simulator

COLUMNS = {
    "name", "date", "diameter_m", "velocity_km_s", "miss_distance_km",
    "is_hazardous", "id", "is_sentry_object", "abs_magnitude_h",
}


def test_sample_rows_have_asteroid_format():
    rows = simulator.make_sample_rows(date(2026, 11, 2))
    assert len(rows) == simulator.SAMPLE_ROWS == 30
    assert all(set(row) == COLUMNS for row in rows)
    assert all("SAMPLE" in row["name"] for row in rows)
    assert {row["date"] for row in rows} == {f"2026-11-0{day}" for day in range(2, 9)}


def test_sample_rows_are_repeatable():
    start = date(2026, 11, 2)
    assert simulator.make_sample_rows(start) == simulator.make_sample_rows(start)
