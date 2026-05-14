"""Equity Valuation Web App — DCF + Comps for any listed company.

Built on Anthropic financial-services skills (Apache 2.0).
Spotify-style dark UI. Spanish.
"""

import io
import json
from copy import deepcopy
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import build_comps
import build_dcf_xlsx
import compute_dcf
import data_fetcher
import memo_generator

st.set_page_config(
    page_title="Valoracion DCF | Spotify Style",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

SPOTIFY_GREEN = "#1DB954"
SPOTIFY_GREEN_LIGHT = "#1ED760"
SPOTIFY_BG = "#121212"
SPOTIFY_CARD = "#181818"
SPOTIFY_TERTIARY = "#282828"
SPOTIFY_TEXT_MUTED = "#B3B3B3"

CUSTOM_CSS = f"""
<style>
    .stApp {{
        background-color: {SPOTIFY_BG};
        color: #FFFFFF;
    }}
    section[data-testid="stSidebar"] {{
        background-color: #000000;
    }}
    h1, h2, h3, h4 {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }}
    .stButton > button {{
        background-color: {SPOTIFY_GREEN};
        color: #000000;
        border: none;
        border-radius: 500px;
        font-weight: 700;
        padding: 0.6rem 2rem;
        transition: all 0.15s ease;
    }}
    .stButton > button:hover {{
        background-color: {SPOTIFY_GREEN_LIGHT};
        transform: scale(1.04);
        color: #000000;
    }}
    [data-testid="stMetric"] {{
        background-color: {SPOTIFY_CARD};
        padding: 1.2rem;
        border-radius: 8px;
        border: 1px solid {SPOTIFY_TERTIARY};
    }}
    [data-testid="stMetric"]:hover {{
        background-color: {SPOTIFY_TERTIARY};
    }}
    [data-testid="stMetricLabel"] {{
        color: {SPOTIFY_TEXT_MUTED} !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }}
    [data-testid="stMetricValue"] {{
        color: #FFFFFF !important;
        font-size: 2rem !important;
        font-weight: 700;
    }}
    [data-testid="stMetricDelta"] {{
        font-weight: 600;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {SPOTIFY_CARD};
        border-radius: 500px;
        padding: 0.5rem 1.2rem;
        color: {SPOTIFY_TEXT_MUTED};
        font-weight: 600;
        border: none;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {SPOTIFY_GREEN} !important;
        color: #000000 !important;
    }}
    .stDataFrame, .stTable {{
        background-color: {SPOTIFY_CARD};
        border-radius: 8px;
    }}
    div[data-testid="stExpander"] {{
        background-color: {SPOTIFY_CARD};
        border-radius: 8px;
        border: 1px solid {SPOTIFY_TERTIARY};
    }}
    .stSlider > div > div > div > div {{
        background-color: {SPOTIFY_GREEN};
    }}
    .stSelectbox label, .stMultiSelect label, .stNumberInput label, .stTextInput label, .stSlider label {{
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }}
    .stAlert {{
        background-color: {SPOTIFY_CARD};
        border-radius: 8px;
    }}
    a {{
        color: {SPOTIFY_GREEN} !important;
    }}
    /* Headline hero */
    .hero-title {{
        font-size: 3rem;
        font-weight: 900;
        letter-spacing: -0.04em;
        background: linear-gradient(135deg, {SPOTIFY_GREEN} 0%, {SPOTIFY_GREEN_LIGHT} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }}
    .hero-sub {{
        color: {SPOTIFY_TEXT_MUTED};
        font-size: 1rem;
        margin-bottom: 2rem;
    }}
</style>
"""


def init_state():
    if "inputs" not in st.session_state:
        st.session_state.inputs = None
    if "peers_data" not in st.session_state:
        st.session_state.peers_data = None
    if "scenarios" not in st.session_state:
        st.session_state.scenarios = None


def render_header():
    st.markdown(
        f"""
        <div class="hero-title">Valoracion DCF</div>
        <div class="hero-sub">Analisis financiero institucional para cualquier empresa cotizada. Construido con agentes Anthropic FSI (Apache 2.0).</div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_companies():
    path = Path(__file__).parent / "companies.json"
    if not path.exists():
        return [], {}
    grouped = json.loads(path.read_text(encoding="utf-8"))
    labels = []
    lookup = {}
    for region, companies in grouped.items():
        for name, ticker in companies.items():
            label = f"{name} ({ticker})"
            labels.append(label)
            lookup[label] = ticker
    return labels, lookup


def render_ticker_input():
    labels, lookup = load_companies()
    with st.sidebar:
        st.header("Empresa y comparables")
        st.caption(f"{len(labels)} empresas cotizadas en US, EU, Asia, LatAm. Escribe para buscar.")

        default_target = next((l for l in labels if "(AAPL)" in l), labels[0] if labels else "")
        target_label = st.selectbox(
            "Empresa objetivo",
            options=labels,
            index=labels.index(default_target) if default_target in labels else 0,
            help="Busca por nombre o ticker.",
        )
        ticker = lookup.get(target_label, "AAPL")

        default_peers_tickers = {"MSFT", "GOOGL", "META", "AMZN", "NFLX"}
        default_peers_labels = [l for l in labels if lookup.get(l) in default_peers_tickers]
        peer_labels = st.multiselect(
            "Empresas comparables",
            options=labels,
            default=default_peers_labels,
            help="Elige de 3 a 6 comparables. Busca por nombre o ticker.",
        )
        peers = [lookup[l] for l in peer_labels if l in lookup]

        with st.expander("Tickers personalizados (avanzado)"):
            custom_target = st.text_input("Sobrescribir ticker objetivo", value="", help="Para empresas no listadas. Ej: ITX.MC")
            custom_peers = st.text_input("Sobrescribir tickers comparables (coma)", value="", help="Ej: ITX.MC, HM-B.ST")
            if custom_target.strip():
                ticker = custom_target.strip()
            if custom_peers.strip():
                peers = [t.strip() for t in custom_peers.split(",") if t.strip()]

        fetch = st.button("Cargar datos", type="primary", use_container_width=True)
        return ticker, peers, fetch


def render_wacc_controls(inputs):
    with st.sidebar:
        st.header("Coste de capital (WACC)")
        wacc_d = inputs["wacc"]
        rf = st.number_input("Tasa libre de riesgo (%)", min_value=0.0, max_value=15.0, value=float(wacc_d["risk_free_rate_pct"]), step=0.1)
        erp = st.number_input("Prima de riesgo mercado (%)", min_value=3.0, max_value=15.0, value=float(wacc_d["equity_risk_premium_pct"]), step=0.1)
        beta = st.number_input("Beta (5 anos)", min_value=0.0, max_value=3.0, value=float(wacc_d["beta"]), step=0.05)
        tax = st.number_input("Tipo impositivo (%)", min_value=0.0, max_value=40.0, value=float(wacc_d["tax_rate_pct"]), step=1.0)

        cost_of_equity = rf + beta * erp
        st.metric("Coste del equity (CAPM)", f"{cost_of_equity:.2f}%")
        wacc = cost_of_equity
        st.metric("WACC (simplificado 100% equity)", f"{wacc:.2f}%")

        wacc_d["risk_free_rate_pct"] = rf
        wacc_d["equity_risk_premium_pct"] = erp
        wacc_d["beta"] = beta
        wacc_d["tax_rate_pct"] = tax
        wacc_d["cost_of_equity_pct"] = round(cost_of_equity, 2)
        wacc_d["wacc_pct"] = round(wacc, 2)
        return inputs


SCENARIO_LABELS = {"bear": "Pesimista", "base": "Base", "bull": "Optimista"}


def render_scenario_controls(inputs, scenario_key):
    label = SCENARIO_LABELS[scenario_key]
    with st.expander(f"Supuestos {label}", expanded=(scenario_key == "base")):
        a = inputs[f"projection_assumptions_{scenario_key}"]
        y1_growth = st.slider(f"{label}: Crecimiento ingresos Y1 (%)", -10.0, 30.0, float(a["revenue_growth_yoy_pct"][0]), 0.5, key=f"{scenario_key}_y1g")
        y10_growth = st.slider(f"{label}: Crecimiento ingresos Y10 (%)", -5.0, 15.0, float(a["revenue_growth_yoy_pct"][-1]), 0.5, key=f"{scenario_key}_y10g")
        margin_stable = st.slider(f"{label}: Margen EBITDA (%)", 5.0, 50.0, float(a["ebitda_margin_pct"][0]), 0.5, key=f"{scenario_key}_mgn")
        terminal_g = st.slider(f"{label}: Crecimiento terminal (%)", 0.0, 5.0, float(a["terminal_growth_pct"]), 0.1, key=f"{scenario_key}_tg")
        exit_mult = st.slider(f"{label}: Multiplo salida (EV/EBITDA)", 4.0, 25.0, float(a["exit_multiple_ev_ebitda"]), 0.5, key=f"{scenario_key}_em")

        a["revenue_growth_yoy_pct"] = list(_interp_decay(y1_growth, y10_growth, 10))
        a["ebitda_margin_pct"] = [margin_stable] * 10
        a["terminal_growth_pct"] = terminal_g
        a["exit_multiple_ev_ebitda"] = exit_mult
    return inputs


def _interp_decay(start, end, n):
    if n <= 1:
        return [start]
    step = (end - start) / (n - 1)
    return [round(start + i * step, 2) for i in range(n)]


def render_market_data_summary(inputs):
    md = inputs["market_data"]
    ccy = inputs["currency"]
    cols = st.columns(4)
    cols[0].metric("Precio", f"{ccy} {md['current_price_eur']:.2f}")
    cols[1].metric("Capitalizacion", f"{ccy} {md['market_cap_eur_m']:,.0f}M")
    cols[2].metric("Caja neta / (Deuda)", f"{ccy} {md['net_cash_eur_m']:,.0f}M")
    cols[3].metric("Valor empresa (EV)", f"{ccy} {md['enterprise_value_eur_m']:,.0f}M")


def render_scenario_cards(inputs, scenarios):
    ccy = inputs["currency"]
    current = inputs["market_data"]["current_price_eur"]
    cols = st.columns(3)
    for i, case in enumerate(["bear", "base", "bull"]):
        s = scenarios[case]["dcf"]
        upside = (s["implied_share_price"] / current - 1) * 100 if current else 0
        with cols[i]:
            st.metric(
                label=f"{SCENARIO_LABELS[case]} implicito",
                value=f"{ccy} {s['implied_share_price']:.2f}",
                delta=f"{upside:+.1f}% vs mercado",
            )


def _plotly_dark_layout(fig, title):
    fig.update_layout(
        title=dict(text=title, font=dict(color="#FFFFFF", size=18, family="sans-serif", weight=700)),
        paper_bgcolor=SPOTIFY_BG,
        plot_bgcolor=SPOTIFY_CARD,
        font=dict(color="#FFFFFF", family="sans-serif"),
        xaxis=dict(gridcolor=SPOTIFY_TERTIARY, color=SPOTIFY_TEXT_MUTED),
        yaxis=dict(gridcolor=SPOTIFY_TERTIARY, color=SPOTIFY_TEXT_MUTED),
        legend=dict(bgcolor=SPOTIFY_CARD, bordercolor=SPOTIFY_TERTIARY),
        height=420,
    )
    return fig


def render_projection_chart(inputs, scenarios):
    ccy = inputs["currency"]
    proj = scenarios["base"]["projection"]
    years = [f"Y{y}" for y in proj["years"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=years, y=proj["revenue"], name="Ingresos", marker_color=SPOTIFY_GREEN))
    fig.add_trace(go.Bar(x=years, y=proj["ebitda"], name="EBITDA", marker_color="#1ED760"))
    fig.add_trace(go.Bar(x=years, y=proj["fcf"], name="FCF (Unlevered)", marker_color="#7CE3A4"))
    fig.add_trace(go.Scatter(x=years, y=proj["pv_fcf"], name="VP del FCF", mode="lines+markers", line=dict(color="#FFFFFF", width=3)))
    _plotly_dark_layout(fig, f"Proyeccion 10 anos - Caso Base ({ccy} M)")
    fig.update_layout(xaxis_title="Ano proyectado", yaxis_title=f"Importe ({ccy} M)", barmode="group")
    st.plotly_chart(fig, use_container_width=True)


def render_sensitivity_heatmap(inputs, scenarios):
    base = scenarios["base"]
    wacc_d = inputs["wacc"]
    md = inputs["market_data"]
    fcf_y10 = base["projection"]["fcf"][-1]
    sum_pv = base["dcf"]["sum_pv_fcf"]
    net_cash = md["net_cash_eur_m"]
    shares = md["shares_outstanding_m"]
    wacc_range = inputs["sensitivity_ranges"]["wacc_pct"]
    tg_range = inputs["sensitivity_ranges"]["terminal_growth_pct"]

    matrix = []
    for tg in tg_range:
        row = []
        for w in wacc_range:
            wf = w / 100
            tgf = tg / 100
            if wf <= tgf:
                row.append(None)
                continue
            tv = fcf_y10 * (1 + tgf) / (wf - tgf)
            pv_tv = tv / ((1 + wf) ** 9.5)
            equity = pv_tv + sum_pv + net_cash
            implied = equity / shares if shares else 0
            row.append(round(implied, 2))
        matrix.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=[f"{w:.1f}%" for w in wacc_range],
        y=[f"{tg:.1f}%" for tg in tg_range],
        colorscale=[[0, "#3F3F3F"], [0.5, "#1DB954"], [1, "#1ED760"]],
        text=[[f"{v:.1f}" if v is not None else "" for v in row] for row in matrix],
        texttemplate="%{text}",
        hovertemplate="WACC: %{x}<br>g Terminal: %{y}<br>Implicito: %{z:.2f}<extra></extra>",
    ))
    _plotly_dark_layout(fig, "Sensibilidad: Precio implicito vs WACC y Crecimiento Terminal")
    fig.update_layout(xaxis_title="WACC", yaxis_title="Crecimiento Terminal")
    st.plotly_chart(fig, use_container_width=True)


def render_historicals_table(inputs):
    hist = inputs["historical"]
    fy_keys = sorted(hist.keys())
    label_map = {"revenue": "Ingresos", "ebitda": "EBITDA", "ebit": "EBIT", "da": "D&A", "capex": "CapEx", "fcf": "FCF", "net_income": "Beneficio neto"}
    rows = []
    for key, label in label_map.items():
        rows.append({"Metrica": label, **{fy: hist[fy].get(key, 0) for fy in fy_keys}})
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_projection_table(scenarios):
    base = scenarios["base"]["projection"]
    df = pd.DataFrame({
        "Ano": [f"Y{y}" for y in base["years"]],
        "Ingresos": [round(v) for v in base["revenue"]],
        "EBITDA": [round(v) for v in base["ebitda"]],
        "EBIT": [round(v) for v in base["ebit"]],
        "FCF": [round(v) for v in base["fcf"]],
        "Factor descuento": [round(v, 4) for v in base["pv_factor"]],
        "VP del FCF": [round(v) for v in base["pv_fcf"]],
    })
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_comps_table(peers_data):
    if not peers_data:
        st.info("No hay datos de comparables. Anade peers en la barra lateral y recarga.")
        return
    df = pd.DataFrame(peers_data)
    display_cols = ["Company", "Ticker", "Currency", "Revenue_TTM_LCY", "EBITDA_TTM_LCY", "EV_Sales", "EV_EBITDA", "PE_Trailing", "Beta_5Y"]
    display_df = df[display_cols].copy()
    display_df["Revenue_TTM_LCY"] = (display_df["Revenue_TTM_LCY"] / 1_000_000).round().astype(int)
    display_df["EBITDA_TTM_LCY"] = (display_df["EBITDA_TTM_LCY"] / 1_000_000).round().astype(int)
    display_df = display_df.rename(columns={
        "Company": "Empresa",
        "Ticker": "Ticker",
        "Currency": "Moneda",
        "Revenue_TTM_LCY": "Ingresos (M LCY)",
        "EBITDA_TTM_LCY": "EBITDA (M LCY)",
        "EV_Sales": "EV/Ventas",
        "EV_EBITDA": "EV/EBITDA",
        "PE_Trailing": "P/E (TTM)",
        "Beta_5Y": "Beta",
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("**Estadisticas de multiplos**")
    nums = pd.DataFrame(peers_data)[["EV_Sales", "EV_EBITDA", "PE_Trailing"]].apply(pd.to_numeric, errors="coerce")
    stats = pd.DataFrame({
        "EV/Ventas": [nums["EV_Sales"].max(), nums["EV_Sales"].quantile(0.75), nums["EV_Sales"].median(), nums["EV_Sales"].quantile(0.25), nums["EV_Sales"].min()],
        "EV/EBITDA": [nums["EV_EBITDA"].max(), nums["EV_EBITDA"].quantile(0.75), nums["EV_EBITDA"].median(), nums["EV_EBITDA"].quantile(0.25), nums["EV_EBITDA"].min()],
        "P/E TTM": [nums["PE_Trailing"].max(), nums["PE_Trailing"].quantile(0.75), nums["PE_Trailing"].median(), nums["PE_Trailing"].quantile(0.25), nums["PE_Trailing"].min()],
    }, index=["Maximo", "Percentil 75", "Mediana", "Percentil 25", "Minimo"])
    st.dataframe(stats.round(2), use_container_width=True)


def render_downloads(inputs, scenarios, peers_data):
    company = inputs["company"]
    safe_name = company.replace(" ", "_").replace(".", "").lower()

    dcf_wb = build_dcf_xlsx.build_workbook(inputs)
    dcf_buffer = io.BytesIO()
    dcf_wb.save(dcf_buffer)
    dcf_buffer.seek(0)

    comps_buffer = None
    if peers_data:
        comps_wb = build_comps.build_workbook(inputs, peers_data)
        comps_buffer = io.BytesIO()
        comps_wb.save(comps_buffer)
        comps_buffer.seek(0)

    memo = memo_generator.generate_memo(inputs, scenarios, peers_data)
    inputs_json = json.dumps(inputs, indent=2, default=str)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.download_button("Modelo DCF (.xlsx)", data=dcf_buffer, file_name=f"{safe_name}_dcf.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with col2:
        if comps_buffer:
            st.download_button("Comparables (.xlsx)", data=comps_buffer, file_name=f"{safe_name}_comps.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.button("Comparables (.xlsx)", disabled=True, help="Anade peers en la barra lateral primero")
    with col3:
        st.download_button("Memo (.md)", data=memo, file_name=f"{safe_name}_analisis.md", mime="text/markdown")
    with col4:
        st.download_button("Inputs (.json)", data=inputs_json, file_name=f"{safe_name}_inputs.json", mime="application/json")


def render_warnings(inputs):
    md = inputs["market_data"]
    hist_keys = sorted(inputs["historical"].keys())
    latest = inputs["historical"][hist_keys[-1]] if hist_keys else None

    if not md["current_price_eur"]:
        st.warning("Precio actual es cero. Verifica que el ticker es correcto.")
    if not md["market_cap_eur_m"]:
        st.warning("Capitalizacion en cero. Datos pueden estar incompletos.")
    if not latest or latest["revenue"] == 0:
        st.error("No se pudo obtener historial de ingresos. Comprueba el ticker o prueba otro sufijo de bolsa (.L, .MC, .T).")


def main():
    init_state()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    render_header()
    ticker, peers, fetch = render_ticker_input()

    if fetch:
        with st.spinner(f"Cargando {ticker} + {len(peers)} comparables..."):
            try:
                inputs = data_fetcher.fetch_company(ticker, peer_tickers=peers)
                peers_data = inputs.pop("peers_data", None) if "peers_data" in inputs else data_fetcher.fetch_peers(peers, inputs["as_of_date"])
                st.session_state.inputs = inputs
                st.session_state.peers_data = peers_data
                st.session_state.scenarios = None
                st.success(f"Cargado {inputs['company']} ({ticker}) + {len(peers_data)} comparables")
            except Exception as e:
                st.error(f"Error en carga de datos: {e}")
                return

    if st.session_state.inputs is None:
        st.info("Selecciona una empresa objetivo y comparables en la barra lateral, despues click **Cargar datos**.")
        st.markdown("---")
        st.markdown(
            """
            ### Como funciona

            1. Selecciona una empresa cotizada (372 disponibles US/EU/Asia/LatAm)
            2. Elige 3 a 6 comparables del mismo sector
            3. Ajusta WACC y supuestos de escenarios (Pesimista / Base / Optimista)
            4. Obtienes proyeccion 10 anos, valor implicito, sensibilidad, comparables
            5. Descarga modelo Excel + memo + inputs

            ### Metodologia

            DCF con 10 anos explicitos. WACC via CAPM. Valor terminal mezclado (perpetuidad + multiplo salida). Cross-check contra peer multiples.

            ### Aviso legal

            **NO ES ASESORAMIENTO FINANCIERO.** Herramienta educativa y producto analista. Verificar contra reporte anual oficial. Rendimientos pasados no predicen futuros.

            ### Construido con

            Skills open-source de [Anthropic financial-services](https://github.com/anthropics/financial-services) (Apache 2.0). DCF, comparables y auditoria.
            """
        )
        return

    inputs = st.session_state.inputs
    peers_data = st.session_state.peers_data

    inputs = render_wacc_controls(inputs)

    with st.sidebar:
        st.header("Escenarios")
    for scen in ["bear", "base", "bull"]:
        with st.sidebar:
            inputs = render_scenario_controls(inputs, scen)

    try:
        scenarios = compute_dcf.run_all(inputs)
    except Exception as e:
        st.error(f"Error en calculo DCF: {e}")
        return
    st.session_state.scenarios = scenarios

    company = inputs["company"]
    ticker = inputs["ticker"]
    st.header(f"{company} ({ticker})")

    render_warnings(inputs)
    render_market_data_summary(inputs)

    st.markdown("### Escenarios de valoracion")
    render_scenario_cards(inputs, scenarios)

    tabs = st.tabs(["Resumen", "Proyeccion", "Sensibilidad", "Comparables", "Historicos", "Descargas"])

    with tabs[0]:
        ccy = inputs["currency"]
        st.markdown(f"**Precio implicito caso base: {ccy} {scenarios['base']['dcf']['implied_share_price']:.2f}**")
        upside = (scenarios["base"]["dcf"]["implied_share_price"] / inputs["market_data"]["current_price_eur"] - 1) * 100
        st.markdown(f"**Potencial vs mercado: {upside:+.1f}%**")
        st.markdown("---")
        st.markdown("**Puente de valoracion (Caso Base)**")
        bridge_data = {
            "Componente": [
                "Suma VP(FCF) Y1-Y10",
                "VP Valor Terminal",
                "(=) Valor Empresa (EV)",
                "(+) Caja neta",
                "(=) Valor Equity",
            ],
            "Valor": [
                scenarios["base"]["dcf"]["sum_pv_fcf"],
                scenarios["base"]["dcf"]["pv_tv_blended"],
                scenarios["base"]["dcf"]["enterprise_value"],
                inputs["market_data"]["net_cash_eur_m"],
                scenarios["base"]["dcf"]["equity_value"],
            ],
        }
        bridge_df = pd.DataFrame(bridge_data)
        bridge_df["Valor"] = bridge_df["Valor"].round(0).astype(int)
        st.dataframe(bridge_df, use_container_width=True, hide_index=True)
        tv_pct = scenarios["base"]["dcf"]["tv_pct_of_ev"]
        if 50 <= tv_pct <= 70:
            st.success(f"Check: Terminal {tv_pct:.1f}% del EV (banda aceptable 50-70%)")
        else:
            st.warning(f"Check: Terminal {tv_pct:.1f}% del EV (FUERA del rango tipico 50-70%)")

    with tabs[1]:
        render_projection_chart(inputs, scenarios)
        st.markdown("**Tabla detallada de proyeccion**")
        render_projection_table(scenarios)

    with tabs[2]:
        render_sensitivity_heatmap(inputs, scenarios)
        st.caption(
            "Precio implicito a cada combinacion de WACC y crecimiento terminal. "
            "Mantiene FCFs explicitos al WACC base; solo varia el terminal."
        )

    with tabs[3]:
        st.markdown("**Empresas comparables**")
        render_comps_table(peers_data)

    with tabs[4]:
        st.markdown("**Financieros historicos (ultimos 5 anos disponibles)**")
        render_historicals_table(inputs)

    with tabs[5]:
        st.markdown("**Descargar deliverables**")
        render_downloads(inputs, scenarios, peers_data)

    st.markdown("---")
    st.caption(
        "NO ES ASESORAMIENTO FINANCIERO. Herramienta educativa. Verificar contra reporte anual oficial. "
        "Construido con skills de Anthropic financial-services (Apache 2.0)."
    )


if __name__ == "__main__":
    main()
