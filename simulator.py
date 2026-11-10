"""Nümunə (uydurma) asteroid datası.

API işləməyəndə və bazada heç bir real data olmayanda ekran boş qalmasın deyə
istifadə olunur. Adları "(SAMPLE-01)" kimidir, bazada is_sample = 1 yazılır.
Burada API, baza və ya ekran kodu yoxdur.
"""

import random
from datetime import timedelta

SAMPLE_ROWS = 30
DAYS = 7
SEED = 42  # same seed, same rows: the demo looks the same every time


def make_sample_rows(start, count=SAMPLE_ROWS, days=DAYS, seed=SEED):
    """`start` tarixindən başlayan `days` günə paylanmış `count` uydurma asteroid."""
    rng = random.Random(seed)
    rows = []
    for number in range(1, count + 1):
        day = start + timedelta(days=(number - 1) % days)
        rows.append(
            {
                "name": f"(SAMPLE-{number:02d})",
                "date": day.isoformat(),
                "diameter_m": round(rng.uniform(5, 1200), 2),
                "velocity_km_s": round(rng.uniform(3, 35), 3),
                "miss_distance_km": round(rng.uniform(200_000, 75_000_000), 1),
                "is_hazardous": rng.random() < 0.1,
                "id": f"sample-{number:02d}",
                "is_sentry_object": False,
                "abs_magnitude_h": round(rng.uniform(17, 28), 2),
            }
        )
    return rows
