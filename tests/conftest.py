import pytest

import db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Every test gets its own empty database, so tests never touch data/space.db."""
    path = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


def asteroid(name="(2026 AB1)", date="2026-11-02", **overrides):
    row = {
        "id": name,
        "name": name,
        "date": date,
        "diameter_m": 150.0,
        "velocity_km_s": 12.3,
        "miss_distance_km": 5_000_000.0,
        "is_hazardous": False,
        "is_sentry_object": False,
        "abs_magnitude_h": 22.1,
    }
    row.update(overrides)
    return row
