from datetime import date, datetime

import pytest

import data_loader
import db
import simulator


def make_feed(**overrides):
    asteroid = {
        "name": "(2026 AB1)",
        "neo_reference_id": "123",
        "absolute_magnitude_h": 22.1,
        "is_potentially_hazardous_asteroid": True,
        "is_sentry_object": False,
        "estimated_diameter": {"meters": {"estimated_diameter_min": 100.0, "estimated_diameter_max": 200.0}},
        "close_approach_data": [
            {
                "close_approach_date": "2026-11-02",
                "relative_velocity": {"kilometers_per_second": "12.34567"},
                "miss_distance": {"kilometers": "1234567.89"},
            }
        ],
    }
    asteroid.update(overrides)
    return {"near_earth_objects": {"2026-11-02": [asteroid]}}


def offline(*args, **kwargs):
    raise OSError("offline")


# ---------- NeoWs ----------


def test_parse_feed_extracts_all_columns():
    [row] = data_loader.parse_feed(make_feed())
    assert row == {
        "name": "(2026 AB1)",
        "date": "2026-11-02",
        "diameter_m": 150.0,
        "velocity_km_s": 12.346,
        "miss_distance_km": 1234567.9,
        "is_hazardous": True,
        "id": "123",
        "is_sentry_object": False,
        "abs_magnitude_h": 22.1,
    }


def test_parse_feed_rejects_empty_response():
    with pytest.raises(ValueError):
        data_loader.parse_feed({"near_earth_objects": {}})


def test_date_range_is_seven_days_inclusive():
    assert data_loader.date_range(date(2026, 11, 8)) == (date(2026, 11, 2), date(2026, 11, 8))


def test_update_recent_saves_real_data(monkeypatch):
    monkeypatch.setattr(data_loader, "fetch_feed", lambda *args: make_feed())
    monkeypatch.setattr(data_loader, "load_api_key", lambda: "test")

    assert data_loader.update_recent() is True
    assert db.count_real_asteroids() == 1
    assert db.recent_window() is not None


def test_api_failure_keeps_existing_real_data(monkeypatch):
    db.replace_recent(data_loader.parse_feed(make_feed()), "2026-11-02", "2026-11-08")
    monkeypatch.setattr(data_loader, "fetch_feed", offline)

    assert data_loader.update_recent() is False
    assert db.load_recent()["name"].tolist() == ["(2026 AB1)"]
    assert db.recent_window()[:2] == ("2026-11-02", "2026-11-08")


def test_api_failure_without_data_uses_simulator(monkeypatch):
    monkeypatch.setattr(data_loader, "fetch_feed", offline)

    assert data_loader.update_recent() is False
    recent = db.load_recent()
    assert len(recent) == simulator.SAMPLE_ROWS
    assert recent["is_sample"].all()
    assert db.count_real_asteroids() == 0


def test_fetch_history_stops_on_failure_and_keeps_window(monkeypatch):
    db.replace_recent([], "2026-11-02", "2026-11-08")
    calls = iter([make_feed(), None])

    def feed(*args):
        result = next(calls)
        if result is None:
            raise OSError("rate limited")
        return result

    monkeypatch.setattr(data_loader, "fetch_feed", feed)
    monkeypatch.setattr(data_loader, "HISTORY_PAUSE_SECONDS", 0)

    assert data_loader.fetch_history(weeks=3, end=date(2026, 11, 8)) == 1
    assert db.recent_window()[:2] == ("2026-11-02", "2026-11-08")


# ---------- JPL ----------


def test_parse_cad_datetime_ignores_locale():
    assert data_loader.parse_cad_datetime("2026-Nov-08 01:57") == datetime(2026, 11, 8, 1, 57)


def test_parse_close_approach_keeps_only_jpl_diameter():
    payload = {
        "fields": ["des", "cd", "dist", "v_rel", "h", "diameter"],
        "data": [
            ["2026 VK2", "2026-Nov-08 01:57", "0.002", "4.9", "30.0", None],
            ["99942", "2029-Apr-13 21:46", "0.00025", "7.4", "19.1", "0.34"],
        ],
    }
    first, second = data_loader.parse_close_approach(payload)
    assert first["date"] == "2026-11-08"
    assert first["distance_km"] == pytest.approx(0.002 * data_loader.AU_KM, rel=1e-6)
    assert first["diameter_m"] is None  # estimating is logic.py's job
    assert second["diameter_m"] == 340.0


def test_parse_close_approach_handles_no_results():
    assert data_loader.parse_close_approach({"fields": ["des"], "count": "0"}) == []


def test_parse_sentry_sorts_by_palermo_and_converts_units():
    payload = {
        "data": [
            {"des": "2011 TO", "fullname": "(2011 TO)", "ip": "2.9e-06", "ps_cum": "-6.15",
             "ps_max": "-6.15", "ts_max": "0", "diameter": "0.018", "range": "2064-2064", "n_imp": 1},
            {"des": "29075", "fullname": "29075 (1950 DA)", "ip": "0.00034", "ps_cum": "-0.98",
             "ps_max": "-0.98", "ts_max": "0", "diameter": "1.3", "range": "2880-2880", "n_imp": 1},
        ]
    }
    rows = data_loader.parse_sentry(payload)
    assert [row["designation"] for row in rows] == ["29075", "2011 TO"]
    assert rows[0]["diameter_m"] == 1300.0


def test_risk_api_failure_keeps_old_data(monkeypatch):
    db.replace_sentry([{"designation": "A", "name": "(A)", "palermo_cum": -3.0, "torino_max": 0}])
    monkeypatch.setattr(data_loader, "open_json", offline)

    assert data_loader.update_sentry() is False
    assert data_loader.update_close_approach() is False
    assert db.load_sentry()["designation"].tolist() == ["A"]
    assert db.load_close_approach() is None
