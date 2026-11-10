"""Ekran qatı (Streamlit): Yerə yaxınlaşan asteroidlər.

Burada yalnız göstərmə var: data db.py-dən, hesablamalar logic.py-dən gəlir,
"Yenilə" düymələri data_loader.py-ni çağırır.

Dizayn: cyanotype / astronomik foto lövhəsi (web/ React versiyası ilə eyni dil).
Prussian göyü fon, kağız-ağ mürəkkəb, tək natrium-amber siqnal yalnız diqqət
tələb edən şey üçün. Şrift Archivo (static/fonts), en oxu ilə. Səhifənin əsas
elementi hero-dakı məsafə xəttidir: Yer, Ay məsafəsi və həftənin asteroidləri.

İşə salmaq: .venv/bin/streamlit run app.py
"""

import html
from datetime import date, datetime

import altair as alt
import pandas as pd
import streamlit as st

import data_loader
import db
import logic

# ---------- Design tokens (match .streamlit/config.toml and web/src/styles.css) ----------

GROUND = "#0e2741"
RAISED = "#13314f"
INK = "#e6edf2"
INK_SOFT = "#93aac0"
RULE = "#284766"
RULE_SOFT = "#1c3a58"
SIGNAL = "#f0a43a"
FONT = "Archivo"

MONTHS_SHORT = ["yan", "fev", "mar", "apr", "may", "iyn", "iyl", "avq", "sen", "okt", "noy", "dek"]
MONTHS_LONG = [
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr",
]
METRIC_NAMES = {"diameter_m": "Diametr", "velocity_km_s": "Sürət", "miss_distance_km": "Yerə məsafə"}
COLLAPSED_ROWS = 8

st.set_page_config(
    page_title="Space App: asteroid radarı",
    page_icon=":material/public:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = f"""
<style>
@font-face {{
  font-family: 'Archivo';
  src: url('app/static/fonts/archivo-latin-wdth-normal.woff2') format('woff2');
  font-weight: 100 900; font-stretch: 62% 125%; font-display: swap;
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC,
    U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}}
@font-face {{
  font-family: 'Archivo';
  src: url('app/static/fonts/archivo-latin-ext-wdth-normal.woff2') format('woff2');
  font-weight: 100 900; font-stretch: 62% 125%; font-display: swap;
  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308,
    U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113,
    U+2C60-2C7F, U+A720-A7FF;
}}
.block-container {{ max-width: 1180px; padding-top: 2.2rem; }}
body, .stApp {{ font-variant-numeric: tabular-nums; }}
h1, h2, h3, .sa-h1, .sa-h2, .sa-wordmark, .sa-value, .sa-verdict, .sa-caption {{
  font-stretch: 72%; letter-spacing: -0.01em; text-wrap: balance;
}}
.sa-wordmark {{ font-weight: 750; font-size: 1.15rem; }}
.sa-updated {{ color: {INK_SOFT}; font-size: 0.875rem; text-align: right; padding-top: 0.45rem; }}
.sa-h1 {{
  font-size: clamp(2.4rem, 6vw, 4.4rem); font-weight: 760; line-height: 1; max-width: 19ch;
  margin: 1.6rem 0 0; padding: 0; color: {INK};
}}
.sa-h2 {{
  font-size: clamp(1.75rem, 3.4vw, 2.6rem); font-weight: 700; line-height: 1.05; max-width: 22ch;
  margin: clamp(2.5rem, 6vw, 4.5rem) 0 0; padding: 0; color: {INK};
}}
.sa-sub {{ color: {INK_SOFT}; font-size: clamp(1.05rem, 1.6vw, 1.25rem); max-width: 52ch; margin-top: 0.6rem; }}
.sa-lead {{ color: {INK_SOFT}; max-width: 68ch; margin: 0.25rem 0 1rem; }}
.sa-foot {{ color: {INK_SOFT}; font-size: 0.8125rem; max-width: 68ch; }}
.sa-legend {{ color: {INK_SOFT}; font-size: 0.875rem; display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: center; }}
.sa-key {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; border: 1.4px solid {INK}; margin-right: 6px; vertical-align: -1px; }}
.sa-key-signal {{ background: {SIGNAL}; border-color: {SIGNAL}; }}
.sa-signal {{ color: #f5b75c; }}
.sa-name {{ color: {INK_SOFT}; font-size: 0.9375rem; }}
.sa-value {{ font-weight: 720; font-size: 2.1rem; line-height: 1.1; }}
.sa-range {{ color: {INK_SOFT}; font-size: 0.875rem; }}
.sa-verdict {{ font-weight: 650; font-size: clamp(1.3rem, 2.4vw, 1.75rem); line-height: 1.2; max-width: 34ch; margin: 0.4rem 0 0.6rem; }}
.sa-caption {{ font-weight: 680; font-size: 1.1rem; margin: 0 0 0.5rem; }}
.sa-table {{ width: 100%; border-collapse: collapse; font-size: 0.9375rem; }}
.sa-table th {{ font-weight: 500; font-size: 0.8125rem; color: {INK_SOFT}; text-align: left; padding: 0 8px 8px 0; border-bottom: 1px solid {RULE}; }}
.sa-table td, .sa-table tbody th {{ padding: 8px 8px 8px 0; vertical-align: top; text-align: left; color: {INK}; font-size: 0.9375rem; border: 0; }}
.sa-table tbody tr + tr > * {{ border-top: 1px solid {RULE_SOFT}; }}
.sa-table tbody th {{ font-weight: 600; }}
.sa-table .num {{ text-align: right; white-space: nowrap; }}
.sa-table .sub {{ display: block; font-weight: 400; font-size: 0.8125rem; color: {INK_SOFT}; }}
.sa-wrap {{ overflow-x: auto; }}
.sa-notes p, .sa-notes li {{ font-size: 0.9375rem; }}
.sa-footer {{ margin-top: 4rem; padding-top: 1.2rem; border-top: 1px solid {RULE_SOFT}; color: {INK_SOFT}; font-size: 0.8125rem; }}
</style>
"""
st.html(CSS)


# ---------- Formatting (screen only) ----------

_SWAP = str.maketrans({",": ".", ".": ","})


def num(value, decimals=0):
    """1234.5 -> "1.234,5" (Azərbaycan yazılışı)."""
    if value is None or pd.isna(value):
        return "naməlum"
    return f"{value:,.{decimals}f}".translate(_SWAP)


def ld(value):
    return num(value, 2 if value < 10 else 1)


def km(value):
    return f"{num(value / 1e6, 1)} mln km" if value >= 1e6 else f"{num(value)} km"


def meters(value):
    return "naməlum" if value is None or pd.isna(value) else f"{num(value)} m"


def metric_text(metric, value):
    if metric == "diameter_m":
        return meters(value)
    if metric == "velocity_km_s":
        return f"{num(value, 1)} km/s"
    return km(value)


def day_short(iso):
    d = date.fromisoformat(str(iso)[:10])
    return f"{d.day} {MONTHS_SHORT[d.month - 1]}"


def day_long(iso):
    d = date.fromisoformat(str(iso)[:10])
    return f"{d.day} {MONTHS_LONG[d.month - 1]}"


def moment(iso):
    t = datetime.fromisoformat(str(iso))
    return f"{t.day} {MONTHS_SHORT[t.month - 1]}, {t:%H:%M}"


def probability(value):
    return f"1 / {num(round(1 / value))}" if value and value > 0 else "yoxdur"


def years(text):
    first, _, last = str(text).partition("-")
    return first if first == last else text


def display_name(name):
    text = str(name)
    return text[1:-1] if text.startswith("(") and text.endswith(")") else text


def esc(value):
    return html.escape(str(value))


def table(headers, rows, caption=None):
    """Kiçik HTML cədvəl. headers: [(mətn, is_number)], rows: [[(html, is_number)]]."""
    head = "".join(f'<th class="{"num" if is_num else ""}">{esc(text)}</th>' for text, is_num in headers)
    body = ""
    for row in rows:
        cells = []
        for index, (content, is_num) in enumerate(row):
            tag = "th" if index == 0 else "td"
            cells.append(f'<{tag} class="{"num" if is_num else ""}">{content}</{tag}>')
        body += f"<tr>{''.join(cells)}</tr>"
    title = f'<p class="sa-caption">{esc(caption)}</p>' if caption else ""
    return f'{title}<div class="sa-wrap"><table class="sa-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def heading(text, level=2):
    st.html(f'<h{level} class="sa-h{level}">{esc(text)}</h{level}>')


def styled(chart, height):
    """Bütün qrafiklər üçün eyni görünüş: şəffaf fon, Archivo, sakit oxlar."""
    return (
        chart.properties(height=height)
        .configure(background="transparent", font=FONT)
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor=INK_SOFT, titleColor=INK_SOFT, gridColor=RULE_SOFT, domainColor=RULE,
            tickColor=RULE, labelFontSize=12, titleFontSize=12, titleFontWeight=600,
        )
        .configure_legend(disable=True)
    )


def lane(name):
    """Addan sabit 0..1 ədəd: nöqtə hər dəfə eyni sətirdə qalsın."""
    value = 2166136261
    for char in str(name):
        value = ((value ^ ord(char)) * 16777619) & 0xFFFFFFFF
    return (value % 1000) / 1000


TOOLTIP = [
    alt.Tooltip("label:N", title="Ad"),
    alt.Tooltip("day:N", title="Tarix"),
    alt.Tooltip("distance_ld:Q", title="Ay məsafəsi", format=".1f"),
    alt.Tooltip("diameter_m:Q", title="Diametr, m", format=",.0f"),
    alt.Tooltip("velocity_km_s:Q", title="Sürət, km/s", format=".1f"),
]


# ---------- Masthead ----------

window = db.recent_window()
left, middle, right_refresh, right_history = st.columns([4, 3, 1.4, 1.1], vertical_alignment="center")
left.html('<span class="sa-wordmark">Space App</span>')
if window and window[2]:
    middle.html(f'<p class="sa-updated">Yenilənib {esc(moment(window[2]))} UTC</p>')

if right_refresh.button("Datanı yenilə", width="stretch"):
    with st.spinner("NASA və JPL-dən data götürülür..."):
        results = data_loader.update_all()
    failed = [name for name, ok in results.items() if not ok]
    names = {"recent": "NASA NeoWs", "sentry": "Sentry", "close_approach": "Close Approach"}
    st.session_state["toast"] = (
        "Data yeniləndi."
        if not failed
        else f"{', '.join(names[n] for n in failed)} cavab vermədi, köhnə data göstərilir."
    )
    st.rerun()

with right_history.popover("Tarixçə", width="stretch"):
    st.markdown("Bir neçə həftəlik NeoWs datası baza xəttini dəqiqləşdirir.")
    weeks = st.number_input("Həftə sayı", min_value=1, max_value=12, value=4)
    st.caption("Hər həftə 1 sorğudur. DEMO_KEY saatda 30 sorğu verir.")
    if st.button("Tarixçəni yığ", width="stretch"):
        with st.spinner(f"{weeks} həftəlik data yığılır..."):
            added = data_loader.fetch_history(int(weeks))
        st.session_state["toast"] = f"Tarixçəyə {added} yeni asteroid əlavə olundu."
        st.rerun()

if "toast" in st.session_state:
    st.toast(st.session_state.pop("toast"))


# ---------- Load ----------

recent = db.load_recent()
if window is None or recent.empty:
    heading("Asteroid datası hələ yoxdur.", 1)
    st.markdown(
        '<p class="sa-sub">"Datanı yenilə" düyməsi son 7 günü NASA-dan, risk datasını JPL-dən götürəcək.</p>',
        unsafe_allow_html=True,
    )
    st.stop()

dashboard = logic.build_dashboard(recent, db.load_history(), db.load_sentry(), db.load_close_approach())
asteroids = dashboard.asteroids.assign(
    label=lambda d: d["name"].map(display_name),
    day=lambda d: d["date"].map(day_long),
    lane=lambda d: d["name"].map(lane),
)
start_iso, end_iso, _ = window
chart_data = asteroids.drop(columns=["outlier_reasons"])

if dashboard.is_sample:
    st.warning(
        "Bu nümunə datadır, real NASA datası deyil. .env faylına NASA_API_KEY yaz və \"Datanı yenilə\" düyməsini bas."
    )


# ---------- Hero: the distance strip ----------

closest = asteroids.loc[asteroids["distance_ld"].idxmin()]
if dashboard.sentry is None:
    risk_line = ""
elif dashboard.torino_positive:
    risk_line = "Sentry siyahısında diqqət tələb edən obyekt var, aşağıya bax."
else:
    risk_line = "Yerə dəymə riski olan obyekt yoxdur."

heading(f"Bu həftə {len(asteroids)} asteroid Yerin yanından keçdi.", 1)
st.markdown(
    f'<p class="sa-sub">Ən yaxını, {esc(closest["label"])}, Aydan {num(closest["distance_ld"], 1)} dəfə uzaqda idi. '
    f"{risk_line}</p>",
    unsafe_allow_html=True,
)

far = asteroids["distance_ld"].max() * 1.3
x_scale = alt.Scale(type="log", domain=[0.3, far])
size_scale = alt.Scale(type="sqrt", domain=[0, asteroids["diameter_m"].max()], range=[25, 650])
strip_x = alt.X(
    "distance_ld:Q",
    scale=x_scale,
    title=None,
    axis=alt.Axis(
        values=[1, 2, 5, 10, 20, 50, 100, 200, 500],
        labelExpr="datum.value == 1 ? 'Ay' : (datum.value == 10 || datum.value == 100) ? datum.value + ' Ay məsafəsi' : ''",
        grid=True, domain=False, ticks=False, labelPadding=10,
    ),
)
lane_y = alt.Y("lane:Q", scale=alt.Scale(domain=[-0.15, 1.15]), axis=None)
base = alt.Chart(chart_data)
earth = alt.Chart(pd.DataFrame({"distance_ld": [0.36], "lane": [0.5], "text": ["Yer"]}))
moon = alt.Chart(pd.DataFrame({"distance_ld": [1]}))
strip = alt.layer(
    moon.mark_rule(color=INK_SOFT, strokeDash=[3, 4]).encode(x=strip_x),
    earth.mark_circle(size=520, color=INK, opacity=1).encode(x=strip_x, y=lane_y),
    earth.mark_text(dy=34, color=INK, fontWeight=600).encode(x=strip_x, y=lane_y, text="text:N"),
    base.transform_filter("!datum.is_hazardous").mark_point(filled=False, color=INK, strokeWidth=1.4, opacity=0.9)
    .encode(x=strip_x, y=lane_y, size=alt.Size("diameter_m:Q", scale=size_scale), tooltip=TOOLTIP),
    base.transform_filter("datum.is_hazardous").mark_circle(color=SIGNAL, opacity=1)
    .encode(x=strip_x, y=lane_y, size=alt.Size("diameter_m:Q", scale=size_scale), tooltip=TOOLTIP),
    alt.Chart(chart_data.loc[[closest.name]]).mark_text(align="right", dx=-14, color=INK, fontWeight=600)
    .encode(x=strip_x, y=lane_y, text=alt.value(f"Ən yaxın: {num(closest['distance_ld'], 1)}")),
)
st.altair_chart(styled(strip, 240), width="stretch")
st.html(
    '<p class="sa-legend"><span><span class="sa-key sa-key-signal"></span>Potensial təhlükəli (NASA təsnifatı)</span>'
    '<span><span class="sa-key"></span>Digərləri</span>'
    "<span>Dairənin ölçüsü diametri göstərir. Şkala loqarifmikdir.</span></p>"
)


# ---------- Which ones need attention? ----------

heading("Hansılarına diqqət etmək lazımdır?")
st.markdown(
    f'<p class="sa-lead">{day_long(start_iso)} ilə {day_long(end_iso)} arası. '
    "Böyük və yaxın keçənlər qrafikin sol yuxarı küncündədir.</p>",
    unsafe_allow_html=True,
)

days = sorted(asteroids["date"].unique())
filter_left, filter_right = st.columns([3, 1.3], vertical_alignment="center")
picked_day = filter_left.pills(
    "Gün", ["all", *days], default="all", format_func=lambda d: "Bütün həftə" if d == "all" else day_short(d),
    label_visibility="collapsed",
)
only_hazardous = filter_right.toggle("Yalnız potensial təhlükəlilər")
day_filter = None if picked_day in (None, "all") else picked_day
filtered = logic.filter_asteroids(asteroids, day_filter, day_filter, only_hazardous)

if filtered.empty:
    st.info("Bu filtrə uyğun asteroid yoxdur. Başqa gün seç və ya filtri söndür.")
else:
    chart_col, list_col = st.columns([1.55, 1], gap="large")
    x = alt.X(
        "distance_ld:Q", scale=alt.Scale(type="log", domain=[asteroids["distance_ld"].min() * 0.8, far]),
        title="Yerdən məsafə, Ay məsafəsi ilə",
        axis=alt.Axis(values=[5, 10, 20, 50, 100, 200, 500]),
    )
    y = alt.Y(
        "diameter_m:Q",
        scale=alt.Scale(type="log", domain=[asteroids["diameter_m"].min() * 0.7, asteroids["diameter_m"].max() * 1.4]),
        title="Diametr, m",
        axis=alt.Axis(values=[3, 10, 30, 100, 300, 1000]),
    )
    points = alt.Chart(filtered.drop(columns=["outlier_reasons"]))
    scatter = alt.layer(
        points.transform_filter("datum.is_outlier").mark_point(size=420, color=INK_SOFT, strokeDash=[2, 3])
        .encode(x=x, y=y),
        points.transform_filter("!datum.is_hazardous").mark_point(size=80, filled=False, color=INK, strokeWidth=1.4)
        .encode(x=x, y=y, tooltip=TOOLTIP),
        points.transform_filter("datum.is_hazardous").mark_circle(size=90, color=SIGNAL, opacity=1)
        .encode(x=x, y=y, tooltip=TOOLTIP),
    )
    chart_col.altair_chart(styled(scatter, 380), width="stretch")
    chart_col.html('<p class="sa-foot">Kəsik halqa: baza xəttinə görə normadan kənar.</p>')

    def ranking_rows(frame):
        rows = []
        for _, a in frame.iterrows():
            notes = [day_short(a["date"])]
            if a["is_hazardous"]:
                notes.append('<span class="sa-signal">potensial təhlükəli</span>')
            if a["is_outlier"]:
                notes.append("normadan kənar")
            rows.append([
                (f'{esc(a["label"])}<span class="sub">{", ".join(notes)}</span>', False),
                (meters(a["diameter_m"]), True),
                (num(a["distance_ld"], 1), True),
                (num(a["attention_score"]), True),
            ])
        return rows

    headers = [("Ad", False), ("Diametr", True), ("Ay məs.", True), ("Bal", True)]
    list_col.html(table(headers, ranking_rows(filtered.head(COLLAPSED_ROWS)), f"Diqqət sırası, {len(filtered)} asteroid"))
    if len(filtered) > COLLAPSED_ROWS:
        with list_col.expander(f"Hamısını göstər ({len(filtered)})"):
            st.html(table(headers, ranking_rows(filtered.iloc[COLLAPSED_ROWS:])))
    list_col.html(
        '<p class="sa-foot">Bal 0-100 arasıdır və yalnız sıralama üçündür, toqquşma ehtimalı deyil. '
        "Ölçü və yaxınlıq 35-ər, NASA təhlükə işarəsi və Sentry siyahısı 15-ər bal verir.</p>"
    )


# ---------- Is this a normal week? ----------

heading("Bu həftə adi həftədirmi?")
reference = dashboard.reference
if dashboard.reference_source == "history":
    span = (date.fromisoformat(reference["date"].max()) - date.fromisoformat(reference["date"].min())).days + 1
    lead = (
        f"Norma son {round(span / 7)} həftənin {num(len(reference))} asteroidindən hesablanıb "
        f"({day_long(reference['date'].min())} ilə {day_long(reference['date'].max())} arası)."
    )
else:
    lead = "Tarixçə yoxdur, ona görə norma yalnız bu həftədən hesablanır. Daha dəqiq norma üçün yuxarıdakı \"Tarixçə\" ilə data yığ."
st.markdown(f'<p class="sa-lead">{esc(lead)}</p>', unsafe_allow_html=True)

comparison = (
    dashboard.comparison.set_index("metric") if dashboard.comparison is not None else None
)
for column, metric in zip(st.columns(3, gap="large"), logic.METRICS):
    stats = dashboard.baseline[metric]
    column.html(
        f'<div class="sa-name">{METRIC_NAMES[metric]}</div>'
        f'<div class="sa-value">{metric_text(metric, stats["median"])}</div>'
        f'<div class="sa-range">Normal aralıq {metric_text(metric, stats["q1"])} ilə {metric_text(metric, stats["q3"])} arası</div>'
    )
    scale_max = max(stats["max"], asteroids[metric].max())
    if metric == "miss_distance_km":
        axis = alt.Axis(labelExpr="format(datum.value / 1e6, '.0f') + ' mln km'", tickCount=4, grid=False)
    elif metric == "diameter_m":
        axis = alt.Axis(labelExpr="format(datum.value, ',.0f') + ' m'", tickCount=4, grid=False)
    else:
        axis = alt.Axis(labelExpr="datum.value + ' km/s'", tickCount=4, grid=False)
    linear = alt.Scale(domain=[0, scale_max])

    def hx(field, **extra):
        return alt.X(f"{field}:Q", scale=linear, axis=axis, title=None, **extra)

    histogram = alt.layer(
        alt.Chart(pd.DataFrame([stats])).mark_rect(color=INK_SOFT, opacity=0.14).encode(x=hx("q1"), x2="q3:Q"),
        alt.Chart(reference[[metric]]).mark_bar(color=INK_SOFT, opacity=0.55, binSpacing=1)
        .encode(x=hx(metric, bin=alt.Bin(maxbins=24, extent=[0, scale_max])), y=alt.Y("count():Q", axis=None)),
        alt.Chart(pd.DataFrame([stats])).mark_rule(color=INK, strokeWidth=2).encode(x=hx("median")),
        alt.Chart(asteroids[[metric]]).mark_tick(color=INK, thickness=1.2, size=9, yOffset=7)
        .encode(x=hx(metric), y=alt.datum(0)),
    )
    column.altair_chart(styled(histogram, 140), width="stretch")
    if comparison is not None:
        row = comparison.loc[metric]
        change = round((row["ratio"] - 1) * 100)
        verdict = (
            "normaya yaxındır" if abs(change) < 3
            else f"normadan {change}% çoxdur" if change > 0
            else f"normadan {abs(change)}% azdır"
        )
        column.html(f'<p>Bu həftənin medianı {metric_text(metric, row["recent_median"])}, {verdict}.</p>')

st.html(
    '<p class="sa-foot">Açıq zolaq normal aralıqdır (ortadakı 50%). Xətt mediandır. '
    "Sütunların altındakı qısa cizgilər bu həftənin asteroidləridir.</p>"
)

outliers = asteroids[asteroids["is_outlier"]]
st.markdown("### Normadan kənar keçənlər")
if outliers.empty:
    st.markdown("Bu həftə heç bir asteroid normal aralıqdan uzaq deyil.")
else:
    lines = []
    for _, a in outliers.iterrows():
        parts = []
        for metric in a["outlier_reasons"]:
            stats = dashboard.baseline[metric]
            above = a[metric] > stats["upper_fence"]
            limit = metric_text(metric, stats["upper_fence"] if above else stats["lower_fence"])
            parts.append(
                f"{METRIC_NAMES[metric].lower()} {metric_text(metric, a[metric])} ({'yuxarı' if above else 'aşağı'} hədd {limit})"
            )
        lines.append(f"- **{a['label']}**, {', '.join(parts)}.")
    st.markdown("\n".join(lines))

if dashboard.weekly is not None and len(dashboard.weekly) > 1:
    st.markdown("### Həftə-həftə")
    rows = [
        [
            (f"{day_long(w.week.date().isoformat())} həftəsi", False),
            (num(w.count), True),
            (f"{num(w.hazardous_pct)}%", True),
            (meters(w.median_diameter_m), True),
        ]
        for w in dashboard.weekly.itertuples()
    ]
    week_col, _ = st.columns([1.2, 1])
    week_col.html(table([("Həftə", False), ("Asteroid", True), ("Potensial təhlükəli", True), ("Median diametr", True)], rows))


# ---------- Objects that could hit Earth ----------

heading("Yerə dəyə biləcək obyektlər")
sentry = dashboard.sentry
if sentry is None:
    st.info("Sentry datası yoxdur. Yuxarıdakı \"Datanı yenilə\" düyməsi onu JPL-dən götürəcək.")
else:
    if dashboard.torino_positive:
        verdict = f"Torino şkalasında 0‑dan yuxarı {len(dashboard.torino_positive)} obyekt var: {', '.join(dashboard.torino_positive)}."
        st.html(f'<p class="sa-verdict sa-signal">{esc(verdict)}</p>')
    else:
        st.html('<p class="sa-verdict">Hazırda Torino şkalasında 0‑dan yuxarı heç bir obyekt yoxdur.</p>')
    st.markdown(
        f'<p class="sa-lead">NASA JPL-in Sentry sistemi gələcək 100 ildə Yerə dəymə ehtimalı sıfır olmayan '
        f"{num(len(sentry))} obyekti izləyir. Torino 0 o deməkdir ki, ehtimal o qədər kiçikdir ki, narahatlığa səbəb yoxdur.</p>",
        unsafe_allow_html=True,
    )
    table_col, notes_col = st.columns([1.7, 1], gap="large")
    rows = [
        [
            (esc(item.name), False),
            (esc(years(item.years)), False),
            (probability(item.impact_probability), True),
            (num(item.palermo_cum, 2), True),
            (meters(item.diameter_m), True),
        ]
        for item in dashboard.sentry_top.itertuples()
    ]
    table_col.html(
        table(
            [("Ad", False), ("Mümkün illər", False), ("Ehtimal", True), ("Palermo", True), ("Diametr", True)],
            rows,
            f"Palermo şkalasına görə ilk {len(rows)}",
        )
    )
    with notes_col:
        st.markdown("### Bu həftə keçənlərdən")
        matches = dashboard.sentry_matches
        if not matches.empty:
            st.markdown(
                "\n".join(
                    f"- **{display_name(m['name'])}** {day_long(m['date'])} günü {num(m['distance_ld'], 1)} Ay məsafəsindən keçdi. "
                    f"Sentry-də dəymə ehtimalı {probability(m['sentry_impact_probability'])}, {years(m['sentry_years'])} illəri üçün."
                    for _, m in matches.iterrows()
                )
            )
        elif dashboard.sentry_flagged:
            st.markdown(
                "NeoWs bunları Sentry obyekti kimi işarələyib: "
                + ", ".join(display_name(n) for n in dashboard.sentry_flagged)
                + ". Sentry siyahısında ad uyğunluğu tapılmadı."
            )
        else:
            st.markdown("Bu həftə keçən asteroidlərin heç biri Sentry siyahısında deyil.")
        st.markdown("### Şkalaları necə oxumaq")
        st.markdown(
            "Palermo -2-dən aşağıdırsa, risk fon səviyyəsindən çox kiçikdir. 0-dan yuxarı olsa, xüsusi diqqət tələb edir. "
            "Torino 0-10 arası ictimaiyyət üçün şkaladır."
        )


# ---------- Upcoming passes ----------

heading("Növbəti 60 gündə kim yaxınlaşacaq?")
future = dashboard.close_approach
if future is None:
    st.info("Yaxınlaşma datası yoxdur. Yuxarıdakı \"Datanı yenilə\" düyməsi onu JPL-dən götürəcək.")
elif future.empty:
    st.markdown("Növbəti 60 gündə 19,5 Ay məsafəsindən yaxın keçid gözlənilmir.")
else:
    inside = int((future["distance_ld"] < 1).sum())
    st.markdown(
        f'<p class="sa-lead">19,5 Ay məsafəsi (0,05 AB) daxilində {len(future)} keçid gözlənilir. '
        + (f"{inside} asteroid Aydan da yaxın keçəcək, onlar qrafikdə rənglidir.</p>" if inside else "Heç biri Aydan yaxın keçməyəcək.</p>"),
        unsafe_allow_html=True,
    )
    timeline_data = future.assign(
        when=pd.to_datetime(future["datetime_utc"]),
        size_m=future["diameter_m"].fillna(1),
        inside=future["distance_ld"] < 1,
        label=future["designation"],
        day=future["datetime_utc"].map(moment),
    )
    months = "[" + ", ".join(f"'{m}'" for m in MONTHS_SHORT) + "]"
    tx = alt.X(
        "when:T", title=None,
        axis=alt.Axis(labelExpr=f"date(datum.value) + ' ' + {months}[month(datum.value)]", grid=False, tickCount=6),
    )
    ty = alt.Y(
        "distance_ld:Q",
        scale=alt.Scale(type="log", domain=[min(0.5, future["distance_ld"].min() * 0.8), future["distance_ld"].max() * 1.15]),
        title=None,
        axis=alt.Axis(values=[0.5, 1, 2, 5, 10, 20], labelExpr="replace(format(datum.value, ''), '.', ',')"),
    )
    tsize = alt.Size("size_m:Q", scale=alt.Scale(type="sqrt", range=[20, 500]))
    ttip = [
        alt.Tooltip("label:N", title="Ad"),
        alt.Tooltip("day:N", title="Vaxt (UTC)"),
        alt.Tooltip("distance_ld:Q", title="Ay məsafəsi", format=".2f"),
        alt.Tooltip("diameter_m:Q", title="Diametr, m", format=",.0f"),
        alt.Tooltip("velocity_km_s:Q", title="Sürət, km/s", format=".1f"),
    ]
    passes = alt.Chart(timeline_data)
    moon_line = alt.Chart(pd.DataFrame({"distance_ld": [1], "text": ["Ay məsafəsi"]}))
    timeline = alt.layer(
        moon_line.mark_rule(color=INK_SOFT, strokeDash=[3, 4]).encode(y=ty),
        moon_line.mark_text(align="right", dy=-8, color=INK, fontWeight=600).encode(
            y=ty, x=alt.value("width"), text="text:N"
        ),
        passes.transform_filter("!datum.inside").mark_point(filled=False, color=INK, strokeWidth=1.3)
        .encode(x=tx, y=ty, size=tsize, tooltip=ttip),
        passes.transform_filter("datum.inside").mark_circle(color=SIGNAL, opacity=1)
        .encode(x=tx, y=ty, size=tsize, tooltip=ttip),
    )
    st.altair_chart(styled(timeline, 300), width="stretch")

    nearest = future.sort_values("distance_ld").head(5)
    rows = [
        [
            (f'<span class="{"sa-signal" if p.distance_ld < 1 else ""}">{esc(p.designation)}</span>', False),
            (esc(moment(p.datetime_utc)), False),
            (ld(p.distance_ld), True),
            (("≈ " if p.diameter_estimated and not pd.isna(p.diameter_m) else "") + meters(p.diameter_m), True),
            (f"{num(p.velocity_km_s, 1)} km/s", True),
        ]
        for p in nearest.itertuples()
    ]
    near_col, _ = st.columns([1.4, 1])
    near_col.html(
        table([("Ad", False), ("Vaxt (UTC)", False), ("Ay məs.", True), ("Diametr", True), ("Sürət", True)], rows,
              f"Ən yaxın {len(rows)} keçid")
    )
    st.html(
        '<p class="sa-foot">≈ işarəli diametrlər parlaqlıqdan təxmin olunub (albedo 0,14), '
        "real ölçü 2 dəfəyə qədər fərqli ola bilər.</p>"
    )

st.html(
    '<div class="sa-footer">Data: NASA NeoWs (api.nasa.gov), NASA JPL CNEOS Sentry və Close Approach '
    "(ssd-api.jpl.nasa.gov). Hesablamalar bu tətbiqdədir, NASA-nın rəsmi qiymətləndirməsi deyil.</div>"
)
