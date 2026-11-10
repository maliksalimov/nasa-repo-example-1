"""Ekran qatı (Streamlit): Yerə yaxınlaşan asteroidlər üçün dashboard.

Burada yalnız göstərmə var: data db.py-dən, hesablamalar logic.py-dən gəlir,
"Yenilə" düymələri data_loader.py-ni çağırır.

İşə salmaq: .venv/bin/streamlit run app.py
"""

from datetime import date, datetime

import altair as alt
import pandas as pd
import streamlit as st

import data_loader
import db
import logic

HAZARD_COLOR = "#d62728"
NORMAL_COLOR = "#1f77b4"

METRIC_LABELS = {
    "diameter_m": "Diametr, m",
    "velocity_km_s": "Sürət, km/s",
    "miss_distance_km": "Yerə məsafə, km",
}
BASELINE_LABELS = {
    "count": "Say",
    "median": "Median",
    "q1": "Q1",
    "q3": "Q3",
    "iqr": "IQR",
    "lower_fence": "Aşağı sərhəd",
    "upper_fence": "Yuxarı sərhəd",
    "min": "Min",
    "max": "Max",
    "mean": "Ortalama",
}

st.set_page_config(page_title="Space App: Asteroid radarı", page_icon="☄️", layout="wide")


# ---------- Formatting (screen only) ----------


def format_probability(probability):
    """0.000571 -> "1 / 1,749"."""
    if not probability or probability <= 0:
        return "—"
    return f"1 / {round(1 / probability):,}"


def format_time(iso):
    if not iso:
        return "naməlum"
    return datetime.fromisoformat(iso).astimezone().strftime("%Y-%m-%d %H:%M")


# ---------- Sidebar: refresh ----------

st.sidebar.header("Data")

if st.sidebar.button("Datanı yenilə", type="primary", width="stretch"):
    with st.spinner("NASA və JPL-dən data götürülür..."):
        results = data_loader.update_all()
    st.session_state["refresh_message"] = (
        ("success", "Bütün data yeniləndi.")
        if all(results.values())
        else ("warning", "Bəzi mənbələr işləmədi, köhnə data göstərilir. Terminala bax.")
    )
    st.rerun()

with st.sidebar.expander("Tarixçə yığ (baza xətti üçün)"):
    weeks = st.number_input("Həftə sayı", min_value=1, max_value=12, value=4)
    st.caption("Hər həftə 1 sorğudur. DEMO_KEY saatda 30 sorğu verir.")
    if st.button("Tarixçəni yığ", width="stretch"):
        with st.spinner(f"{weeks} həftəlik data yığılır..."):
            added = data_loader.fetch_history(int(weeks))
        st.session_state["refresh_message"] = ("success", f"Tarixçəyə {added} yeni asteroid əlavə olundu.")
        st.rerun()

if "refresh_message" in st.session_state:
    level, text = st.session_state.pop("refresh_message")
    getattr(st.sidebar, level)(text)


# ---------- Load ----------

st.title("☄️ Space App: Asteroid radarı")

window = db.recent_window()
recent = db.load_recent()
if window is None or recent.empty:
    st.error("Bazada asteroid datası yoxdur. Soldakı **Datanı yenilə** düyməsini bas.")
    st.stop()

dashboard = logic.build_dashboard(recent, db.load_history(), db.load_sentry(), db.load_close_approach())
asteroids = dashboard.asteroids
reference = dashboard.reference
start_iso, end_iso, updated = window

reference_label = (
    f"tarixçə ({reference['date'].min()} – {reference['date'].max()}, {len(reference)} asteroid)"
    if dashboard.reference_source == "history"
    else "son 7 gün (tarixçə yoxdur)"
)
st.caption(f"Son 7 gün: {start_iso} – {end_iso} · yenilənib: {format_time(updated)} · baza xətti: {reference_label}")

if dashboard.is_sample:
    st.warning(
        "⚠️ Bu **nümunə (uydurma) datadır**, real NASA datası deyil. "
        "API açarını `.env`-ə yaz və **Datanı yenilə** düyməsini bas."
    )


# ---------- Sidebar: filters ----------

st.sidebar.header("Filtr")
first_day, last_day = date.fromisoformat(start_iso), date.fromisoformat(end_iso)
picked = st.sidebar.date_input("Tarix aralığı", value=(first_day, last_day), min_value=first_day, max_value=last_day)
start_day, end_day = (picked[0], picked[-1]) if isinstance(picked, (tuple, list)) and picked else (first_day, last_day)
only_hazardous = st.sidebar.checkbox("Yalnız təhlükəlilər")

filtered = logic.filter_asteroids(asteroids, start_day.isoformat(), end_day.isoformat(), only_hazardous)
if filtered.empty:
    st.info("Filtrə uyğun asteroid yoxdur.")
    st.stop()

view = filtered.assign(
    status=filtered["is_hazardous"].map({True: "Təhlükəli", False: "Adi"}),
    outlier_label=filtered["is_outlier"].map({True: "Kənar dəyər", False: "Normal"}),
)


# ---------- KPI ----------

kpi = st.columns(4)
closest = view.loc[view["miss_distance_km"].idxmin()]
largest = view.loc[view["diameter_m"].idxmax()]
kpi[0].metric("Asteroid sayı", len(view))
kpi[1].metric("Təhlükəli", f"{view['is_hazardous'].mean():.0%}", f"{view['is_hazardous'].sum()} ədəd", delta_color="off")
kpi[2].metric("Ən yaxın keçid", f"{closest['distance_ld']:.1f} LD", closest["name"], delta_color="off")
kpi[3].metric("Ən böyük", f"{largest['diameter_m']:,.0f} m", largest["name"], delta_color="off")


# ---------- Tabs ----------

tab_recent, tab_baseline, tab_sentry, tab_future = st.tabs(
    ["Son 7 gün", "Baza xətti", "Toqquşma riski (Sentry)", "Gələcək yaxınlaşmalar"]
)

ASTEROID_COLUMNS = {
    "name": st.column_config.TextColumn("Ad"),
    "date": st.column_config.TextColumn("Tarix"),
    "attention_score": st.column_config.ProgressColumn("Diqqət skoru", min_value=0, max_value=100, format="%.0f"),
    "diameter_m": st.column_config.NumberColumn("Diametr, m", format="%.1f"),
    "velocity_km_s": st.column_config.NumberColumn("Sürət, km/s", format="%.2f"),
    "distance_ld": st.column_config.NumberColumn("Məsafə, LD", format="%.1f"),
    "miss_distance_km": st.column_config.NumberColumn("Məsafə, km", format="localized"),
    "is_hazardous": st.column_config.CheckboxColumn("Təhlükəli"),
    "is_sentry_object": st.column_config.CheckboxColumn("Sentry"),
    "is_outlier": st.column_config.CheckboxColumn("Kənar dəyər"),
}

with tab_recent:
    scatter = (
        alt.Chart(view.drop(columns=["outlier_reasons"]))
        .mark_point(filled=True, size=110, opacity=0.8)
        .encode(
            x=alt.X("distance_ld:Q", scale=alt.Scale(type="log"), title="Yerə məsafə, LD (log)"),
            y=alt.Y("diameter_m:Q", scale=alt.Scale(type="log"), title="Diametr, m (log)"),
            color=alt.Color(
                "status:N",
                title="Status",
                scale=alt.Scale(domain=["Təhlükəli", "Adi"], range=[HAZARD_COLOR, NORMAL_COLOR]),
            ),
            shape=alt.Shape(
                "outlier_label:N",
                title="Baza xəttinə görə",
                scale=alt.Scale(domain=["Normal", "Kənar dəyər"], range=["circle", "diamond"]),
            ),
            tooltip=[
                alt.Tooltip("name:N", title="Ad"),
                alt.Tooltip("date:N", title="Tarix"),
                alt.Tooltip("diameter_m:Q", title="Diametr, m", format=",.1f"),
                alt.Tooltip("distance_ld:Q", title="Məsafə, LD", format=".1f"),
                alt.Tooltip("velocity_km_s:Q", title="Sürət, km/s", format=".2f"),
                alt.Tooltip("attention_score:Q", title="Diqqət skoru"),
            ],
        )
        .properties(height=420)
        .interactive()
    )
    st.altair_chart(scatter, width="stretch")
    st.caption("Sol yuxarı künc = böyük və yaxın. 1 LD = Yerdən Aya qədər məsafə (384 400 km).")

    st.subheader("Diqqət skoruna görə sıralama")
    st.dataframe(view[list(ASTEROID_COLUMNS)], column_config=ASTEROID_COLUMNS, hide_index=True, width="stretch")
    st.caption(
        "Diqqət skoru (0–100) yalnız sıralama üçündür, **toqquşma ehtimalı deyil**: "
        "35 × diametr persentili + 35 × yaxınlıq persentili + 15 təhlükəlidirsə + 15 Sentry-dədirsə. "
        "Real risk üçün **Toqquşma riski** tabına bax."
    )

with tab_baseline:
    st.markdown(
        f"Baza xətti mənbəyi: **{reference_label}**. Normal aralıq = Q1–Q3, kənar dəyər = IQR × 1.5 sərhədindən kənar."
    )
    table = logic.baseline_table(reference).rename(index=METRIC_LABELS, columns=BASELINE_LABELS)
    st.dataframe(
        table,
        column_config={
            label: st.column_config.NumberColumn(label, format="localized")
            for key, label in BASELINE_LABELS.items()
            if key != "count"
        },
        width="stretch",
    )

    if dashboard.comparison is not None:
        st.subheader("Son 7 gün baza xətti ilə müqayisədə")
        comparison = dashboard.comparison.assign(metric=dashboard.comparison["metric"].map(METRIC_LABELS))
        st.dataframe(
            comparison,
            column_config={
                "metric": "Göstərici",
                "recent_median": st.column_config.NumberColumn("Son 7 gün (median)", format="localized"),
                "baseline_median": st.column_config.NumberColumn("Baza xətti (median)", format="localized"),
                "ratio": st.column_config.NumberColumn("Nisbət", format="%.2f×"),
            },
            hide_index=True,
            width="stretch",
        )
        trend = dashboard.weekly
        left, right = st.columns(2)
        left.altair_chart(
            alt.Chart(trend)
            .mark_bar(color=NORMAL_COLOR)
            .encode(x=alt.X("week:T", title="Həftə"), y=alt.Y("count:Q", title="Asteroid sayı"))
            .properties(height=260, title="Həftəlik asteroid sayı"),
            width="stretch",
        )
        right.altair_chart(
            alt.Chart(trend)
            .mark_line(point=True, color=HAZARD_COLOR)
            .encode(x=alt.X("week:T", title="Həftə"), y=alt.Y("hazardous_pct:Q", title="Təhlükəli, %"))
            .properties(height=260, title="Təhlükəli asteroid faizi"),
            width="stretch",
        )
    else:
        st.info(
            "Baza xətti yalnız son 7 gündən hesablanır, bu azdır. "
            "Soldakı **Tarixçə yığ** bölməsi ilə bir neçə həftəlik data yığ."
        )

    st.subheader("Paylanma")
    metric = st.selectbox("Göstərici", list(logic.METRICS), format_func=METRIC_LABELS.get)
    stats = dashboard.baseline[metric]
    histogram = (
        alt.Chart(reference[[metric]])
        .mark_bar(color=NORMAL_COLOR, opacity=0.7)
        .encode(
            x=alt.X(f"{metric}:Q", bin=alt.Bin(maxbins=30), title=METRIC_LABELS[metric]),
            y=alt.Y("count():Q", title="Say"),
        )
    )
    lines = pd.DataFrame(
        [{"value": stats["median"], "label": "Median"}]
        + [
            {"value": stats[key], "label": label}
            for key, label in [("lower_fence", "Aşağı sərhəd"), ("upper_fence", "Yuxarı sərhəd")]
            if stats["min"] <= stats[key] <= stats["max"]
        ]
    )
    rules = (
        alt.Chart(lines)
        .mark_rule(strokeWidth=2, strokeDash=[6, 4])
        .encode(
            x="value:Q",
            color=alt.Color("label:N", title="", scale=alt.Scale(scheme="dark2")),
            tooltip=[alt.Tooltip("label:N", title=""), alt.Tooltip("value:Q", title="Dəyər", format=",.2f")],
        )
    )
    st.altair_chart((histogram + rules).properties(height=300), width="stretch")

    outliers = view[view["is_outlier"]]
    st.subheader(f"Kənar dəyərlər ({len(outliers)})")
    if outliers.empty:
        st.success("Seçilmiş aralıqda baza xəttindən kənar asteroid yoxdur.")
    else:
        reasons = outliers["outlier_reasons"].map(lambda keys: ", ".join(METRIC_LABELS[key] for key in keys))
        st.dataframe(
            outliers.assign(reason=reasons)[
                ["name", "date", "reason", "diameter_m", "velocity_km_s", "distance_ld", "is_hazardous"]
            ],
            column_config={**ASTEROID_COLUMNS, "reason": st.column_config.TextColumn("Səbəb")},
            hide_index=True,
            width="stretch",
        )

with tab_sentry:
    sentry = dashboard.sentry
    if sentry is None:
        st.info("Sentry datası yoxdur. **Datanı yenilə** düyməsini bas və ya `python3 data_loader.py` işə sal.")
    else:
        cols = st.columns(3)
        cols[0].metric("Sentry-də obyekt", f"{len(sentry):,}")
        cols[1].metric("Torino > 0", len(dashboard.torino_positive))
        cols[2].metric("Ən yüksək Palermo", f"{sentry['palermo_cum'].max():.2f}")

        if not dashboard.torino_positive:
            st.success("Torino şkalası üzrə hazırda 0-dan böyük obyekt yoxdur (heç bir real təhlükə yoxdur).")
        else:
            st.warning("Torino şkalası 0-dan böyük olanlar: " + ", ".join(dashboard.torino_positive))

        st.subheader(f"Palermo şkalasına görə top {len(dashboard.sentry_top)}")
        top = dashboard.sentry_top.assign(probability=dashboard.sentry_top["impact_probability"].map(format_probability))
        st.dataframe(
            top[["name", "years", "probability", "palermo_cum", "torino_max", "diameter_m", "n_impacts", "last_obs"]],
            column_config={
                "name": "Ad",
                "years": "Mümkün illər",
                "probability": "Dəymə ehtimalı",
                "palermo_cum": st.column_config.NumberColumn("Palermo", format="%.2f"),
                "torino_max": "Torino",
                "diameter_m": st.column_config.NumberColumn("Diametr, m", format="localized"),
                "n_impacts": "Mümkün dəymə sayı",
                "last_obs": "Son müşahidə",
            },
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Palermo < −2: narahatlıq yoxdur · −2…0: izlənilir · > 0: fon riskindən yüksək. "
            "Torino 0–10: ictimaiyyət üçün risk şkalası, 0 = təhlükə yoxdur. Mənbə: NASA JPL CNEOS Sentry."
        )

        st.subheader("Son 7 gündə keçən və Sentry-də olanlar")
        matched = dashboard.sentry_matches
        if matched.empty and not dashboard.sentry_flagged:
            st.success("Son 7 gündə keçən asteroidlərin heç biri Sentry siyahısında deyil.")
        elif matched.empty:
            st.write(", ".join(dashboard.sentry_flagged))
            st.caption("NeoWs bunları Sentry obyekti kimi işarələyib, amma Sentry siyahısında ad uyğunluğu tapılmadı.")
        else:
            matched = matched.assign(probability=matched["sentry_impact_probability"].map(format_probability))
            st.dataframe(
                matched[["name", "date", "distance_ld", "diameter_m", "probability", "sentry_palermo_cum", "sentry_years"]],
                column_config={
                    **ASTEROID_COLUMNS,
                    "probability": "Dəymə ehtimalı",
                    "sentry_palermo_cum": st.column_config.NumberColumn("Palermo", format="%.2f"),
                    "sentry_years": "Mümkün illər",
                },
                hide_index=True,
                width="stretch",
            )

with tab_future:
    future = dashboard.close_approach
    if future is None:
        st.info("Yaxınlaşma datası yoxdur. **Datanı yenilə** düyməsini bas və ya `python3 data_loader.py` işə sal.")
    elif future.empty:
        st.success("Növbəti 60 gündə 0.05 au daxilində yaxınlaşma yoxdur.")
    else:
        future = future.assign(datetime_utc=pd.to_datetime(future["datetime_utc"]))
        cols = st.columns(3)
        nearest = future.loc[future["distance_ld"].idxmin()]
        cols[0].metric("Keçid sayı (60 gün)", len(future))
        cols[1].metric(
            "Ən yaxın", f"{nearest['distance_ld']:.2f} LD", f"{nearest['designation']} · {nearest['date']}", delta_color="off"
        )
        cols[2].metric("Aydan yaxın (< 1 LD)", int((future["distance_ld"] < 1).sum()))

        timeline = (
            alt.Chart(future)
            .mark_circle(color=NORMAL_COLOR, opacity=0.7)
            .encode(
                x=alt.X("datetime_utc:T", title="Tarix (UTC)"),
                y=alt.Y("distance_ld:Q", title="Yerə məsafə, LD"),
                size=alt.Size("diameter_m:Q", title="Diametr, m", scale=alt.Scale(range=[30, 600])),
                tooltip=[
                    alt.Tooltip("designation:N", title="Ad"),
                    alt.Tooltip("datetime_utc:T", title="Vaxt", format="%Y-%m-%d %H:%M"),
                    alt.Tooltip("distance_ld:Q", title="Məsafə, LD", format=".2f"),
                    alt.Tooltip("diameter_m:Q", title="Diametr, m", format=",.0f"),
                    alt.Tooltip("velocity_km_s:Q", title="Sürət, km/s", format=".2f"),
                ],
            )
        )
        moon = alt.Chart(pd.DataFrame({"y": [1]})).mark_rule(color="gray", strokeDash=[4, 4]).encode(y="y:Q")
        st.altair_chart((timeline + moon).properties(height=380).interactive(), width="stretch")
        st.caption("Boz xətt = Ay məsafəsi (1 LD). Dairənin ölçüsü = diametr.")

        st.dataframe(
            future[["designation", "datetime_utc", "distance_ld", "distance_km", "velocity_km_s", "diameter_m", "diameter_estimated"]],
            column_config={
                "designation": "Ad",
                "datetime_utc": st.column_config.DatetimeColumn("Vaxt (UTC)", format="YYYY-MM-DD HH:mm"),
                "distance_ld": st.column_config.NumberColumn("Məsafə, LD", format="%.2f"),
                "distance_km": st.column_config.NumberColumn("Məsafə, km", format="localized"),
                "velocity_km_s": st.column_config.NumberColumn("Sürət, km/s", format="%.2f"),
                "diameter_m": st.column_config.NumberColumn("Diametr, m", format="%.0f"),
                "diameter_estimated": st.column_config.CheckboxColumn("Diametr təxminidir"),
            },
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Diametri JPL verməyəndə mütləq ulduz ölçüsündən (H) təxmin olunur, albedo 0.14 fərz edilir. "
            "Real diametr 2 dəfəyə qədər fərqli ola bilər. Mənbə: NASA JPL CNEOS Close Approach API."
        )

st.divider()
st.caption("Data: NASA NeoWs (api.nasa.gov) · NASA JPL CNEOS Sentry və Close Approach (ssd-api.jpl.nasa.gov).")
