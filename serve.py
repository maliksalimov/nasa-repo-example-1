"""Ekran qatı (veb): React frontendi (web/dist) və onun API-sini göstərir.

- GET  /api/data            bazadakı data + logic.py nəticələri, JSON kimi
- POST /api/refresh         data_loader ilə bütün mənbələri yeniləyir
- POST /api/history?weeks=4 data_loader ilə NeoWs tarixçəsi yığır

Burada qayda və SQL yoxdur: data db.py-dən, hesablamalar logic.py-dən gəlir,
bu fayl yalnız onları JSON-a çevirib göndərir.

İşə salmaq:
    (cd web && npm run build)
    .venv/bin/python serve.py          # http://127.0.0.1:8000
"""

import argparse
import json
import math
import mimetypes
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd

import data_loader
import db
import logic

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "web" / "dist"
REFRESH_LOCK = threading.Lock()

ASTEROID_FIELDS = [
    "name", "date", "diameter_m", "velocity_km_s", "miss_distance_km", "distance_ld",
    "is_hazardous", "is_sentry_object", "attention_score", "is_outlier", "outlier_reasons",
]
SENTRY_FIELDS = ["name", "years", "impact_probability", "palermo_cum", "torino_max", "diameter_m", "n_impacts"]
MATCH_FIELDS = [
    "name", "date", "distance_ld", "diameter_m",
    "sentry_impact_probability", "sentry_palermo_cum", "sentry_years",
]
CLOSE_APPROACH_FIELDS = [
    "designation", "datetime_utc", "date", "distance_km", "distance_ld", "velocity_km_s",
    "abs_magnitude_h", "diameter_m", "diameter_estimated",
]


# ---------- JSON ----------


def clean(value):
    """pandas/numpy dəyərlərini JSON-a uyğun Python tiplərinə çevirir."""
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):  # numpy scalar
        value = value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def records(df, fields=None):
    if df is None or df.empty:
        return []
    if fields is not None:
        df = df[fields]
    return [clean(row) for row in df.to_dict(orient="records")]


def baseline_json(dashboard):
    reference = dashboard.reference
    metrics = {}
    for column in logic.METRICS:
        stats = dict(dashboard.baseline[column])
        stats["values"] = pd.to_numeric(reference[column], errors="coerce").dropna().round(3).tolist()
        metrics[column] = stats
    weekly = None
    if dashboard.weekly is not None:
        weekly = dashboard.weekly.assign(week=dashboard.weekly["week"].dt.date.astype(str))
    return clean(
        {
            "source": dashboard.reference_source,
            "start": reference["date"].min(),
            "end": reference["date"].max(),
            "count": len(reference),
            "metrics": metrics,
            "comparison": records(dashboard.comparison) if dashboard.comparison is not None else None,
            "weekly": records(weekly) if weekly is not None else None,
        }
    )


def sentry_json(dashboard):
    if dashboard.sentry is None:
        return None
    return clean(
        {
            "count": len(dashboard.sentry),
            "updated_at": db.updated_at("sentry"),
            "torino_positive": dashboard.torino_positive,
            "max_palermo": dashboard.sentry["palermo_cum"].max(),
            "top": records(dashboard.sentry_top, SENTRY_FIELDS),
            "recent_matches": records(dashboard.sentry_matches, MATCH_FIELDS),
            "recent_flagged": dashboard.sentry_flagged,
        }
    )


def build_payload():
    window = db.recent_window()
    recent = db.load_recent()
    if window is None or recent.empty:
        return {"recent": None}
    start, end, updated = window

    dashboard = logic.build_dashboard(recent, db.load_history(), db.load_sentry(), db.load_close_approach())
    close_approach = None
    if dashboard.close_approach is not None:
        close_approach = {
            "updated_at": db.updated_at("close_approach"),
            "items": records(dashboard.close_approach, CLOSE_APPROACH_FIELDS),
        }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "is_sample": dashboard.is_sample,
        "recent": {
            "start": start,
            "end": end,
            "updated_at": updated,
            "asteroids": records(dashboard.asteroids, ASTEROID_FIELDS),
        },
        "baseline": baseline_json(dashboard),
        "sentry": sentry_json(dashboard),
        "close_approach": close_approach,
    }


# ---------- HTTP ----------


class Handler(BaseHTTPRequestHandler):
    server_version = "SpaceApp/1.0"

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/data":
            try:
                self.send_json(build_payload())
            except Exception as error:  # report, do not crash the server
                self.send_json({"error": f"Data oxunmadı: {error}"}, 500)
            return
        self.serve_static(path)

    def do_POST(self):
        url = urlparse(self.path)
        # Requiring a JSON content type forces a CORS preflight, so other
        # websites cannot trigger refreshes from the user's browser.
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            self.send_json({"error": "Content-Type application/json olmalıdır"}, 415)
            return
        if url.path not in ("/api/refresh", "/api/history"):
            self.send_json({"error": "Belə ünvan yoxdur"}, 404)
            return
        if not REFRESH_LOCK.acquire(blocking=False):
            self.send_json({"error": "Yeniləmə artıq gedir"}, 409)
            return
        try:
            if url.path == "/api/refresh":
                self.send_json(data_loader.update_all())
            else:
                weeks = int(parse_qs(url.query).get("weeks", ["4"])[0])
                self.send_json({"added": data_loader.fetch_history(max(1, min(weeks, 12)))})
        finally:
            REFRESH_LOCK.release()

    def serve_static(self, path):
        if not DIST_DIR.exists():
            self.send_json({"error": "web/dist yoxdur. Əvvəl: cd web && npm run build"}, 404)
            return
        target = (DIST_DIR / path.lstrip("/")).resolve()
        if not target.is_relative_to(DIST_DIR.resolve()) or not target.is_file():
            target = DIST_DIR / "index.html"  # single-page app fallback
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        if "/api/" in self.path:
            super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(description="Space App veb serveri")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Space App: http://127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
