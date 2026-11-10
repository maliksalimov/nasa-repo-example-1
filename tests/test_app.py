from streamlit.testing.v1 import AppTest

import db
from conftest import asteroid


def run_app():
    return AppTest.from_file("../app.py", default_timeout=60).run()


def html_text(at):
    return " ".join(element.proto.body for element in at.get("html"))


def test_app_shows_empty_state_when_database_is_empty():
    at = run_app()
    assert not at.exception, [e.value for e in at.exception]
    assert "Asteroid datası hələ yoxdur." in html_text(at)


def test_app_renders_every_section_and_filters():
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
    text = html_text(at)
    for heading in [
        "Bu həftə 2 asteroid Yerin yanından keçdi.",
        "Hansılarına diqqət etmək lazımdır?",
        "Bu həftə adi həftədirmi?",
        "Yerə dəyə biləcək obyektlər",
        "Növbəti 60 gündə kim yaxınlaşacaq?",
    ]:
        assert heading in text
    assert "Diqqət sırası, 2 asteroid" in text
    assert "2026 VK2" in text

    at.toggle[0].set_value(True).run()
    assert not at.exception
    assert "Diqqət sırası, 1 asteroid" in html_text(at)
