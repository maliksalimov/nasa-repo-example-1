# Space App: Asteroid radarı

Yerə yaxınlaşan asteroidlər üçün veb tətbiq: son 7 gün, baza xətti və kənar dəyərlər, toqquşma riski (Sentry) və gələcək yaxınlaşmalar.

## İşə salma

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements.txt   # testlər üçün: requirements-dev.txt
echo "NASA_API_KEY=sənin_açarın" > .env  # açar: https://api.nasa.gov
.venv/bin/python data_loader.py              # NeoWs + Sentry + Close Approach -> data/space.db
.venv/bin/python data_loader.py --history 4  # 4 həftəlik NeoWs tarixçəsi

.venv/bin/streamlit run app.py               # ekran 1: Streamlit

(cd web && npm install && npm run build)     # ekran 2: React frontend -> web/dist
.venv/bin/python serve.py                    # http://127.0.0.1:8000
```

Köhnə `data/*.csv` fayllarını bazaya köçürmək (bir dəfə): `.venv/bin/python db.py --import-csv`

Frontend üzərində işləyəndə: `serve.py` açıq qalsın, ayrıca `cd web && npm run dev` (Vite `/api`-ni 8000-ə ötürür).

Testlər: `.venv/bin/python -m pytest` (hər test öz müvəqqəti bazası ilə işləyir, `data/space.db`-yə toxunmur)

## Quruluş

Hər fayl bir iş görür. Asılılıq yalnız yuxarıdan aşağıdır: ekran qaydaları və bazanı çağırır, qaydalar heç nəyi çağırmır.

```
app.py (Streamlit)   serve.py + web/ (React)     ekran
        |                     |
        +------ logic.py -----+                  qaydalar
        |                     |
        +-- data_loader.py ---+                  data: API -> baza
        |        |   simulator.py                data: nümunə data
        +------ db.py --------+                  baza: SQLite
```

| Fayl | Yalnız bunu edir | Bunu etmir |
|---|---|---|
| `app.py` | Streamlit ekranı (cyanotype dizayn, `.streamlit/config.toml`, şrift `static/fonts`), canlı: https://space-app-asteroid-radar.streamlit.app | SQL, API, hesablama |
| `serve.py` | HTTP: `web/dist`, `/api/data` (JSON), `/api/refresh`, yalnız 127.0.0.1 | SQL, API, hesablama |
| `web/` | React + TypeScript ekranı | Python tərəfinə toxunmur, yalnız `/api` |
| `logic.py` | qaydalar: baza xətti, kənar dəyər, diqqət skoru, diametr təxmini, Sentry uyğunluğu, `build_dashboard()` | I/O, ekran mətni |
| `db.py` | SQLite (`data/space.db`): cədvəllər, oxuma, yazma, CSV köçürmə | qayda, API |
| `data_loader.py` | NASA NeoWs, JPL Sentry, JPL Close Approach: götürmək, vahid çevirmək, bazaya yazmaq | qayda, ekran |
| `simulator.py` | API işləməyəndə 30 sətirlik nümunə data | API, baza |

Baza cədvəlləri: `asteroids` (NeoWs, real və nümunə, açar `id + date`), `sentry`, `close_approach`, `meta` (son 7 günün pəncərəsi, yenilənmə vaxtları).

## Dizayn

Cyanotype / astronomik foto lövhəsi: Prussian göyü fon, kağız-ağ mürəkkəb, tək natrium-amber siqnal rəngi. Amber yalnız diqqət tələb edən şey üçündür: NASA-nın "potensial təhlükəli" işarəsi və Aydan yaxın keçid. Şrift: Archivo (variable, en oxu ilə). Əsas element hero-dakı məsafə xəttidir: Yer, Ay məsafəsi və həftənin asteroidləri log şkalada. Light və dark rejim sistem ayarına görə seçilir.

## API işləməyəndə

- NeoWs: bazada real data varsa saxlanılır, yoxdursa `simulator.py` 30 sətirlik nümunə data verir (adı `SAMPLE`, bazada `is_sample = 1`). Hər iki ekran bunu xəbərdarlıqla göstərir. Tarixçəyə və baza xəttinə nümunə data düşmür.
- Sentry / Close Approach: bazadakı köhnə data saxlanılır. Risk datası üçün nümunə data yaradılmır.
- `.env`-də açar yoxdursa `DEMO_KEY` işlədilir (saatda 30 sorğu).

## Fərziyyələr

- NeoWs diametri = API-nin verdiyi min və max-ın ortası.
- Close Approach diametri JPL verməyəndə H-dan hesablanır, albedo 0.14 fərz edilir. Real dəyər 2 dəfəyə qədər fərqli ola bilər.
- Kənar dəyər = Q1 − 1.5×IQR və ya Q3 + 1.5×IQR sərhədindən kənar. Tarixçə varsa sərhədlər tarixçədən hesablanır.
- Diqqət skoru (0–100) yalnız sıralama üçündür, toqquşma ehtimalı deyil: 35 × diametr persentili + 35 × yaxınlıq persentili + 15 təhlükəlidirsə + 15 Sentry-dədirsə.
