"""Qaydalar qatı: baza xətti, kənar dəyərlər, diqqət skoru, risk xülasəsi.

Burada ekran, şəbəkə və ya baza kodu yoxdur. Funksiyalar DataFrame alır və
DataFrame və ya dəyər qaytarır. Həm Streamlit (app.py), həm də veb server
(serve.py) eyni qaydaları build_dashboard() vasitəsilə işlədir.
"""

import math
import re
from dataclasses import dataclass, field

import pandas as pd

LUNAR_DISTANCE_KM = 384_400
IQR_FACTOR = 1.5
DEFAULT_ALBEDO = 0.14  # typical NEO albedo, used only when JPL gives no diameter
METRICS = ("diameter_m", "velocity_km_s", "miss_distance_km")
SENTRY_TOP = 12

# Attention score weights. Sum is 100.
WEIGHT_SIZE = 35
WEIGHT_CLOSENESS = 35
WEIGHT_HAZARDOUS = 15
WEIGHT_SENTRY = 15


# ---------- Units and formulas ----------


def to_lunar_distance(km):
    """Kilometri "Ay məsafəsi"nə (LD) çevirir. 1 LD = 384 400 km."""
    return km / LUNAR_DISTANCE_KM


def diameter_from_h(h, albedo=DEFAULT_ALBEDO):
    """Mütləq ulduz ölçüsündən (H) təxmini diametr, metrlə.

    Standart düstur: D(km) = 1329 / sqrt(albedo) * 10^(-H/5). Ədəd və ya Series qəbul edir.
    """
    return 1329 / math.sqrt(albedo) * 10 ** (-h / 5) * 1000


# ---------- Preparing stored data ----------


def prepare_asteroids(df):
    """Bazadan gələn asteroidlərə tip və köməkçi sütun (distance_ld) əlavə edir."""
    df = df.copy()
    for column in ("is_hazardous", "is_sentry_object", "is_sample"):
        df[column] = df[column].fillna(False).astype(bool) if column in df else False
    df["date"] = df["date"].astype(str)
    df["distance_ld"] = to_lunar_distance(df["miss_distance_km"])
    return df


def prepare_close_approach(df):
    """Gələcək keçidlərə LD və (JPL verməyəndə) H-dan təxmini diametr əlavə edir."""
    df = df.copy()
    df["distance_ld"] = to_lunar_distance(df["distance_km"])
    df["diameter_estimated"] = df["diameter_m"].isna()
    can_estimate = df["diameter_m"].isna() & df["abs_magnitude_h"].notna()
    df.loc[can_estimate, "diameter_m"] = diameter_from_h(df.loc[can_estimate, "abs_magnitude_h"])
    df["diameter_m"] = df["diameter_m"].round(1)
    return df.sort_values("datetime_utc").reset_index(drop=True)


def filter_asteroids(df, start=None, end=None, only_hazardous=False):
    """Tarix aralığı (daxil olmaqla, "YYYY-MM-DD") və təhlükəlilik üzrə filtr."""
    mask = pd.Series(True, index=df.index)
    if start is not None:
        mask &= df["date"] >= str(start)
    if end is not None:
        mask &= df["date"] <= str(end)
    if only_hazardous:
        mask &= df["is_hazardous"]
    return df[mask]


def is_sample(df):
    """Datada nümunə (uydurma) sətir varmı."""
    if df.empty:
        return False
    if "is_sample" in df and df["is_sample"].any():
        return True
    return bool(df["name"].astype(str).str.contains("SAMPLE").any())


# ---------- Baseline and outliers ----------


def baseline(series):
    """Bir sütun üçün baza xətti: median, kvartillər, IQR sərhədləri və s."""
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {}
    q1, median, q3 = values.quantile([0.25, 0.5, 0.75])
    iqr = q3 - q1
    return {
        "count": int(values.size),
        "median": median,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower_fence": q1 - IQR_FACTOR * iqr,
        "upper_fence": q3 + IQR_FACTOR * iqr,
        "min": values.min(),
        "max": values.max(),
        "mean": values.mean(),
    }


def baseline_table(df, columns=METRICS):
    """Bir neçə sütunun baza xətti cədvəl kimi (sətir = sütun adı)."""
    return pd.DataFrame({column: baseline(df[column]) for column in columns}).T


def flag_outliers(df, columns=METRICS, reference=None):
    """Hər sütun üçün `is_outlier_<sütun>`, ümumi `is_outlier` və `outlier_reasons` əlavə edir.

    Sərhədlər `reference` datasından hesablanır (məs. tarixçə). Verilməsə, `df`-in özündən.
    `outlier_reasons` hər sətir üçün normadan kənar olan sütunların siyahısıdır.
    """
    reference = df if reference is None else reference
    result = df.copy()
    flags = []
    for column in columns:
        stats = baseline(reference[column])
        flag = f"is_outlier_{column}"
        if stats:
            values = pd.to_numeric(result[column], errors="coerce")
            result[flag] = (values < stats["lower_fence"]) | (values > stats["upper_fence"])
        else:
            result[flag] = False
        flags.append(flag)
    result["is_outlier"] = result[flags].any(axis=1) if flags else False
    result["outlier_reasons"] = [
        [column for column in columns if result.at[index, f"is_outlier_{column}"]] for index in result.index
    ]
    return result


def choose_reference(recent, history):
    """Baza xətti üçün data: tarixçə son 7 gündən çoxdursa tarixçə, yoxsa son 7 gün."""
    if history is not None and len(history) > len(recent):
        return history, "history"
    return recent, "recent"


def attention_score(df):
    """Sıralama üçün 0-100 arası sadə skor. Bu toqquşma ehtimalı DEYİL.

    35 × diametr persentili + 35 × yaxınlıq persentili
    + 15 təhlükəlidirsə + 15 Sentry siyahısındadırsa.
    """
    if df.empty:
        return pd.Series(dtype=float, index=df.index)
    size = df["diameter_m"].rank(pct=True)
    closeness = (-df["miss_distance_km"]).rank(pct=True)
    hazardous = df["is_hazardous"].astype(bool).astype(int)
    sentry = df.get("is_sentry_object", pd.Series(False, index=df.index)).astype(bool).astype(int)
    score = (
        WEIGHT_SIZE * size
        + WEIGHT_CLOSENESS * closeness
        + WEIGHT_HAZARDOUS * hazardous
        + WEIGHT_SENTRY * sentry
    )
    return score.round(1)


def compare_medians(recent, reference, columns=METRICS):
    """Son datanın medianını baza xəttinin medianı ilə müqayisə edir."""
    rows = []
    for column in columns:
        recent_median = pd.to_numeric(recent[column], errors="coerce").median()
        reference_median = pd.to_numeric(reference[column], errors="coerce").median()
        ratio = recent_median / reference_median if reference_median else float("nan")
        rows.append(
            {
                "metric": column,
                "recent_median": recent_median,
                "baseline_median": reference_median,
                "ratio": ratio,
            }
        )
    return pd.DataFrame(rows)


def weekly_trend(history):
    """Tarixçəni həftələrə bölür: asteroid sayı, təhlükəli faizi, median diametr."""
    data = history.assign(week=pd.to_datetime(history["date"]).dt.to_period("W").dt.start_time)
    return (
        data.groupby("week")
        .agg(
            count=("name", "size"),
            hazardous_pct=("is_hazardous", lambda s: 100 * s.astype(bool).mean()),
            median_diameter_m=("diameter_m", "median"),
        )
        .reset_index()
    )


# ---------- Sentry ----------


def torino_positive(sentry):
    """Torino şkalasında 0-dan yuxarı olan obyektlərin adları."""
    return sentry.loc[sentry["torino_max"] > 0, "name"].astype(str).tolist()


def designation_keys(name):
    """Asteroid adından müqayisə açarlarını çıxarır.

    "307493 (2002 XP90)" -> {"307493", "2002 XP90"}
    "(2011 TO)"          -> {"2011 TO"}
    """
    text = str(name).strip()
    keys = set(re.findall(r"\(([^)]+)\)", text))
    number = re.match(r"^(\d+)\b", text)
    if number:
        keys.add(number.group(1))
    if not keys:
        keys.add(text)
    return keys


def match_sentry(asteroids, sentry):
    """NeoWs asteroidlərini Sentry siyahısı ilə uyğunlaşdırır (ad/nömrə üzrə)."""
    lookup = {}
    for index, row in sentry.iterrows():
        for key in designation_keys(row["name"]) | {str(row["designation"])}:
            lookup.setdefault(key, index)
    matches = []
    for _, row in asteroids.iterrows():
        index = next((lookup[key] for key in designation_keys(row["name"]) if key in lookup), None)
        if index is not None:
            matches.append({**row.to_dict(), **sentry.loc[index].add_prefix("sentry_").to_dict()})
    return pd.DataFrame(matches)


# ---------- Everything a screen needs ----------


@dataclass
class Dashboard:
    """Ekranların göstərdiyi hər şey, artıq hesablanmış halda."""

    asteroids: pd.DataFrame  # son 7 gün, kənar dəyər və diqqət skoru ilə, skora görə sıralı
    reference: pd.DataFrame  # baza xəttinin hesablandığı data
    reference_source: str  # "history" və ya "recent"
    baseline: dict  # sütun -> baseline() nəticəsi
    is_sample: bool
    comparison: pd.DataFrame | None = None  # yalnız tarixçə olanda
    weekly: pd.DataFrame | None = None  # yalnız tarixçə olanda
    sentry: pd.DataFrame | None = None
    sentry_top: pd.DataFrame | None = None
    torino_positive: list = field(default_factory=list)
    sentry_matches: pd.DataFrame = field(default_factory=pd.DataFrame)
    sentry_flagged: list = field(default_factory=list)
    close_approach: pd.DataFrame | None = None


def build_dashboard(recent, history=None, sentry=None, close_approach=None):
    """Bazadan gələn xam cədvəllərdən ekran üçün bütün nəticələri hesablayır.

    `recent` boş olmamalıdır; boş data halını ekran özü göstərir.
    """
    recent = prepare_asteroids(recent)
    history = prepare_asteroids(history) if history is not None and not history.empty else None
    reference, source = choose_reference(recent, history)

    asteroids = flag_outliers(recent, reference=reference)
    asteroids["attention_score"] = attention_score(asteroids)
    asteroids = asteroids.sort_values("attention_score", ascending=False).reset_index(drop=True)

    dashboard = Dashboard(
        asteroids=asteroids,
        reference=reference,
        reference_source=source,
        baseline={column: baseline(reference[column]) for column in METRICS},
        is_sample=is_sample(recent),
    )
    if source == "history":
        dashboard.comparison = compare_medians(recent, history)
        dashboard.weekly = weekly_trend(history)

    if sentry is not None and not sentry.empty:
        sentry = sentry.sort_values("palermo_cum", ascending=False).reset_index(drop=True)
        dashboard.sentry = sentry
        dashboard.sentry_top = sentry.head(SENTRY_TOP)
        dashboard.torino_positive = torino_positive(sentry)
        dashboard.sentry_matches = match_sentry(recent, sentry)
        dashboard.sentry_flagged = recent.loc[recent["is_sentry_object"], "name"].tolist()

    if close_approach is not None:
        dashboard.close_approach = prepare_close_approach(close_approach)

    return dashboard
