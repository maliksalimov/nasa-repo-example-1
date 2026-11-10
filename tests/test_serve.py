import json
import math

import numpy as np
import pandas as pd

import db
import serve
from conftest import asteroid


def test_clean_makes_values_json_safe():
    value = {"a": np.float64(1.5), "b": float("nan"), "c": [np.int64(2), math.inf], "d": pd.Timestamp("2026-11-02")}
    assert serve.clean(value) == {"a": 1.5, "b": None, "c": [2, None], "d": "2026-11-02T00:00:00"}


def test_payload_without_data():
    assert serve.build_payload() == {"recent": None}


def test_payload_has_every_field_the_frontend_reads():
    db.replace_recent(
        [asteroid("(A)", diameter_m=600.0), asteroid("(B)", "2026-11-03"), asteroid("(2011 TO)", "2026-11-04")],
        "2026-11-02",
        "2026-11-08",
    )
    db.save_asteroids([asteroid("(OLD)", "2026-10-20")])
    db.replace_sentry([{
        "designation": "2011 TO", "name": "(2011 TO)", "impact_probability": 2.9e-6, "palermo_cum": -6.15,
        "palermo_max": -6.15, "torino_max": 0, "diameter_m": 18.0, "years": "2064-2064", "n_impacts": 1,
    }])
    db.replace_close_approach([{
        "designation": "2026 VK2", "datetime_utc": "2026-11-08T01:57", "date": "2026-11-08",
        "distance_km": 871744.9, "velocity_km_s": 4.9, "abs_magnitude_h": 30.25, "diameter_m": None,
    }])

    payload = serve.build_payload()
    json.dumps(payload, allow_nan=False)  # fails on NaN/inf

    assert payload["is_sample"] is False
    assert (payload["recent"]["start"], payload["recent"]["end"]) == ("2026-11-02", "2026-11-08")
    assert set(payload["recent"]["asteroids"][0]) == set(serve.ASTEROID_FIELDS)
    baseline = payload["baseline"]
    assert baseline["source"] == "history" and baseline["count"] == 4
    assert {c["metric"] for c in baseline["comparison"]} == {"diameter_m", "velocity_km_s", "miss_distance_km"}
    assert baseline["weekly"][0]["week"].count("-") == 2
    assert payload["sentry"]["recent_matches"][0]["name"] == "(2011 TO)"
    [item] = payload["close_approach"]["items"]
    assert item["diameter_estimated"] is True and item["diameter_m"] > 0
