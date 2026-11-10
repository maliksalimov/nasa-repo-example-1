import pandas as pd
import pytest

import logic
from conftest import asteroid


def frame(**columns):
    return pd.DataFrame(columns)


def test_baseline_uses_quartiles_and_iqr_fences():
    stats = logic.baseline(pd.Series([1, 2, 3, 4, 100]))
    assert stats["median"] == 3
    assert (stats["q1"], stats["q3"], stats["iqr"]) == (2, 4, 2)
    assert (stats["lower_fence"], stats["upper_fence"]) == (-1, 7)


def test_flag_outliers_marks_values_and_reasons():
    df = frame(diameter_m=[1, 2, 3, 4, 100], velocity_km_s=[5, 5, 5, 5, 5])
    result = logic.flag_outliers(df, columns=["diameter_m", "velocity_km_s"])
    assert result["is_outlier"].tolist() == [False, False, False, False, True]
    assert result["outlier_reasons"].tolist() == [[], [], [], [], ["diameter_m"]]


def test_flag_outliers_can_use_reference_data():
    reference = frame(diameter_m=[10, 11, 12, 13, 14])
    recent = frame(diameter_m=[12, 50])
    result = logic.flag_outliers(recent, columns=["diameter_m"], reference=reference)
    assert result["is_outlier"].tolist() == [False, True]


def test_attention_score_ranks_big_close_hazardous_first():
    df = frame(
        diameter_m=[500, 10],
        miss_distance_km=[1_000_000, 50_000_000],
        is_hazardous=[True, False],
        is_sentry_object=[True, False],
    )
    assert logic.attention_score(df).tolist() == [100.0, 35.0]


def test_diameter_from_h_matches_known_value():
    # H = 22 with albedo 0.14 is about 141 m.
    assert logic.diameter_from_h(22) == pytest.approx(141.0, rel=0.01)


def test_prepare_close_approach_estimates_only_missing_diameters():
    df = frame(
        designation=["A", "B", "C"],
        datetime_utc=["2026-11-09T00:00", "2026-11-08T00:00", "2026-11-10T00:00"],
        distance_km=[384_400.0, 768_800.0, 100_000.0],
        abs_magnitude_h=[22.0, 19.1, None],
        diameter_m=[None, 340.0, None],
    )
    result = logic.prepare_close_approach(df)
    assert result["designation"].tolist() == ["B", "A", "C"]  # sorted by time
    assert result["distance_ld"].tolist()[:2] == [2.0, 1.0]
    assert result["diameter_estimated"].tolist() == [False, True, True]
    assert result["diameter_m"].iloc[0] == 340.0
    assert result["diameter_m"].iloc[1] == pytest.approx(141.0, rel=0.01)
    assert pd.isna(result["diameter_m"].iloc[2])  # no H, no estimate


def test_filter_asteroids_by_dates_and_hazard():
    df = logic.prepare_asteroids(pd.DataFrame([
        asteroid("(A)", "2026-11-02", is_hazardous=True),
        asteroid("(B)", "2026-11-03"),
        asteroid("(C)", "2026-11-05", is_hazardous=True),
    ]))
    assert logic.filter_asteroids(df, "2026-11-03", "2026-11-05")["name"].tolist() == ["(B)", "(C)"]
    assert logic.filter_asteroids(df, only_hazardous=True)["name"].tolist() == ["(A)", "(C)"]


def test_choose_reference_prefers_longer_history():
    recent = pd.DataFrame([asteroid()])
    history = pd.DataFrame([asteroid(), asteroid("(B)")])
    assert logic.choose_reference(recent, history)[1] == "history"
    assert logic.choose_reference(recent, None)[1] == "recent"
    assert logic.choose_reference(recent, recent)[1] == "recent"


@pytest.mark.parametrize(
    "name, keys",
    [
        ("307493 (2002 XP90)", {"307493", "2002 XP90"}),
        ("(2011 TO)", {"2011 TO"}),
        ("101955 Bennu (1999 RQ36)", {"101955", "1999 RQ36"}),
    ],
)
def test_designation_keys(name, keys):
    assert logic.designation_keys(name) == keys


def test_match_sentry_by_number_or_provisional_name():
    asteroids = frame(name=["101955 Bennu (1999 RQ36)", "(2026 ZZ9)", "(2011 TO)"])
    sentry = frame(
        designation=["101955", "2011 TO"],
        name=["101955 Bennu (1999 RQ36)", "(2011 TO)"],
        palermo_cum=[-1.4, -6.15],
    )
    matched = logic.match_sentry(asteroids, sentry)
    assert matched["name"].tolist() == ["101955 Bennu (1999 RQ36)", "(2011 TO)"]
    assert matched["sentry_palermo_cum"].tolist() == [-1.4, -6.15]


def test_build_dashboard_combines_everything():
    recent = pd.DataFrame([
        asteroid("(A)", diameter_m=600.0, is_hazardous=True),
        asteroid("(B)", diameter_m=20.0),
        asteroid("(SAMPLE-01)", diameter_m=40.0),
    ])
    sentry = frame(designation=["X"], name=["(X)"], palermo_cum=[-2.0], torino_max=[1])
    dashboard = logic.build_dashboard(recent, None, sentry, None)

    assert dashboard.asteroids["name"].iloc[0] == "(A)"  # highest attention score first
    assert dashboard.reference_source == "recent"
    assert dashboard.comparison is None and dashboard.weekly is None
    assert dashboard.is_sample is True
    assert dashboard.torino_positive == ["(X)"]
    assert dashboard.close_approach is None
