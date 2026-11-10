from streamlit.testing.v1 import AppTest

import db
from conftest import asteroid


def run_app():
    return AppTest.from_file("../app.py", default_timeout=60).run()


def test_app_asks_for_data_when_database_is_empty():
    at = run_app()
    assert not at.exception
    assert "Datanı yenilə" in at.error[0].value


def test_app_renders_all_tabs_with_data():
    db.replace_recent(
        [asteroid("(A)", diameter_m=600.0, is_hazardous=True), asteroid("(B)", "2026-11-03")],
        "2026-11-02",
        "2026-11-08",
    )
    db.replace_sentry([{"designation": "X", "name": "(X)", "impact_probability": 1e-6, "palermo_cum": -5.0,
                        "palermo_max": -5.0, "torino_max": 0, "years": "2100-2100", "n_impacts": 1}])
    db.replace_close_approach([{"designation": "2026 VK2", "datetime_utc": "2026-11-08T01:57", "date": "2026-11-08",
                                "distance_km": 300000.0, "velocity_km_s": 4.9, "abs_magnitude_h": 30.0}])

    at = run_app()
    assert not at.exception, [e.value for e in at.exception]
    assert [tab.label for tab in at.tabs] == ["Son 7 gün", "Baza xətti", "Toqquşma riski (Sentry)", "Gələcək yaxınlaşmalar"]
    assert at.metric[0].value == "2"

    at.sidebar.checkbox[0].check().run()
    assert not at.exception
    assert at.metric[0].value == "1"
