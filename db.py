"""Baza qatı: SQLite (data/space.db).

Layihədə SQL yalnız bu faylda yazılır. Digər fayllar datanı bu funksiyalarla
saxlayır və oxuyur. Burada API, qayda və ya ekran kodu yoxdur.

Cədvəllər:
    asteroids       NeoWs keçidləri (real və nümunə), açar: id + date
    sentry          JPL Sentry siyahısı, hər yeniləmədə tam əvəz olunur
    close_approach  JPL gələcək keçidləri, hər yeniləmədə tam əvəz olunur
    meta            son 7 günün pəncərəsi və yenilənmə vaxtları

Köhnə CSV-ləri bazaya köçürmək: python3 db.py --import-csv
"""

import argparse
import csv
import math
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "space.db"

ASTEROID_COLUMNS = [
    "id",
    "date",
    "name",
    "diameter_m",
    "velocity_km_s",
    "miss_distance_km",
    "is_hazardous",
    "is_sentry_object",
    "abs_magnitude_h",
    "is_sample",
]
SENTRY_COLUMNS = [
    "designation",
    "name",
    "impact_probability",
    "palermo_cum",
    "palermo_max",
    "torino_max",
    "diameter_m",
    "v_inf_km_s",
    "years",
    "n_impacts",
    "last_obs",
]
CLOSE_APPROACH_COLUMNS = [
    "designation",
    "datetime_utc",
    "date",
    "distance_km",
    "velocity_km_s",
    "abs_magnitude_h",
    "diameter_m",
]
BOOLEAN_COLUMNS = ("is_hazardous", "is_sentry_object", "is_sample")

SCHEMA = """
CREATE TABLE IF NOT EXISTS asteroids (
    id               TEXT    NOT NULL,
    date             TEXT    NOT NULL,
    name             TEXT    NOT NULL,
    diameter_m       REAL,
    velocity_km_s    REAL,
    miss_distance_km REAL,
    is_hazardous     INTEGER NOT NULL,
    is_sentry_object INTEGER NOT NULL DEFAULT 0,
    abs_magnitude_h  REAL,
    is_sample        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (id, date)
);
CREATE TABLE IF NOT EXISTS sentry (
    designation        TEXT PRIMARY KEY,
    name               TEXT,
    impact_probability REAL,
    palermo_cum        REAL,
    palermo_max        REAL,
    torino_max         INTEGER,
    diameter_m         REAL,
    v_inf_km_s         REAL,
    years              TEXT,
    n_impacts          INTEGER,
    last_obs           TEXT
);
CREATE TABLE IF NOT EXISTS close_approach (
    designation     TEXT NOT NULL,
    datetime_utc    TEXT NOT NULL,
    date            TEXT,
    distance_km     REAL,
    velocity_km_s   REAL,
    abs_magnitude_h REAL,
    diameter_m      REAL,
    PRIMARY KEY (designation, datetime_utc)
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


# ---------- Connection ----------


def connect():
    """Bazaya qoşulur və cədvəlləri (yoxdursa) yaradır.

    DB_PATH hər çağırışda oxunur, ona görə testlər onu müvəqqəti fayla dəyişə bilər.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.execute("PRAGMA journal_mode=WAL")  # readers do not block the writer
    connection.executescript(SCHEMA)
    return connection


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def _value(value):
    """Python dəyərini SQLite-a uyğun edir: boş mətn və NaN -> NULL, bool -> 0/1."""
    if value is None or value == "":
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, bool):
        return int(value)
    if value in ("True", "true"):
        return 1
    if value in ("False", "false"):
        return 0
    return value


def _insert(connection, table, columns, rows):
    placeholders = ", ".join("?" for _ in columns)
    connection.executemany(
        f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        [[_value(row.get(column)) for column in columns] for row in rows],
    )


def _query(sql, params=()):
    with closing(connect()) as connection:
        df = pd.read_sql_query(sql, connection, params=params)
    for column in BOOLEAN_COLUMNS:
        if column in df:
            df[column] = df[column].fillna(0).astype(bool)
    return df


# ---------- Meta ----------


def set_meta(connection, key, value):
    connection.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, str(value)))


def get_meta(key):
    with closing(connect()) as connection:
        row = connection.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


# ---------- Asteroids ----------


def save_asteroids(rows, sample=False):
    """Asteroidləri yazır. Eyni id + date varsa, yenisi köhnəni əvəz edir."""
    rows = [{**row, "is_sample": sample} for row in rows]
    with closing(connect()) as connection, connection:
        _insert(connection, "asteroids", ASTEROID_COLUMNS, rows)


def replace_recent(rows, start, end, sample=False):
    """Son 7 günün datasını yazır və pəncərəni yeniləyir. Köhnə nümunə sətirlər silinir.

    Hamısı bir tranzaksiyadır: ekran heç vaxt yarımçıq vəziyyət görmür.
    """
    rows = [{**row, "is_sample": sample} for row in rows]
    with closing(connect()) as connection, connection:
        connection.execute("DELETE FROM asteroids WHERE is_sample = 1")
        _insert(connection, "asteroids", ASTEROID_COLUMNS, rows)
        set_meta(connection, "recent_start", start)
        set_meta(connection, "recent_end", end)
        set_meta(connection, "recent_updated_at", now_utc())


def count_real_asteroids():
    with closing(connect()) as connection:
        return connection.execute("SELECT COUNT(*) FROM asteroids WHERE is_sample = 0").fetchone()[0]


def recent_window():
    """Son 7 günün pəncərəsi: (start, end, updated_at) və ya None."""
    start, end = get_meta("recent_start"), get_meta("recent_end")
    if start is None or end is None:
        return None
    return start, end, get_meta("recent_updated_at")


def load_recent():
    """Son 7 günün asteroidləri. Pəncərə yoxdursa, boş cədvəl."""
    window = recent_window()
    if window is None:
        return pd.DataFrame(columns=ASTEROID_COLUMNS)
    start, end, _ = window
    return _query(
        f"SELECT {', '.join(ASTEROID_COLUMNS)} FROM asteroids WHERE date BETWEEN ? AND ? ORDER BY date, name",
        (start, end),
    )


def load_history():
    """Bütün real asteroidlər (nümunə data daxil deyil)."""
    return _query(
        f"SELECT {', '.join(ASTEROID_COLUMNS)} FROM asteroids WHERE is_sample = 0 ORDER BY date, name"
    )


# ---------- Sentry and Close Approach ----------


def _replace_table(table, columns, rows):
    with closing(connect()) as connection, connection:
        connection.execute(f"DELETE FROM {table}")
        _insert(connection, table, columns, rows)
        set_meta(connection, f"{table}_updated_at", now_utc())


def replace_sentry(rows):
    _replace_table("sentry", SENTRY_COLUMNS, rows)


def replace_close_approach(rows):
    _replace_table("close_approach", CLOSE_APPROACH_COLUMNS, rows)


def load_sentry():
    """Sentry siyahısı. Heç vaxt yüklənməyibsə None (boş siyahıdan fərqli)."""
    if get_meta("sentry_updated_at") is None:
        return None
    return _query(f"SELECT {', '.join(SENTRY_COLUMNS)} FROM sentry ORDER BY palermo_cum DESC")


def load_close_approach():
    """Gələcək keçidlər. Heç vaxt yüklənməyibsə None."""
    if get_meta("close_approach_updated_at") is None:
        return None
    return _query(f"SELECT {', '.join(CLOSE_APPROACH_COLUMNS)} FROM close_approach ORDER BY datetime_utc")


def updated_at(table):
    """'recent', 'sentry' və ya 'close_approach' cədvəlinin son yenilənmə vaxtı."""
    return get_meta(f"{table}_updated_at")


# ---------- Migration from the old CSV files ----------


def _read_csv(path):
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def import_csv(data_dir=None):
    """Köhnə data/*.csv fayllarını bazaya köçürür. Nə köçürüldüyünü qaytarır."""
    data_dir = Path(data_dir or DATA_DIR)
    imported = {}

    history_path = data_dir / "history.csv"
    if history_path.exists():
        rows = _read_csv(history_path)
        save_asteroids(rows)
        imported["history.csv"] = len(rows)

    recent_path = data_dir / "asteroids.csv"
    if recent_path.exists():
        rows = _read_csv(recent_path)
        if rows:
            sample = any("SAMPLE" in row["name"] for row in rows)
            dates = [row["date"] for row in rows]
            replace_recent(rows, min(dates), max(dates), sample=sample)
            imported["asteroids.csv"] = len(rows)

    sentry_path = data_dir / "sentry.csv"
    if sentry_path.exists():
        rows = _read_csv(sentry_path)
        replace_sentry(rows)
        imported["sentry.csv"] = len(rows)

    cad_path = data_dir / "close_approach.csv"
    if cad_path.exists():
        rows = _read_csv(cad_path)
        # The old file stored estimated diameters. The database keeps only JPL's
        # own value; the estimate is a rule and is computed in logic.py.
        for row in rows:
            if row.get("diameter_estimated") == "True":
                row["diameter_m"] = None
        replace_close_approach(rows)
        imported["close_approach.csv"] = len(rows)

    return imported


def main():
    parser = argparse.ArgumentParser(description="Space App bazası")
    parser.add_argument("--import-csv", action="store_true", help="data/*.csv fayllarını bazaya köçür")
    args = parser.parse_args()
    if args.import_csv:
        for name, count in import_csv().items():
            print(f"{name}: {count} sətir köçürüldü")
    print(f"Baza: {DB_PATH}")
    print(f"Real asteroid: {count_real_asteroids()}, son 7 gün: {recent_window()}")


if __name__ == "__main__":
    main()
