"""Data qatı: NASA və JPL API-lərindən datanı götürür və bazaya yazır.

Mənbələr:
- NASA NeoWs feed:      son 7 günün asteroidləri (açar .env-də NASA_API_KEY)
- JPL CNEOS Sentry:     Yerə dəymə ehtimalı olan obyektlər (açarsız)
- JPL Close Approach:   gələcək yaxın keçidlər (açarsız)

Bu fayl yalnız datanı alır, vahidləri çevirir (au -> km, km -> m) və saxlayır.
Qaydalar (baza xətti, kənar dəyər, diametr təxmini) logic.py-dədir.

API işləməyəndə:
- NeoWs: bazada real data varsa saxlanılır, yoxdursa simulator.py nümunə data verir.
- Sentry / Close Approach: köhnə data saxlanılır. Risk datası uydurulmur.

İşə salmaq:
    python3 data_loader.py              # bütün mənbələri yenilə
    python3 data_loader.py --history 4  # son 4 həftəlik NeoWs tarixçəsi
"""

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import db
import simulator

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

NEOWS_URL = "https://api.nasa.gov/neo/rest/v1/feed"
SENTRY_URL = "https://ssd-api.jpl.nasa.gov/sentry.api"
CAD_URL = "https://ssd-api.jpl.nasa.gov/cad.api"
DEMO_KEY = "DEMO_KEY"  # NASA-nın hamıya açıq, limitli açarı (saatda 30 sorğu)
TIMEOUT_SECONDS = 30
DAYS = 7
HISTORY_PAUSE_SECONDS = 1
AU_KM = 149_597_870.7
CAD_DAYS = 60
CAD_DIST_MAX_AU = 0.05

# Errors that mean "the API did not give us usable data".
# urllib errors are OSError subclasses; bad JSON raises ValueError.
API_ERRORS = (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError)

MONTHS = {
    name: number
    for number, name in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        start=1,
    )
}


# ---------- HTTP ----------


def load_api_key():
    """Açarı mühit dəyişənindən, yoxdursa .env faylından oxuyur."""
    key = os.environ.get("NASA_API_KEY", "").strip()
    if key:
        return key

    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip().removeprefix("export ").strip()
            name, separator, value = line.partition("=")
            if separator and name.strip() == "NASA_API_KEY":
                key = value.strip().strip("\"'")
                if key:
                    return key

    print("XƏBƏRDARLIQ: .env-də NASA_API_KEY yoxdur, DEMO_KEY işlədilir.")
    return DEMO_KEY


def make_ssl_context():
    """certifi varsa onun sertifikatlarını işlədir.

    python.org-un macOS Python-u sistem sertifikatlarını görmür və
    CERTIFICATE_VERIFY_FAILED verir; certifi bunu həll edir.
    """
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


SSL_CONTEXT = make_ssl_context()


def open_json(url, params=None):
    """URL-dən JSON oxuyur."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS, context=SSL_CONTEXT) as response:
        return json.load(response)


def today_utc():
    return datetime.now(timezone.utc).date()


def date_range(end=None):
    """`end` daxil olmaqla 7 günün başlanğıc və son tarixini qaytarır."""
    end = end or today_utc()
    return end - timedelta(days=DAYS - 1), end


def to_float(value):
    """Mətni ədədə çevirir. Boş və ya None olanda None qaytarır."""
    if value is None or value == "":
        return None
    return float(value)


# ---------- NASA NeoWs ----------


def fetch_feed(api_key, start, end):
    """NeoWs feed-in xam JSON cavabı."""
    return open_json(
        NEOWS_URL,
        {"start_date": start.isoformat(), "end_date": end.isoformat(), "api_key": api_key},
    )


def parse_feed(feed):
    """NeoWs cavabını sətirlərə çevirir. Diametr API-nin min və max-ının ortasıdır."""
    rows = []
    for asteroids in feed["near_earth_objects"].values():
        for asteroid in asteroids:
            approach = asteroid["close_approach_data"][0]
            diameter = asteroid["estimated_diameter"]["meters"]
            average_diameter = (
                diameter["estimated_diameter_min"] + diameter["estimated_diameter_max"]
            ) / 2
            rows.append(
                {
                    "name": asteroid["name"],
                    "date": approach["close_approach_date"],
                    "diameter_m": round(average_diameter, 2),
                    "velocity_km_s": round(
                        float(approach["relative_velocity"]["kilometers_per_second"]), 3
                    ),
                    "miss_distance_km": round(float(approach["miss_distance"]["kilometers"]), 1),
                    "is_hazardous": bool(asteroid["is_potentially_hazardous_asteroid"]),
                    "id": str(asteroid["neo_reference_id"]),
                    "is_sentry_object": bool(asteroid.get("is_sentry_object", False)),
                    "abs_magnitude_h": asteroid.get("absolute_magnitude_h"),
                }
            )
    if not rows:
        raise ValueError("API cavabında asteroid yoxdur")
    return sorted(rows, key=lambda row: (row["date"], row["name"]))


def update_recent():
    """Son 7 günü yeniləyir. Real data gəlibsə True qaytarır."""
    start, end = date_range()
    try:
        rows = parse_feed(fetch_feed(load_api_key(), start, end))
    except API_ERRORS as error:
        print(f"XƏBƏRDARLIQ: NeoWs API işləmədi ({error}).", file=sys.stderr)
        if db.count_real_asteroids() > 0:
            print("Bazadakı köhnə real data saxlanılır.", file=sys.stderr)
            return False
        print(f"Real data YOX, {simulator.SAMPLE_ROWS} sətirlik nümunə data yazılır.", file=sys.stderr)
        db.replace_recent(simulator.make_sample_rows(start), start.isoformat(), end.isoformat(), sample=True)
        return False

    db.replace_recent(rows, start.isoformat(), end.isoformat())
    print(f"NeoWs: {len(rows)} asteroid ({start} - {end}).")
    return True


def fetch_history(weeks=4, end=None):
    """Son `weeks` həftəni 7 günlük hissələrlə yığıb bazaya əlavə edir.

    Son 7 günün pəncərəsini dəyişmir. Bir hissə alınmasa, dayanır.
    Bazaya yeni əlavə olunan asteroid sayını qaytarır.
    """
    api_key = load_api_key()
    if api_key == DEMO_KEY and weeks > 20:
        print("XƏBƏRDARLIQ: DEMO_KEY saatda 30 sorğu verir, tarixçə yarımçıq qala bilər.")

    before = db.count_real_asteroids()
    window_end = end or today_utc()
    for week in range(weeks):
        start, finish = date_range(window_end)
        try:
            rows = parse_feed(fetch_feed(api_key, start, finish))
        except API_ERRORS as error:
            print(f"XƏBƏRDARLIQ: {start} - {finish} alınmadı ({error}). Dayanıram.", file=sys.stderr)
            break
        db.save_asteroids(rows)
        print(f"Həftə {week + 1}/{weeks}: {start} - {finish}, {len(rows)} asteroid.")
        window_end = start - timedelta(days=1)
        if week < weeks - 1:
            time.sleep(HISTORY_PAUSE_SECONDS)

    added = db.count_real_asteroids() - before
    print(f"Tarixçə: {added} yeni asteroid.")
    return added


# ---------- JPL Sentry ----------


def parse_sentry(payload):
    rows = []
    for item in payload["data"]:
        diameter_km = to_float(item.get("diameter"))
        rows.append(
            {
                "designation": item["des"],
                "name": item.get("fullname", item["des"]).strip(),
                "impact_probability": float(item["ip"]),
                "palermo_cum": float(item["ps_cum"]),
                "palermo_max": float(item["ps_max"]),
                "torino_max": int(item["ts_max"] or 0),
                "diameter_m": round(diameter_km * 1000, 1) if diameter_km is not None else None,
                "v_inf_km_s": to_float(item.get("v_inf")),
                "years": item.get("range", ""),
                "n_impacts": int(item.get("n_imp") or 0),
                "last_obs": item.get("last_obs", ""),
            }
        )
    return sorted(rows, key=lambda row: row["palermo_cum"], reverse=True)


def update_sentry():
    """Sentry siyahısını yeniləyir. Uğurlu olanda True qaytarır."""
    try:
        rows = parse_sentry(open_json(SENTRY_URL))
    except API_ERRORS as error:
        print(f"XƏBƏRDARLIQ: Sentry API işləmədi ({error}). Köhnə data saxlanılır.", file=sys.stderr)
        return False
    db.replace_sentry(rows)
    print(f"Sentry: {len(rows)} obyekt.")
    return True


# ---------- JPL Close Approach ----------


def parse_cad_datetime(text):
    """JPL formatı "2026-Nov-08 01:57" -> datetime. Locale-dən asılı deyil."""
    day_part, time_part = text.split(" ")
    year, month, day = day_part.split("-")
    hour, minute = time_part.split(":")
    return datetime(int(year), MONTHS[month], int(day), int(hour), int(minute))


def parse_close_approach(payload):
    """CAD cavabı `fields` + `data` massivləridir. Keçid olmayanda `data` yoxdur.

    Diametr yalnız JPL verəndə yazılır. Təxmini diametr logic.py-də hesablanır.
    """
    fields = payload["fields"]
    rows = []
    for values in payload.get("data", []):
        item = dict(zip(fields, values))
        moment = parse_cad_datetime(item["cd"])
        diameter_km = to_float(item.get("diameter"))
        rows.append(
            {
                "designation": item["des"],
                "datetime_utc": moment.isoformat(timespec="minutes"),
                "date": moment.date().isoformat(),
                "distance_km": round(float(item["dist"]) * AU_KM, 1),
                "velocity_km_s": round(float(item["v_rel"]), 3),
                "abs_magnitude_h": to_float(item.get("h")),
                "diameter_m": round(diameter_km * 1000, 1) if diameter_km is not None else None,
            }
        )
    return rows


def update_close_approach(days=CAD_DAYS, dist_max_au=CAD_DIST_MAX_AU):
    """Bu gündən `days` gün irəli, `dist_max_au` daxilindəki keçidləri yeniləyir."""
    start = today_utc()
    params = {
        "date-min": start.isoformat(),
        "date-max": (start + timedelta(days=days)).isoformat(),
        "dist-max": str(dist_max_au),
        "diameter": "true",
    }
    try:
        rows = parse_close_approach(open_json(CAD_URL, params))
    except API_ERRORS as error:
        print(f"XƏBƏRDARLIQ: Close Approach API işləmədi ({error}). Köhnə data saxlanılır.", file=sys.stderr)
        return False
    db.replace_close_approach(rows)
    print(f"Close Approach: {len(rows)} keçid ({days} gün, {dist_max_au} au).")
    return True


# ---------- All sources ----------


def update_all():
    """Bütün mənbələri yeniləyir. Hər mənbə üçün uğurlu olub-olmadığını qaytarır."""
    return {
        "recent": update_recent(),
        "sentry": update_sentry(),
        "close_approach": update_close_approach(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="NASA və JPL datasını bazaya yazır.")
    parser.add_argument(
        "--history",
        type=int,
        metavar="HƏFTƏ",
        help="yalnız NeoWs tarixçəsi yığ (bu qədər həftə)",
    )
    args = parser.parse_args(argv)
    if args.history is not None:
        if args.history < 1:
            parser.error("--history ən azı 1 olmalıdır")
        fetch_history(args.history)
        return 0
    results = update_all()
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
