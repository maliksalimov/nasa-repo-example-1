import csv

import db
from conftest import asteroid


def test_empty_database_has_no_window_and_no_risk_data():
    assert db.recent_window() is None
    assert db.load_recent().empty
    assert db.load_sentry() is None
    assert db.load_close_approach() is None


def test_recent_round_trip_keeps_types():
    db.replace_recent([asteroid(is_hazardous=True), asteroid("(2026 CD2)", "2026-11-03")], "2026-11-02", "2026-11-08")
    recent = db.load_recent()
    assert recent["name"].tolist() == ["(2026 AB1)", "(2026 CD2)"]
    assert recent["is_hazardous"].tolist() == [True, False]
    assert recent["diameter_m"].dtype.kind == "f"
    start, end, updated = db.recent_window()
    assert (start, end) == ("2026-11-02", "2026-11-08") and updated


def test_recent_only_returns_rows_inside_window():
    db.save_asteroids([asteroid("(OLD)", "2026-10-01")])
    db.replace_recent([asteroid()], "2026-11-02", "2026-11-08")
    assert db.load_recent()["name"].tolist() == ["(2026 AB1)"]
    assert sorted(db.load_history()["name"]) == ["(2026 AB1)", "(OLD)"]


def test_real_data_replaces_sample_data():
    db.replace_recent([asteroid("(SAMPLE-01)")], "2026-11-02", "2026-11-08", sample=True)
    assert db.count_real_asteroids() == 0
    assert db.load_history().empty  # history never contains sample rows

    db.replace_recent([asteroid()], "2026-11-02", "2026-11-08")
    assert db.load_recent()["name"].tolist() == ["(2026 AB1)"]
    assert db.count_real_asteroids() == 1


def test_same_asteroid_and_date_is_stored_once():
    db.save_asteroids([asteroid(diameter_m=100.0)])
    db.save_asteroids([asteroid(diameter_m=120.0)])
    history = db.load_history()
    assert len(history) == 1 and history["diameter_m"].iloc[0] == 120.0


def test_sentry_and_close_approach_are_replaced_whole():
    db.replace_sentry([{"designation": "A", "name": "(A)", "palermo_cum": -3.0, "torino_max": 0}])
    db.replace_sentry([{"designation": "B", "name": "(B)", "palermo_cum": -1.0, "torino_max": 0}])
    assert db.load_sentry()["designation"].tolist() == ["B"]

    db.replace_close_approach([])
    cad = db.load_close_approach()
    assert cad is not None and cad.empty  # loaded, but no passes


def test_import_csv_moves_old_files(tmp_path):
    def write(name, rows):
        with (tmp_path / name).open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    write("asteroids.csv", [{k: str(v) for k, v in asteroid().items()}])
    write("history.csv", [{k: str(v) for k, v in asteroid("(OLD)", "2026-10-01").items()}])
    write("close_approach.csv", [{
        "designation": "2026 VK2", "datetime_utc": "2026-11-08T01:57", "date": "2026-11-08",
        "distance_km": "871744.9", "distance_ld": "2.268", "velocity_km_s": "4.912",
        "abs_magnitude_h": "30.254", "diameter_m": "3.2", "diameter_estimated": "True",
    }])

    imported = db.import_csv(tmp_path)

    assert imported == {"history.csv": 1, "asteroids.csv": 1, "close_approach.csv": 1}
    assert db.recent_window()[:2] == ("2026-11-02", "2026-11-02")
    assert db.load_recent()["is_hazardous"].tolist() == [False]
    assert len(db.load_history()) == 2
    # The old estimated diameter is dropped: estimating is logic.py's job.
    assert db.load_close_approach()["diameter_m"].isna().all()
