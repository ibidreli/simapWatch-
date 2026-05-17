import marimo

__generated_with = "0.23.4"
app = marimo.App(width="full", app_title="simapWatch Investigativ Lab")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        "# simapWatch Investigativ Lab\n\n"
        "Interaktives, reaktives Notebook fuer journalistische Beschaffungsanalyse.\n"
        "Passe Filter an und alle Insights, Charts und Tabellen werden automatisch neu berechnet."
    )
    return


@app.cell
def _():
    import altair as alt
    import pandas as pd
    import re
    import sys
    from pathlib import Path

    return Path, alt, pd, re, sys


@app.cell
def _():
    canton_population = {
        "AG": 706_000,
        "AI": 16_500,
        "AR": 55_300,
        "BE": 1_059_000,
        "BL": 296_000,
        "BS": 201_000,
        "FR": 343_600,
        "GE": 517_000,
        "GL": 41_300,
        "GR": 206_000,
        "JU": 74_100,
        "LU": 424_000,
        "NE": 177_000,
        "NW": 43_600,
        "OW": 38_800,
        "SG": 520_000,
        "SH": 84_900,
        "SO": 281_700,
        "SZ": 167_000,
        "TG": 291_000,
        "TI": 354_000,
        "UR": 37_200,
        "VD": 838_000,
        "VS": 357_000,
        "ZG": 132_600,
        "ZH": 1_619_000,
    }
    cpv_division_labels = {
        "45": "Bauarbeiten",
        "71": "Architektur und Ingenieurleistungen",
        "72": "IT und Software",
        "48": "Softwarepakete und Informationssysteme",
        "33": "Medizinische Ausruestung",
        "60": "Transportdienste",
        "80": "Bildung und Training",
        "85": "Gesundheit und Soziales",
        "90": "Reinigung, Abfall, Umwelt",
    }
    month_labels = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "Mai",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Okt",
        11: "Nov",
        12: "Dez",
    }
    swiss_cantons = set(canton_population.keys())
    return canton_population, cpv_division_labels, month_labels, swiss_cantons


@app.cell
def _(Path, sys):
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    default_db_path = src_root / "simapwatch.db"
    return default_db_path, src_root


@app.cell
def _():
    from simapwatch.analysis import load_analysis_dataframe

    return (load_analysis_dataframe,)


@app.cell
def _(default_db_path, mo):
    db_path_input = mo.ui.text(
        value=str(default_db_path),
        label="SQLite DB path",
        full_width=True,
    )
    months_slider = mo.ui.slider(
        start=1,
        stop=60,
        step=1,
        value=18,
        label="Lookback (Monate)",
        show_value=True,
    )
    top_n_slider = mo.ui.slider(
        start=5,
        stop=30,
        step=1,
        value=12,
        label="Top-N fuer Rankings",
        show_value=True,
    )
    chart_scale = mo.ui.slider(
        start=80,
        stop=200,
        step=10,
        value=130,
        label="Chart-Groesse (%)",
        show_value=True,
    )
    table_page_size = mo.ui.slider(
        start=8,
        stop=40,
        step=2,
        value=16,
        label="Zeilen pro Tabelle",
        show_value=True,
    )
    metric_mode = mo.ui.dropdown(
        options={"Volumen CHF": "volume", "Anzahl Zuschlaege": "count"},
        value="Volumen CHF",
        label="Bewertungsmetrik",
    )
    time_grain = mo.ui.dropdown(
        options={"Monat": "M", "Woche": "W"},
        value="Monat",
        label="Zeitgranularitaet",
    )
    min_amount = mo.ui.number(
        start=0,
        step=50_000,
        value=0,
        label="Min Betrag CHF",
    )
    max_amount = mo.ui.number(
        start=0,
        step=50_000,
        value=None,
        label="Max Betrag CHF (optional)",
    )
    buyer_text = mo.ui.text(
        value="",
        placeholder="z.B. Kanton Bern",
        label="Buyer enthaelt",
    )
    winner_text = mo.ui.text(
        value="",
        placeholder="z.B. AG",
        label="Winner enthaelt",
    )
    cpv_prefix_text = mo.ui.text(
        value="",
        placeholder="z.B. 45",
        label="CPV Prefix",
    )
    title_text = mo.ui.text(
        value="",
        placeholder="z.B. Bruecke, Software, Reinigung",
        label="Titel enthaelt",
    )
    single_bid_only = mo.ui.switch(value=False, label="Nur Single-Bid (1 Angebot)")
    inter_canton_only = mo.ui.switch(value=False, label="Nur interkantonale Fluesse")

    return (
        buyer_text,
        chart_scale,
        cpv_prefix_text,
        db_path_input,
        inter_canton_only,
        max_amount,
        metric_mode,
        min_amount,
        months_slider,
        single_bid_only,
        table_page_size,
        time_grain,
        title_text,
        top_n_slider,
        winner_text,
    )


@app.cell
def _(db_path_input, load_analysis_dataframe, pd):
    db_path = db_path_input.value.strip()
    load_error = None
    try:
        df_raw = load_analysis_dataframe(db_path)
    except Exception as exc:
        df_raw = pd.DataFrame()
        load_error = str(exc)
    return db_path, df_raw, load_error


@app.cell
def _(df_raw, re, swiss_cantons):
    procurement_options = sorted(
        str(value).strip()
        for value in df_raw.get("procurement_type", [])
        if str(value).strip()
    )

    def _extract_canton(value):
        tokens = re.findall(r"[A-Z]{2}", str(value or "").upper())
        for token in reversed(tokens):
            if token in swiss_cantons:
                return token
        return None

    canton_set = set()
    if not df_raw.empty:
        for _column in [
            "winner_region",
            "procurement_office_region",
            "winner_address",
            "procurement_office_address",
        ]:
            if _column not in df_raw.columns:
                continue
            for raw_value in df_raw[_column].dropna():
                canton = _extract_canton(raw_value)
                if canton:
                    canton_set.add(canton)

    canton_options = sorted(canton_set)
    return canton_options, procurement_options


@app.cell
def _(canton_options, mo, procurement_options):
    procurement_types = mo.ui.multiselect(
        options=procurement_options,
        value=[],
        label="Beschaffungstypen",
        full_width=True,
    )
    canton_filter = mo.ui.multiselect(
        options=canton_options,
        value=[],
        label="Kantone (Buyer oder Winner)",
        full_width=True,
    )
    return canton_filter, procurement_types


@app.cell(hide_code=True)
def _(
    buyer_text,
    canton_filter,
    chart_scale,
    cpv_prefix_text,
    db_path_input,
    inter_canton_only,
    max_amount,
    metric_mode,
    min_amount,
    mo,
    months_slider,
    procurement_types,
    single_bid_only,
    table_page_size,
    time_grain,
    title_text,
    top_n_slider,
    winner_text,
):
    guide_panel = mo.callout(
        mo.md(
            """
### So liest du das Dashboard

1. **Filter setzen**: Zeitraum, Betrag, Regionen, Buyer/Winner.
2. **Metrik waehlen**: Volumen oder Anzahl.
3. **Story lesen**: In jedem Tab steht zuerst die Einordnung, danach die Charts.
4. **Auffaelligkeiten pruefen**: Risiko-Tab zeigt potenziell kritische Vergaben.
"""
        ),
        kind="info",
    )

    scope_block = mo.vstack(
        [
            mo.md("#### Scope und Darstellung"),
            mo.hstack([months_slider, top_n_slider, metric_mode, time_grain], widths="equal", wrap=True),
            mo.hstack([chart_scale, table_page_size], widths="equal", wrap=True),
        ],
        gap=0.7,
    )
    filter_block = mo.vstack(
        [
            mo.md("#### Inhaltsfilter"),
            mo.hstack([min_amount, max_amount, single_bid_only, inter_canton_only], widths="equal", wrap=True),
            mo.hstack([buyer_text, winner_text, cpv_prefix_text, title_text], widths="equal", wrap=True),
            mo.hstack([procurement_types, canton_filter], widths="equal", wrap=True),
        ],
        gap=0.7,
    )

    controls = mo.vstack(
        [
            guide_panel,
            db_path_input,
            scope_block,
            filter_block,
        ],
        gap=1.0,
    )
    controls
    return


@app.cell
def _(chart_scale, table_page_size):
    chart_scale_factor = float(chart_scale.value or 100) / 100.0
    table_rows_per_page = int(table_page_size.value or 16)
    return chart_scale_factor, table_rows_per_page


@app.cell(hide_code=True)
def _(db_path, load_error, mo):
    if load_error:
        status_panel = mo.callout(
            mo.md(f"**Fehler beim Laden** von `{db_path}`:\n\n`{load_error}`"),
            kind="danger",
        )
    else:
        status_panel = mo.callout(
            mo.md(f"Daten geladen aus `{db_path}`"),
            kind="success",
        )
    status_panel
    return


@app.cell
def _(cpv_division_labels, df_raw, pd, re, swiss_cantons):
    df = df_raw.copy()
    if df.empty:
        for _column, dtype in [
            ("publication_dt", "datetime64[ns]"),
            ("award_amount_chf", "float64"),
            ("offers_count", "int64"),
            ("buyer_canton", "object"),
            ("winner_canton", "object"),
            ("is_inter_canton", "bool"),
            ("cpv_division", "object"),
            ("cpv_label", "object"),
            ("month_key", "object"),
            ("week_key", "object"),
            ("month_num", "float64"),
            ("offers_bucket", "object"),
        ]:
            df[_column] = pd.Series(dtype=dtype)
    else:
        def _extract_canton_df(value):
            tokens = re.findall(r"[A-Z]{2}", str(value or "").upper())
            for token in reversed(tokens):
                if token in swiss_cantons:
                    return token
            return "unknown"

        date_source = df["publication_date"].fillna(df["overview_publication_date"])
        df["publication_dt"] = pd.to_datetime(date_source, format="%d.%m.%Y", errors="coerce")
        df["award_amount_chf"] = pd.to_numeric(df["award_amount_chf"], errors="coerce").fillna(0.0)
        df["offers_count"] = pd.to_numeric(df["offers_count"], errors="coerce").fillna(0).astype(int)
        df["winner_name"] = df["winner_name"].fillna("").astype(str).str.strip()
        df["procurement_office"] = df["procurement_office"].fillna("").astype(str).str.strip()
        df["title"] = df["title"].fillna("").astype(str)
        df["procurement_type"] = df["procurement_type"].fillna("unbekannt").astype(str)

        df["cpv_primary"] = (
            df["cpv_primary"]
            .fillna("")
            .astype(str)
            .str.replace(r"[^0-9]", "", regex=True)
            .str.slice(0, 8)
        )
        df["cpv_division"] = df["cpv_primary"].str.slice(0, 2)
        df["cpv_label"] = df["cpv_division"].map(cpv_division_labels).fillna("Andere")

        winner_region = df.get("winner_region", pd.Series(index=df.index, dtype=object)).fillna("")
        winner_address = df.get("winner_address", pd.Series(index=df.index, dtype=object)).fillna("")
        buyer_region = df.get("procurement_office_region", pd.Series(index=df.index, dtype=object)).fillna("")
        buyer_address = df.get("procurement_office_address", pd.Series(index=df.index, dtype=object)).fillna("")

        df["winner_canton"] = [_extract_canton_df(a if str(a).strip() else b) for a, b in zip(winner_region, winner_address)]
        df["buyer_canton"] = [_extract_canton_df(a if str(a).strip() else b) for a, b in zip(buyer_region, buyer_address)]
        df["is_inter_canton"] = (
            (df["winner_canton"] != "unknown")
            & (df["buyer_canton"] != "unknown")
            & (df["winner_canton"] != df["buyer_canton"])
        )

        df["month_key"] = df["publication_dt"].dt.to_period("M").astype(str)
        df["week_key"] = df["publication_dt"].dt.strftime("%G-W%V")
        df["month_num"] = df["publication_dt"].dt.month

        df["offers_bucket"] = "unbekannt"
        df.loc[df["offers_count"] == 1, "offers_bucket"] = "1"
        df.loc[df["offers_count"] == 2, "offers_bucket"] = "2"
        df.loc[(df["offers_count"] >= 3) & (df["offers_count"] <= 5), "offers_bucket"] = "3-5"
        df.loc[(df["offers_count"] >= 6) & (df["offers_count"] <= 10), "offers_bucket"] = "6-10"
        df.loc[df["offers_count"] >= 11, "offers_bucket"] = "11+"

    return (df,)


@app.cell
def _(
    buyer_text,
    canton_filter,
    cpv_prefix_text,
    df,
    inter_canton_only,
    max_amount,
    metric_mode,
    min_amount,
    months_slider,
    pd,
    procurement_types,
    single_bid_only,
    time_grain,
    title_text,
    winner_text,
):
    filtered = df.copy()

    if not filtered.empty:
        latest_date = filtered["publication_dt"].max()
        if pd.notna(latest_date):
            cutoff = latest_date - pd.DateOffset(months=int(months_slider.value or 12))
            filtered = filtered[filtered["publication_dt"].notna() & (filtered["publication_dt"] >= cutoff)]

    buyer_query = buyer_text.value.strip().casefold()
    if buyer_query:
        filtered = filtered[filtered["procurement_office"].str.casefold().str.contains(buyer_query, regex=False)]

    winner_query = winner_text.value.strip().casefold()
    if winner_query:
        filtered = filtered[filtered["winner_name"].str.casefold().str.contains(winner_query, regex=False)]

    cpv_prefix = cpv_prefix_text.value.strip()
    if cpv_prefix:
        filtered = filtered[filtered["cpv_primary"].str.startswith(cpv_prefix)]

    title_query = title_text.value.strip().casefold()
    if title_query:
        filtered = filtered[filtered["title"].str.casefold().str.contains(title_query, regex=False)]

    min_value = min_amount.value
    if min_value is not None and float(min_value) > 0:
        filtered = filtered[filtered["award_amount_chf"] >= float(min_value)]

    max_value = max_amount.value
    if max_value is not None and float(max_value) > 0:
        filtered = filtered[filtered["award_amount_chf"] <= float(max_value)]

    selected_proc_types = set(procurement_types.value or [])
    if selected_proc_types:
        filtered = filtered[filtered["procurement_type"].isin(selected_proc_types)]

    selected_cantons = set(canton_filter.value or [])
    if selected_cantons:
        filtered = filtered[
            filtered["buyer_canton"].isin(selected_cantons) | filtered["winner_canton"].isin(selected_cantons)
        ]

    if single_bid_only.value:
        filtered = filtered[(filtered["offers_count"] > 0) & (filtered["offers_count"] <= 1)]

    if inter_canton_only.value:
        filtered = filtered[filtered["is_inter_canton"]]

    metric_mode_value = metric_mode.value or "volume"
    time_grain_value = time_grain.value or "M"
    return filtered, metric_mode_value, time_grain_value


@app.cell
def _(filtered, mo, pd, table_rows_per_page):
    row_count = int(len(filtered))
    summary_total_volume = float(filtered["award_amount_chf"].sum()) if row_count else 0.0
    median_amount = float(filtered["award_amount_chf"].median()) if row_count else 0.0
    winner_count = int(filtered["winner_name"].replace("", pd.NA).dropna().nunique()) if row_count else 0
    buyer_count = int(filtered["procurement_office"].replace("", pd.NA).dropna().nunique()) if row_count else 0

    if row_count and summary_total_volume > 0:
        winner_volume = (
            filtered[filtered["winner_name"] != ""]
            .groupby("winner_name", as_index=False)
            .agg(volume_chf=("award_amount_chf", "sum"))
            .sort_values("volume_chf", ascending=False)
        )
        top10_share = float((winner_volume["volume_chf"].head(10).sum() / summary_total_volume) * 100.0)
        top1_name = str(winner_volume.iloc[0]["winner_name"]) if not winner_volume.empty else "-"
        top1_share = (
            float((winner_volume["volume_chf"].iloc[0] / summary_total_volume) * 100.0) if not winner_volume.empty else 0.0
        )
    else:
        top10_share = 0.0
        top1_name = "-"
        top1_share = 0.0

    known_offers = filtered[filtered["offers_count"] > 0]
    single_bid_share = (
        float((known_offers["offers_count"] <= 1).mean() * 100.0) if not known_offers.empty else 0.0
    )

    known_cantons = filtered[
        (filtered["buyer_canton"] != "unknown")
        & (filtered["winner_canton"] != "unknown")
    ]
    inter_share = float((known_cantons["is_inter_canton"].mean() * 100.0)) if not known_cantons.empty else 0.0

    q4_volume_share = 0.0
    if row_count and summary_total_volume > 0:
        q4_volume = float(filtered[filtered["month_num"].isin([10, 11, 12])]["award_amount_chf"].sum())
        q4_volume_share = (q4_volume / summary_total_volume) * 100.0

    kpi_df = pd.DataFrame(
        [
            {"KPI": "Zuschlaege", "Wert": f"{row_count:,}".replace(",", "'")},
            {"KPI": "Volumen CHF", "Wert": f"{summary_total_volume:,.0f}".replace(",", "'")},
            {"KPI": "Median CHF", "Wert": f"{median_amount:,.0f}".replace(",", "'")},
            {"KPI": "Gewinner", "Wert": f"{winner_count:,}".replace(",", "'")},
            {"KPI": "Buyer", "Wert": f"{buyer_count:,}".replace(",", "'")},
            {"KPI": "Top-10 Gewinner Anteil", "Wert": f"{top10_share:.2f}%"},
            {"KPI": "Single-Bid Anteil", "Wert": f"{single_bid_share:.2f}%"},
            {"KPI": "Interkantonaler Anteil", "Wert": f"{inter_share:.2f}%"},
            {"KPI": "Q4 Budgetanteil", "Wert": f"{q4_volume_share:.2f}%"},
        ]
    )
    kpi_table = mo.ui.table(kpi_df, pagination=False, selection=None, show_download=False, label="KPI Snapshot")

    story_panel = mo.callout(
        mo.md(
            f"""
### Journalistische Kernaussagen

- **Konzentration:** Top-10 Gewinner kontrollieren **{top10_share:.2f}%** des Volumens.
- **Dominanter Akteur:** Top-1 Gewinner (**{top1_name}**) haelt **{top1_share:.2f}%**.
- **Wettbewerb:** Single-Bid Anteil liegt bei **{single_bid_share:.2f}%**.
- **Regionaler Bias:** Interkantonale Fluesse liegen bei **{inter_share:.2f}%**.
- **Timing:** **{q4_volume_share:.2f}%** des Volumens faellt ins Q4.
"""
        ),
        kind="info",
    )
    return kpi_table, story_panel


@app.cell(hide_code=True)
def _(kpi_table, mo, story_panel):
    overview_intro = mo.callout(
        mo.md(
            """
Diese Uebersicht liefert die wichtigsten Signale auf einen Blick.
Nutze danach die Spezial-Tabs, um jede Hypothese mit Details zu pruefen.
"""
        ),
        kind="neutral",
    )
    overview_panel = mo.vstack([overview_intro, story_panel, kpi_table], gap=1.0)
    overview_panel
    return (overview_panel,)


@app.cell
def _(alt, chart_scale_factor, filtered, metric_mode_value, month_labels, mo, pd, time_grain_value, top_n_slider):
    if filtered.empty:
        trend_panel = mo.callout("Keine Daten im aktuellen Filter fuer Trend/CPV.", kind="warn")
    else:
        trend_height_main = int(340 * chart_scale_factor)
        trend_height_mid = int(250 * chart_scale_factor)
        trend_height_side = int(250 * chart_scale_factor)
        trend_explainer = mo.callout(
            mo.md(
                """
**Was zeigt dieser Block?**

- **Trend**: Volumen und Zuschlagsanzahl pro Periode.
- **Kosten pro Zuschlag**: zeigt, ob Peaks durch mehr Faelle oder teurere Einzelfaelle entstehen.
- **CPV Deep Dive**: welche Beschaffungscluster den Zeitraum dominieren.
- **Budget Rush**: wie stark Ausgaben auf Jahresende konzentriert sind.
"""
            ),
            kind="neutral",
        )

        trend_period_col = "month_key" if time_grain_value == "M" else "week_key"
        trend_period_title = "Monat" if time_grain_value == "M" else "Woche"

        trend_df = (
            filtered.groupby(trend_period_col, as_index=False)
            .agg(volume_chf=("award_amount_chf", "sum"), awards=("award_row_id", "count"))
            .rename(columns={trend_period_col: "period"})
            .sort_values("period")
        )
        trend_df["avg_ticket"] = trend_df["volume_chf"] / trend_df["awards"].where(trend_df["awards"] > 0, 1)

        trend_chart = alt.layer(
            alt.Chart(trend_df).mark_bar(color="#4e79a7").encode(
                x=alt.X("period:N", title=trend_period_title),
                y=alt.Y("volume_chf:Q", title="Volumen CHF"),
                tooltip=["period:N", "awards:Q", "volume_chf:Q", "avg_ticket:Q"],
            ),
            alt.Chart(trend_df).mark_line(color="#f28e2b", point=True).encode(
                x="period:N",
                y=alt.Y("awards:Q", title="Anzahl Zuschlaege"),
            ),
        ).resolve_scale(y="independent").properties(height=trend_height_main, title="Trend: Volumen und Anzahl")

        avg_ticket_chart = (
            alt.Chart(trend_df)
            .mark_line(point=True, color="#2ca02c")
            .encode(
                x=alt.X("period:N", title=trend_period_title),
                y=alt.Y("avg_ticket:Q", title="Durchschnittlicher Zuschlag CHF"),
                tooltip=["period:N", "avg_ticket:Q"],
            )
            .properties(height=trend_height_mid, title="Kosten pro Zuschlag")
        )

        trend_top_n = int(top_n_slider.value or 12)
        cpv_df = (
            filtered.groupby(["cpv_label", "cpv_division"], as_index=False)
            .agg(volume_chf=("award_amount_chf", "sum"), awards=("award_row_id", "count"))
        )
        cpv_df["metric_value"] = cpv_df["volume_chf"] if metric_mode_value == "volume" else cpv_df["awards"]
        cpv_df = cpv_df.sort_values("metric_value", ascending=False).head(trend_top_n)

        cpv_chart = (
            alt.Chart(cpv_df)
            .mark_bar()
            .encode(
                x=alt.X(
                    "metric_value:Q",
                    title="Volumen CHF" if metric_mode_value == "volume" else "Anzahl Zuschlaege",
                ),
                y=alt.Y("cpv_label:N", sort="-x", title="CPV Cluster"),
                tooltip=["cpv_label:N", "cpv_division:N", "awards:Q", "volume_chf:Q"],
                color=alt.Color("cpv_label:N", legend=None),
            )
            .properties(height=trend_height_main, title="CPV Deep Dive")
        )

        budget_rush = (
            filtered.groupby("month_num", as_index=False)
            .agg(volume_chf=("award_amount_chf", "sum"), awards=("award_row_id", "count"))
            .dropna(subset=["month_num"])
        )
        budget_rush["month_num"] = budget_rush["month_num"].astype(int)
        total_budget = float(budget_rush["volume_chf"].sum()) if not budget_rush.empty else 0.0
        budget_rush["share_pct"] = (
            (budget_rush["volume_chf"] / total_budget) * 100.0 if total_budget > 0 else 0.0
        )
        budget_rush["month_name"] = budget_rush["month_num"].map(month_labels)
        budget_rush = budget_rush.sort_values("month_num")

        budget_chart = (
            alt.Chart(budget_rush)
            .mark_bar(color="#9c755f")
            .encode(
                x=alt.X("month_name:N", title="Monat"),
                y=alt.Y("share_pct:Q", title="Anteil am Volumen (%)"),
                tooltip=["month_name:N", "share_pct:Q", "volume_chf:Q", "awards:Q"],
            )
            .properties(height=trend_height_side, title="Budget Rush: Monatsanteile am Gesamtvolumen")
        )

        trend_panel = mo.vstack(
            [
                trend_explainer,
                mo.ui.altair_chart(trend_chart, chart_selection=False, label="Trend"),
                mo.ui.altair_chart(avg_ticket_chart, chart_selection=False, label="Kosten pro Zuschlag"),
                mo.hstack(
                    [
                        mo.ui.altair_chart(cpv_chart, chart_selection=False, label="CPV"),
                        mo.ui.altair_chart(budget_chart, chart_selection=False, label="Budget Rush"),
                    ],
                    widths="equal",
                    wrap=True,
                    gap=1.0,
                ),
            ],
            gap=1.0,
        )
    return (trend_panel,)


@app.cell
def _(alt, chart_scale_factor, filtered, mo, pd, top_n_slider):
    if filtered.empty:
        concentration_panel = mo.callout("Keine Daten fuer Konzentrationsanalyse.", kind="warn")
    else:
        conc_height_main = int(320 * chart_scale_factor)
        conc_height_side = int(260 * chart_scale_factor)
        conc_explainer = mo.callout(
            mo.md(
                """
**Was zeigt dieser Block?**

- **Pareto**: ob wenige Winner den Markt dominieren.
- **Top-10 vs Rest**: schnelle Machtverteilung.
- **Lorenz + Gini**: standardisierte Konzentrationsmessung fuer Vergleich ueber Zeit.
"""
            ),
            kind="neutral",
        )

        winner_df = (
            filtered[filtered["winner_name"] != ""]
            .groupby("winner_name", as_index=False)
            .agg(volume_chf=("award_amount_chf", "sum"), awards=("award_row_id", "count"))
            .sort_values("volume_chf", ascending=False)
        )
        if winner_df.empty:
            concentration_panel = mo.callout("Keine Gewinnerdaten verfuegbar.", kind="warn")
        else:
            conc_total_volume = float(winner_df["volume_chf"].sum())
            conc_top_n = int(top_n_slider.value or 12)
            pareto_df = winner_df.head(conc_top_n).copy()
            pareto_df["rank"] = range(1, len(pareto_df) + 1)
            pareto_df["cum_share_pct"] = (
                (pareto_df["volume_chf"].cumsum() / conc_total_volume) * 100.0 if conc_total_volume > 0 else 0.0
            )

            pareto_chart = alt.layer(
                alt.Chart(pareto_df).mark_bar(color="#1f77b4").encode(
                    x=alt.X("winner_name:N", sort=None, title="Gewinner"),
                    y=alt.Y("volume_chf:Q", title="Volumen CHF"),
                    tooltip=["winner_name:N", "volume_chf:Q", "awards:Q", "cum_share_pct:Q"],
                ),
                alt.Chart(pareto_df).mark_line(color="#d62728", point=True).encode(
                    x="winner_name:N",
                    y=alt.Y("cum_share_pct:Q", title="Kumulierte Volumenanteile (%)"),
                ),
            ).resolve_scale(y="independent").properties(height=conc_height_main, title="Pareto: Winner Konzentration")

            conc_top10_volume = float(winner_df["volume_chf"].head(10).sum())
            top10_vs_rest = pd.DataFrame(
                [
                    {"segment": "Top 10", "volume_chf": conc_top10_volume},
                    {"segment": "Rest", "volume_chf": max(conc_total_volume - conc_top10_volume, 0.0)},
                ]
            )
            top10_vs_rest["share_pct"] = (
                (top10_vs_rest["volume_chf"] / conc_total_volume) * 100.0 if conc_total_volume > 0 else 0.0
            )
            top10_chart = (
                alt.Chart(top10_vs_rest)
                .mark_bar()
                .encode(
                    x=alt.X("segment:N", title="Segment"),
                    y=alt.Y("volume_chf:Q", title="Volumen CHF"),
                    color=alt.Color("segment:N", legend=None),
                    tooltip=["segment:N", "volume_chf:Q", "share_pct:Q"],
                )
                .properties(height=conc_height_side, title="Top-10 vs Rest")
            )

            ascending = winner_df["volume_chf"].sort_values().tolist()
            lorenz_points = [{"winner_share_pct": 0.0, "volume_share_pct": 0.0}]
            cumulative = 0.0
            for idx, amount in enumerate(ascending, start=1):
                cumulative += float(amount)
                lorenz_points.append(
                    {
                        "winner_share_pct": (idx / len(ascending)) * 100.0,
                        "volume_share_pct": (cumulative / conc_total_volume) * 100.0 if conc_total_volume > 0 else 0.0,
                    }
                )
            lorenz_df = pd.DataFrame(lorenz_points)
            equality_df = pd.DataFrame(
                [
                    {"winner_share_pct": 0.0, "volume_share_pct": 0.0},
                    {"winner_share_pct": 100.0, "volume_share_pct": 100.0},
                ]
            )

            weighted_sum = sum((index + 1) * value for index, value in enumerate(ascending))
            gini = 0.0
            if ascending and conc_total_volume > 0:
                n = len(ascending)
                gini = (2.0 * weighted_sum) / (n * conc_total_volume) - ((n + 1) / n)

            lorenz_chart = alt.layer(
                alt.Chart(equality_df).mark_line(strokeDash=[6, 4], color="#777777").encode(
                    x=alt.X("winner_share_pct:Q", title="Anteil Gewinner (%)"),
                    y=alt.Y("volume_share_pct:Q", title="Anteil Volumen (%)"),
                ),
                alt.Chart(lorenz_df).mark_line(color="#ff7f0e", point=True).encode(
                    x=alt.X("winner_share_pct:Q", title="Anteil Gewinner (%)"),
                    y=alt.Y("volume_share_pct:Q", title="Anteil Volumen (%)"),
                    tooltip=["winner_share_pct:Q", "volume_share_pct:Q"],
                ),
            ).properties(height=conc_height_main, title="Lorenz Kurve")

            concentration_panel = mo.vstack(
                [
                    conc_explainer,
                    mo.callout(
                        mo.md(f"**Gini Koeffizient (Winner Volumen): {gini:.3f}**"),
                        kind="info",
                    ),
                    mo.hstack(
                        [
                            mo.ui.altair_chart(pareto_chart, chart_selection=False, label="Pareto"),
                            mo.ui.altair_chart(top10_chart, chart_selection=False, label="Top10 vs Rest"),
                        ],
                        widths="equal",
                        wrap=True,
                        gap=1.0,
                    ),
                    mo.ui.altair_chart(lorenz_chart, chart_selection=False, label="Lorenz"),
                ],
                gap=1.0,
            )
    return (concentration_panel,)


@app.cell
def _(alt, chart_scale_factor, filtered, metric_mode_value, mo, table_rows_per_page, top_n_slider):
    if filtered.empty:
        dependency_panel = mo.callout("Keine Daten fuer Buyer-Winner-Abhaengigkeiten.", kind="warn")
    else:
        dep_heatmap_height = int(460 * chart_scale_factor)
        dep_explainer = mo.callout(
            mo.md(
                """
**Was zeigt dieser Block?**

- Matrix der wichtigsten Buyer/Winner-Kombinationen.
- Je dunkler das Feld, desto hoeher Volumen bzw. Anzahl.
- Die Tabelle darunter zeigt konkrete Paare als Recherche-Startpunkt.
"""
            ),
            kind="neutral",
        )

        non_empty = filtered[(filtered["procurement_office"] != "") & (filtered["winner_name"] != "")]
        if non_empty.empty:
            dependency_panel = mo.callout("Keine verwertbaren Buyer/Winner Namen vorhanden.", kind="warn")
        else:
            dep_top_n = int(top_n_slider.value or 12)
            top_buyers = (
                non_empty.groupby("procurement_office", as_index=False)
                .agg(volume_chf=("award_amount_chf", "sum"))
                .sort_values("volume_chf", ascending=False)
                .head(dep_top_n)["procurement_office"]
                .tolist()
            )
            top_winners = (
                non_empty.groupby("winner_name", as_index=False)
                .agg(volume_chf=("award_amount_chf", "sum"))
                .sort_values("volume_chf", ascending=False)
                .head(dep_top_n)["winner_name"]
                .tolist()
            )

            pair_df = (
                non_empty.groupby(["procurement_office", "winner_name"], as_index=False)
                .agg(award_count=("award_row_id", "count"), volume_chf=("award_amount_chf", "sum"))
            )
            pair_df = pair_df[
                pair_df["procurement_office"].isin(top_buyers) & pair_df["winner_name"].isin(top_winners)
            ].copy()
            if pair_df.empty:
                dependency_panel = mo.callout("Top-Paare leer im aktuellen Filter.", kind="warn")
            else:
                dep_value_field = "volume_chf" if metric_mode_value == "volume" else "award_count"
                dep_value_title = "Volumen CHF" if metric_mode_value == "volume" else "Anzahl Zuschlaege"

                heatmap = (
                    alt.Chart(pair_df)
                    .mark_rect()
                    .encode(
                        x=alt.X("winner_name:N", title="Winner", sort=top_winners),
                        y=alt.Y("procurement_office:N", title="Buyer", sort=top_buyers),
                        color=alt.Color(f"{dep_value_field}:Q", title=dep_value_title),
                        tooltip=["procurement_office:N", "winner_name:N", "award_count:Q", "volume_chf:Q"],
                    )
                    .properties(height=dep_heatmap_height, title="Abhaengigkeit Buyer -> Winner (Heatmap)")
                )

                top_pairs_table = pair_df.sort_values(["award_count", "volume_chf"], ascending=[False, False]).head(25)
                table_widget = mo.ui.table(
                    top_pairs_table,
                    page_size=table_rows_per_page,
                    selection=None,
                    label="Top Buyer-Winner Paare",
                )

                dependency_panel = mo.vstack(
                    [
                        dep_explainer,
                        mo.ui.altair_chart(heatmap, chart_selection=False, label="Buyer-Winner Heatmap"),
                        table_widget,
                    ],
                    gap=1.0,
                )
    return (dependency_panel,)


@app.cell
def _(alt, chart_scale_factor, filtered, mo, top_n_slider):
    if filtered.empty:
        competition_panel = mo.callout("Keine Daten fuer Wettbewerbsanalyse.", kind="warn")
    else:
        comp_height_main = int(390 * chart_scale_factor)
        comp_height_side = int(270 * chart_scale_factor)
        comp_height_bar = int(360 * chart_scale_factor)
        comp_explainer = mo.callout(
            mo.md(
                """
**Was zeigt dieser Block?**

- **Scatter + Trendlinie**: Zusammenhang Angebote vs. Zuschlagshoehe.
- **Bucket-Chart**: mediane Preise je Wettbewerbsintensitaet.
- **Single-Bid je Typ**: strukturelles Wettbewerbsrisiko pro Verfahrenstyp.
"""
            ),
            kind="neutral",
        )

        scatter_df = filtered[(filtered["offers_count"] > 0) & (filtered["award_amount_chf"] > 0)].copy()
        if scatter_df.empty:
            competition_panel = mo.callout("Keine Angebote/Betraege fuer Scatter verfuegbar.", kind="warn")
        else:
            top_types = (
                scatter_df.groupby("procurement_type", as_index=False)
                .agg(count=("award_row_id", "count"))
                .sort_values("count", ascending=False)
                .head(8)["procurement_type"]
                .tolist()
            )
            scatter_df["type_group"] = scatter_df["procurement_type"].where(
                scatter_df["procurement_type"].isin(top_types),
                other="Other",
            )

            scatter_chart = alt.layer(
                alt.Chart(scatter_df)
                .mark_circle(size=70, opacity=0.45)
                .encode(
                    x=alt.X("offers_count:Q", title="Anzahl Angebote"),
                    y=alt.Y("award_amount_chf:Q", title="Zuschlag CHF", scale=alt.Scale(type="log")),
                    color=alt.Color("type_group:N", title="Beschaffungstyp"),
                    tooltip=["publication_number:N", "title:N", "offers_count:Q", "award_amount_chf:Q", "type_group:N"],
                ),
                alt.Chart(scatter_df)
                .transform_regression("offers_count", "award_amount_chf")
                .mark_line(color="#111111", strokeWidth=2)
                .encode(x="offers_count:Q", y=alt.Y("award_amount_chf:Q", scale=alt.Scale(type="log"))),
            ).properties(height=comp_height_main, title="Wettbewerb vs Preis (log-scale)")

            offer_bucket_df = (
                scatter_df.groupby("offers_bucket", as_index=False)
                .agg(
                    award_count=("award_row_id", "count"),
                    median_chf=("award_amount_chf", "median"),
                    avg_chf=("award_amount_chf", "mean"),
                )
                .sort_values("offers_bucket")
            )
            bucket_chart = (
                alt.Chart(offer_bucket_df)
                .mark_bar(color="#59a14f")
                .encode(
                    x=alt.X("offers_bucket:N", title="Angebots-Bucket"),
                    y=alt.Y("median_chf:Q", title="Median Zuschlag CHF"),
                    tooltip=["offers_bucket:N", "award_count:Q", "median_chf:Q", "avg_chf:Q"],
                )
                .properties(height=comp_height_side, title="Medianpreis nach Angebotsintensitaet")
            )

            comp_top_n = int(top_n_slider.value or 12)
            proc_comp = (
                scatter_df.groupby("procurement_type", as_index=False)
                .agg(
                    award_count=("award_row_id", "count"),
                    single_bid_count=("offers_count", lambda s: int((s <= 1).sum())),
                    volume_chf=("award_amount_chf", "sum"),
                )
                .sort_values("award_count", ascending=False)
                .head(comp_top_n)
            )
            proc_comp["single_bid_share_pct"] = (
                proc_comp["single_bid_count"] / proc_comp["award_count"].where(proc_comp["award_count"] > 0, 1)
            ) * 100.0
            single_bid_chart = (
                alt.Chart(proc_comp)
                .mark_bar(color="#e15759")
                .encode(
                    x=alt.X("single_bid_share_pct:Q", title="Single-Bid Anteil (%)"),
                    y=alt.Y("procurement_type:N", sort="-x", title="Beschaffungstyp"),
                    tooltip=["procurement_type:N", "award_count:Q", "single_bid_count:Q", "single_bid_share_pct:Q"],
                )
                .properties(height=comp_height_bar, title="Wettbewerbsrisiko je Beschaffungstyp")
            )

            competition_panel = mo.vstack(
                [
                    comp_explainer,
                    mo.ui.altair_chart(scatter_chart, chart_selection=False, label="Scatter"),
                    mo.hstack(
                        [
                            mo.ui.altair_chart(bucket_chart, chart_selection=False, label="Preis nach Offers"),
                            mo.ui.altair_chart(single_bid_chart, chart_selection=False, label="Single-Bid je Typ"),
                        ],
                        widths="equal",
                        wrap=True,
                        gap=1.0,
                    ),
                ],
                gap=1.0,
            )
    return (competition_panel,)


@app.cell
def _(alt, canton_population, chart_scale_factor, filtered, metric_mode_value, mo, pd, time_grain_value, top_n_slider):
    if filtered.empty:
        region_panel = mo.callout("Keine Daten fuer Regionalanalyse.", kind="warn")
    else:
        region_height_heatmap = int(420 * chart_scale_factor)
        region_height_side = int(320 * chart_scale_factor)
        region_height_line = int(260 * chart_scale_factor)
        region_explainer = mo.callout(
            mo.md(
                """
**Was zeigt dieser Block?**

- **Bias-Matrix**: welche Kantone systematisch miteinander vergeben.
- **Heimvorteil**: Anteil lokaler Gewinner je Buyer-Kanton.
- **Normalisierung pro 100k**: fairer Vergleich kleiner/grosser Kantone.
- **Zeittrend**: Veraenderung interkantonaler Fluesse ueber die Zeit.
"""
            ),
            kind="neutral",
        )

        known = filtered[
            (filtered["buyer_canton"] != "unknown")
            & (filtered["winner_canton"] != "unknown")
        ].copy()
        if known.empty:
            region_panel = mo.callout("Keine Kantoninformationen verfuegbar.", kind="warn")
        else:
            flow_df = (
                known.groupby(["buyer_canton", "winner_canton"], as_index=False)
                .agg(award_count=("award_row_id", "count"), volume_chf=("award_amount_chf", "sum"))
            )
            region_value_field = "volume_chf" if metric_mode_value == "volume" else "award_count"
            region_value_title = "Volumen CHF" if metric_mode_value == "volume" else "Anzahl Zuschlaege"
            region_heatmap = (
                alt.Chart(flow_df)
                .mark_rect()
                .encode(
                    x=alt.X("winner_canton:N", title="Winner Kanton"),
                    y=alt.Y("buyer_canton:N", title="Buyer Kanton"),
                    color=alt.Color(f"{region_value_field}:Q", title=region_value_title),
                    tooltip=["buyer_canton:N", "winner_canton:N", "award_count:Q", "volume_chf:Q"],
                )
                .properties(height=region_height_heatmap, title="Regionaler Bias Matrix")
            )

            buyer_local = (
                known.groupby("buyer_canton", as_index=False)
                .agg(
                    known_awards=("award_row_id", "count"),
                    local_awards=("is_inter_canton", lambda s: int((~s).sum())),
                )
            )
            buyer_local["local_share_pct"] = (
                buyer_local["local_awards"] / buyer_local["known_awards"].where(buyer_local["known_awards"] > 0, 1)
            ) * 100.0
            region_top_n = int(top_n_slider.value or 12)
            buyer_local = buyer_local.sort_values("local_share_pct", ascending=False).head(region_top_n)
            local_share_chart = (
                alt.Chart(buyer_local)
                .mark_bar(color="#b07aa1")
                .encode(
                    x=alt.X("local_share_pct:Q", title="Lokaler Winner Anteil (%)"),
                    y=alt.Y("buyer_canton:N", sort="-x", title="Buyer Kanton"),
                    tooltip=["buyer_canton:N", "known_awards:Q", "local_awards:Q", "local_share_pct:Q"],
                )
                .properties(height=region_height_side, title="Heimvorteil je Buyer-Kanton")
            )

            winner_canton = (
                known.groupby("winner_canton", as_index=False)
                .agg(award_count=("award_row_id", "count"), volume_chf=("award_amount_chf", "sum"))
            )
            winner_canton["population"] = winner_canton["winner_canton"].map(canton_population)
            winner_canton = winner_canton[winner_canton["population"].notna() & (winner_canton["population"] > 0)].copy()
            winner_canton["awards_per_100k"] = (winner_canton["award_count"] / winner_canton["population"]) * 100_000.0
            per100k_chart = (
                alt.Chart(winner_canton.sort_values("awards_per_100k", ascending=False).head(region_top_n))
                .mark_bar(color="#76b7b2")
                .encode(
                    x=alt.X("awards_per_100k:Q", title="Zuschlaege pro 100k Einwohner"),
                    y=alt.Y("winner_canton:N", sort="-x", title="Winner Kanton"),
                    tooltip=["winner_canton:N", "award_count:Q", "population:Q", "awards_per_100k:Q"],
                )
                .properties(height=region_height_side, title="Winner-Kanton normalisiert pro 100k")
            )

            region_period_col = "month_key" if time_grain_value == "M" else "week_key"
            inter_trend = (
                known.groupby(region_period_col, as_index=False)
                .agg(
                    known_awards=("award_row_id", "count"),
                    inter_awards=("is_inter_canton", "sum"),
                )
                .rename(columns={region_period_col: "period"})
                .sort_values("period")
            )
            inter_trend["inter_share_pct"] = (
                inter_trend["inter_awards"] / inter_trend["known_awards"].where(inter_trend["known_awards"] > 0, 1)
            ) * 100.0
            inter_trend_chart = (
                alt.Chart(inter_trend)
                .mark_line(point=True, color="#f28e2b")
                .encode(
                    x=alt.X("period:N", title="Periode"),
                    y=alt.Y("inter_share_pct:Q", title="Interkantonaler Anteil (%)"),
                    tooltip=["period:N", "known_awards:Q", "inter_awards:Q", "inter_share_pct:Q"],
                )
                .properties(height=region_height_line, title="Interkantonalitaet im Zeitverlauf")
            )

            region_panel = mo.vstack(
                [
                    region_explainer,
                    mo.ui.altair_chart(region_heatmap, chart_selection=False, label="Regional Heatmap"),
                    mo.hstack(
                        [
                            mo.ui.altair_chart(local_share_chart, chart_selection=False, label="Heimvorteil"),
                            mo.ui.altair_chart(per100k_chart, chart_selection=False, label="Pro 100k"),
                        ],
                        widths="equal",
                        wrap=True,
                        gap=1.0,
                    ),
                    mo.ui.altair_chart(inter_trend_chart, chart_selection=False, label="Interkantonaler Trend"),
                ],
                gap=1.0,
            )
    return (region_panel,)


@app.cell
def _(alt, chart_scale_factor, filtered, mo, pd, table_rows_per_page):
    if filtered.empty:
        risk_panel = mo.callout("Keine Daten fuer Risikoanalyse.", kind="warn")
    else:
        risk_hist_height = int(260 * chart_scale_factor)
        risk_explainer = mo.callout(
            mo.md(
                """
**Was zeigt dieser Block?**

Der Score ist eine **Heuristik** fuer Recherche-Priorisierung, kein Beweis:
- wenig Angebote,
- sehr hoher Betrag,
- wiederholtes Buyer/Winner-Paar,
- ggf. freihändiger Charakter.
"""
            ),
            kind="neutral",
        )

        risk_df = filtered.copy()
        risk_df = risk_df[risk_df["award_amount_chf"] > 0].copy()
        if risk_df.empty:
            risk_panel = mo.callout("Keine positiven Zuschlagsbetraege fuer Risikoanalyse.", kind="warn")
        else:
            p90 = float(risk_df["award_amount_chf"].quantile(0.90))
            p95 = float(risk_df["award_amount_chf"].quantile(0.95))

            pair_counts = (
                risk_df.groupby(["procurement_office", "winner_name"], as_index=False)
                .agg(pair_repeat_count=("award_row_id", "count"))
            )
            risk_df = risk_df.merge(pair_counts, on=["procurement_office", "winner_name"], how="left")
            risk_df["pair_repeat_count"] = risk_df["pair_repeat_count"].fillna(0).astype(int)

            risk_df["risk_score"] = 0
            risk_df.loc[risk_df["offers_count"] <= 1, "risk_score"] += 35
            risk_df.loc[risk_df["offers_count"] == 2, "risk_score"] += 10
            risk_df.loc[risk_df["award_amount_chf"] >= p95, "risk_score"] += 30
            risk_df.loc[(risk_df["award_amount_chf"] >= p90) & (risk_df["award_amount_chf"] < p95), "risk_score"] += 15
            risk_df.loc[risk_df["pair_repeat_count"] >= 5, "risk_score"] += 20
            risk_df.loc[(risk_df["pair_repeat_count"] >= 3) & (risk_df["pair_repeat_count"] < 5), "risk_score"] += 10
            risk_df.loc[
                risk_df["procurement_type"].str.casefold().str.contains("freihaendig|direkt", regex=True, na=False),
                "risk_score",
            ] += 15
            risk_df.loc[
                (risk_df["award_amount_chf"] >= 1_000_000) & (risk_df["offers_count"] <= 1),
                "risk_score",
            ] += 20
            risk_df["risk_score"] = risk_df["risk_score"].clip(0, 100)

            risky = risk_df[risk_df["risk_score"] >= 40].copy().sort_values(
                ["risk_score", "award_amount_chf"], ascending=[False, False]
            )
            preview_cols = [
                "publication_date",
                "publication_number",
                "title",
                "procurement_office",
                "winner_name",
                "award_amount_chf",
                "offers_count",
                "pair_repeat_count",
                "risk_score",
                "project_url",
            ]
            risk_table = mo.ui.table(
                risky[preview_cols].head(250),
                page_size=table_rows_per_page,
                selection=None,
                label="Auffaellige Zuschlaege (Heuristik)",
            )

            bands = pd.cut(
                risk_df["risk_score"],
                bins=[0, 20, 40, 60, 80, 101],
                labels=["0-20", "21-40", "41-60", "61-80", "81-100"],
                include_lowest=True,
                right=False,
            )
            band_df = bands.value_counts(dropna=False).reset_index()
            band_df.columns = ["risk_band", "count"]
            band_df["risk_band"] = band_df["risk_band"].astype(str)
            risk_hist = (
                alt.Chart(band_df)
                .mark_bar(color="#d62728")
                .encode(
                    x=alt.X("risk_band:N", title="Risikoband"),
                    y=alt.Y("count:Q", title="Anzahl Zuschlaege"),
                    tooltip=["risk_band:N", "count:Q"],
                )
                .properties(height=risk_hist_height, title="Verteilung Risiko-Scores")
            )

            risk_panel = mo.vstack(
                [
                    risk_explainer,
                    mo.callout(
                        mo.md(
                            f"Hochrisiko-Faelle (Score >= 40): **{len(risky):,}** von **{len(risk_df):,}**"
                            .replace(",", "'")
                        ),
                        kind="warn",
                    ),
                    mo.ui.altair_chart(risk_hist, chart_selection=False, label="Risk Histogram"),
                    risk_table,
                ],
                gap=1.0,
            )
    return (risk_panel,)


@app.cell
def _(filtered, mo, pd):
    if filtered.empty:
        data_panel = mo.callout("Keine Datensaetze im aktuellen Filter.", kind="warn")
    else:
        data_explainer = mo.callout(
            mo.md(
                """
Hier siehst du die zugrundeliegenden Faelle zur Verifikation.
Nutze diese Tabelle fuer Plausibilisierung und als Einstieg in einzelne Stories.
"""
            ),
            kind="neutral",
        )
        recent_cols = [
            "publication_date",
            "publication_number",
            "title",
            "procurement_office",
            "winner_name",
            "buyer_canton",
            "winner_canton",
            "procurement_type",
            "award_amount_chf",
            "offers_count",
            "cpv_primary",
        ]
        cols = [column for column in recent_cols if column in filtered.columns]
        if "publication_dt" in filtered.columns:
            base_df = filtered.sort_values("publication_dt", ascending=False)
        else:
            base_df = filtered
        table_df = base_df[cols].head(400)
        data_table = mo.ui.table(
            table_df,
            page_size=table_rows_per_page,
            selection=None,
            label="Gefilterte Zuschlaege",
        )
        data_panel = mo.vstack([data_explainer, mo.md("### Datenvorschau"), data_table], gap=1.0)
    return (data_panel,)


@app.cell
def _(mo):
    method_panel = mo.vstack(
        [
            mo.callout(
                mo.md(
                    """
### Methodik und Einordnung

- Alle Auswertungen basieren auf den aktuell gefilterten Zuschlaegen.
- Viele Kennzahlen sind **deskriptiv**: sie zeigen Muster, nicht automatisch Fehlverhalten.
- Risiko-Score ist eine Priorisierungshilfe fuer journalistische Nachrecherche.
"""
                ),
                kind="info",
            ),
            mo.md(
                """
#### Glossar

- **Top-10 Anteil**: Volumenanteil der zehn groessten Winner.
- **Gini**: Ungleichverteilung von Volumen zwischen Winnern.
- **Single-Bid**: Zuschlag mit nur einem Angebot.
- **Interkantonal**: Buyer- und Winner-Kanton unterscheiden sich.
"""
            ),
            mo.md(
                """
#### Recherche-Workflow (Empfehlung)

1. In `Uebersicht` auffaellige Signale identifizieren.  
2. In `Konzentration`, `Abhaengigkeit` und `Wettbewerb` Ursachen eingrenzen.  
3. In `Risiko & Outlier` konkrete Faelle priorisieren.  
4. In `Daten` Einzelbelege und Publikationsnummern pruefen.
"""
            ),
        ],
        gap=1.0,
    )
    return (method_panel,)


@app.cell(hide_code=True)
def _(
    competition_panel,
    concentration_panel,
    data_panel,
    dependency_panel,
    method_panel,
    mo,
    overview_panel,
    region_panel,
    risk_panel,
    trend_panel,
):
    tabs = mo.tabs(
        {
            "Uebersicht": overview_panel,
            "Trend & CPV": trend_panel,
            "Konzentration & Macht": concentration_panel,
            "Buyer-Winner Abhaengigkeit": dependency_panel,
            "Wettbewerb vs Preis": competition_panel,
            "Regionen & Bias": region_panel,
            "Risiko & Outlier": risk_panel,
            "Daten": data_panel,
            "Methodik": method_panel,
        }
    )
    tabs
    return


if __name__ == "__main__":
    app.run()
