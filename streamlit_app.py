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
import explanations
import insights as insights_mod
import memo_generator
import news as news_mod
import wallet as wallet_mod


@st.cache_data(ttl=600, show_spinner=False)
def _cached_news(query: str, max_records: int = 18):
    return news_mod.gdelt_query(query, max_records=max_records)

st.set_page_config(
    page_title="Valoracion de Renta Variable | DCF + Comparables",
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
        font-size: clamp(0.95rem, 1.8vw, 1.5rem) !important;
        font-weight: 700;
        white-space: normal !important;
        overflow-wrap: anywhere !important;
        overflow: visible !important;
    }}
    [data-testid="stMetricValue"] > div {{
        overflow: visible !important;
        text-overflow: clip !important;
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
        <div class="hero-title">Valoracion de Renta Variable</div>
        <div class="hero-sub">Analisis fundamental de empresas cotizadas: DCF, comparables y diagnostico de calidad. Datos reales, metodologia institucional.</div>
        """,
        unsafe_allow_html=True,
    )


SENT_STYLE = {
    "positivo": ("#1DB954", "OK"),
    "neutro": ("#E8C547", "~"),
    "alerta": ("#E84B4B", "!"),
}


def render_insights(inputs, scenarios, peers_data):
    items = insights_mod.generate_insights(inputs, scenarios, peers_data)
    st.markdown(f"### Insights del analisis")
    st.caption(insights_mod.insights_summary_line(items))
    cats = {}
    for it in items:
        cats.setdefault(it["categoria"], []).append(it)
    for cat, group in cats.items():
        st.markdown(f"**{cat}**")
        for it in group:
            color, tag = SENT_STYLE.get(it["sentimiento"], ("#B3B3B3", "-"))
            st.markdown(
                f"""<div style="background-color:#181818;border-left:4px solid {color};
                border-radius:6px;padding:0.8rem 1rem;margin-bottom:0.5rem;">
                <span style="color:{color};font-weight:700;">[{tag}] {it['titulo']}</span><br>
                <span style="color:#B3B3B3;font-size:0.92rem;">{it['detalle']}</span>
                </div>""",
                unsafe_allow_html=True,
            )


def render_wallet(inputs):
    st.markdown("### Mi Cartera - Laboratorio de simulacion")
    st.info(
        "Practica con **dinero ficticio** (paper trading). Toma las tesis del analisis, "
        "ejecuta ordenes simuladas, y comprueba con el tiempo si seguir el modelo te "
        "hubiera funcionado. Sin riesgo: ni un euro real. Asi aprendes y decides si el "
        "servicio te aporta antes de invertir de verdad."
    )

    sub = st.tabs(["Alpaca (acciones)", "Polymarket (solo lectura)"])

    # ---------- Alpaca ----------
    with sub[0]:
        with st.expander("Guia paso a paso: crear y conectar tu cuenta paper de Alpaca (gratis, ~3 min)", expanded=True):
            st.markdown(
                "**Paso 1 - Crear cuenta**\n"
                "- Abre **https://alpaca.markets** y pulsa *Sign Up*.\n"
                "- Registrate con email y contrasena. Verifica el email (revisa spam).\n"
                "- No necesitas fondear ni completar el alta de broker para usar Paper.\n\n"
                "**Paso 2 - Entrar al modo Paper**\n"
                "- Inicia sesion. Veras el panel de *Trading*.\n"
                "- Arriba a la izquierda hay un selector de cuenta: cambia de *Live* a "
                "**Paper**. Es una cartera ficticia con 100.000 USD virtuales.\n\n"
                "**Paso 3 - Generar las claves API (en Paper)**\n"
                "- Confirma que el selector dice **Paper** (critico: las claves Live no "
                "funcionan aqui y viceversa).\n"
                "- En el panel derecho busca **API Keys** y pulsa **Generate New Key** "
                "(o *Regenerate*).\n"
                "- Te muestra **API Key ID** y **Secret Key**. El Secret se ve **una sola "
                "vez**: copialo ya. Si lo pierdes, regenera (invalida el anterior).\n\n"
                "**Paso 4 - Conectar aqui**\n"
                "- Deja activado **Paper Trading** abajo.\n"
                "- Pega *API Key ID* y *Secret* en los campos.\n"
                "- Pulsa **Conectar Alpaca**. Si ves tu cuenta y 100.000 USD, listo.\n"
                "- Las claves solo viven en tu sesion del navegador. No se guardan ni se "
                "suben a ningun sitio (puedes verificarlo: el repo no las contiene).\n\n"
                "**Si falla la conexion**\n"
                "- *Claves invalidas*: generaste claves Live, no Paper. Cambia a Paper y regenera.\n"
                "- *Sin permiso*: copiaste mal el Secret (espacios). Regenera y pega limpio.\n"
                "- *Nada aparece*: email sin verificar. Confirma el correo de Alpaca y reintenta."
            )
        st.caption("Modo Paper = dinero ficticio. Aprende y valida la metodologia sin arriesgar capital.")
        secrets_key = None
        try:
            secrets_key = st.secrets.get("ALPACA_API_KEY")
            secrets_sec = st.secrets.get("ALPACA_API_SECRET")
        except Exception:
            secrets_sec = None

        paper = st.toggle("Paper Trading (dinero ficticio)", value=True, key="alp_paper")
        if not paper:
            st.error(
                "MODO LIVE: las ordenes usan DINERO REAL. Verifica simbolo, cantidad y lado "
                "antes de confirmar. Tu decides y asumes el riesgo."
            )
        col_k, col_s = st.columns(2)
        akey = col_k.text_input("Alpaca API Key ID", value=secrets_key or "", type="password", key="alp_key")
        asec = col_s.text_input("Alpaca API Secret", value=secrets_sec or "", type="password", key="alp_sec")

        if st.button("Conectar Alpaca", key="alp_conn"):
            try:
                acct = wallet_mod.alpaca_account(akey, asec, paper=paper)
                st.session_state["alp_acct"] = acct
                st.session_state["alp_ok"] = True
                st.success("Conectado.")
            except wallet_mod.WalletError as e:
                st.session_state["alp_ok"] = False
                st.error(str(e))

        if st.session_state.get("alp_ok"):
            try:
                acct = wallet_mod.alpaca_account(akey, asec, paper=paper)
                positions = wallet_mod.alpaca_positions(akey, asec, paper=paper)
            except wallet_mod.WalletError as e:
                st.error(str(e))
                return

            ccy = acct.get("currency", "USD")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Valor cartera", f"{ccy} {float(acct.get('portfolio_value', 0)):,.0f}")
            c2.metric("Efectivo", f"{ccy} {float(acct.get('cash', 0)):,.0f}")
            c3.metric("Poder de compra", f"{ccy} {float(acct.get('buying_power', 0)):,.0f}")
            c4.metric("Modo", "PAPER" if paper else "LIVE")

            if positions:
                rows = []
                for p in positions:
                    rows.append({
                        "Simbolo": p.get("symbol"),
                        "Cantidad": p.get("qty"),
                        "Valor mercado": round(float(p.get("market_value", 0)), 2),
                        "P&L no realizado": round(float(p.get("unrealized_pl", 0)), 2),
                        "P&L %": round(float(p.get("unrealized_plpc", 0)) * 100, 2),
                    })
                st.markdown("**Posiciones**")
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("Sin posiciones abiertas.")

            st.markdown("---")
            st.markdown("**Nueva orden** (basada en tu analisis)")
            base_sym = inputs.get("ticker", "").split(".")[0]
            o1, o2, o3 = st.columns(3)
            sym = o1.text_input("Simbolo", value=base_sym, key="ord_sym")
            qty = o2.number_input("Cantidad (acciones)", min_value=0.0, value=1.0, step=1.0, key="ord_qty")
            side = o3.selectbox("Lado", ["buy", "sell"], key="ord_side")
            verdict_hint = ""
            model_verdict, model_up = "NA", 0.0
            sc = st.session_state.get("scenarios")
            if sc and inputs.get("market_data", {}).get("current_price_eur"):
                imp = sc["base"]["dcf"]["implied_share_price"]
                cur = inputs["market_data"]["current_price_eur"]
                model_up = (imp / cur - 1) * 100 if cur else 0
                m = sc.get("_meta", {})
                if m.get("dcf_applicable") is False:
                    model_verdict = "NOVALORABLE"
                elif model_up > 10:
                    model_verdict = "BARATA"
                elif model_up < -10:
                    model_verdict = "CARA"
                else:
                    model_verdict = "JUSTA"
                verdict_hint = f" | Modelo: {model_verdict} ({model_up:+.0f}% vs mercado)"
            st.caption(f"Orden {side.upper()} {qty} {sym} a mercado, {'PAPER' if paper else 'LIVE'}{verdict_hint}")
            st.caption("La orden se etiqueta con el veredicto del modelo para medir despues si seguirlo funciona.")

            confirm = st.checkbox("Entiendo que es una simulacion y quiero enviar esta orden", key="ord_confirm")
            if st.button("Enviar orden simulada", key="ord_send", disabled=not confirm):
                try:
                    tag = wallet_mod.make_order_tag(model_verdict, model_up)
                    res = wallet_mod.alpaca_place_order(akey, asec, sym, qty, side, paper=paper, client_order_id=tag)
                    st.success(f"Orden enviada. ID: {res.get('id', '?')} | estado: {res.get('status', '?')}")
                except wallet_mod.WalletError as e:
                    st.error(str(e))

            st.markdown("---")
            st.markdown("**Resultados de tus simulaciones** (¿seguir el modelo funciona?)")
            recent = wallet_mod.alpaca_recent_orders(akey, asec, paper=paper, limit=50)
            tagged = []
            for o in recent:
                v, up = wallet_mod.parse_order_tag(o.get("client_order_id", ""))
                if v:
                    tagged.append({
                        "Fecha": (o.get("submitted_at") or "")[:10],
                        "Simbolo": o.get("symbol"),
                        "Lado": o.get("side"),
                        "Cant": o.get("qty"),
                        "Veredicto modelo": v,
                        "Upside@entrada %": up,
                        "Estado": o.get("status"),
                    })
            if tagged:
                pos_by_sym = {}
                try:
                    for p in wallet_mod.alpaca_positions(akey, asec, paper=paper):
                        pos_by_sym[p.get("symbol")] = float(p.get("unrealized_plpc", 0)) * 100
                except wallet_mod.WalletError:
                    pass
                for t in tagged:
                    t["P&L actual %"] = round(pos_by_sym.get(t["Simbolo"], 0), 2)
                df = pd.DataFrame(tagged)
                st.dataframe(df, use_container_width=True, hide_index=True)
                aligned = [t for t in tagged if (t["Veredicto modelo"] == "BARATA" and t["Lado"] == "buy") or (t["Veredicto modelo"] == "CARA" and t["Lado"] == "sell")]
                if aligned:
                    avg = sum(t["P&L actual %"] for t in aligned) / len(aligned)
                    cc1, cc2 = st.columns(2)
                    cc1.metric("Operaciones alineadas con el modelo", len(aligned))
                    cc2.metric("P&L medio (alineadas)", f"{avg:+.2f}%")
                    st.caption(
                        "Operaciones donde compraste lo que el modelo decia BARATA o vendiste lo "
                        "CARA. Si el P&L medio es positivo de forma consistente con muchas operaciones, "
                        "la metodologia te esta aportando. Pocas operaciones aun no demuestran nada."
                    )
            else:
                st.info("Aun no hay ordenes simuladas etiquetadas. Envia alguna desde el analisis para empezar a medir.")

    # ---------- Polymarket ----------
    with sub[1]:
        st.caption(
            "Solo lectura. Pega la direccion publica de tu wallet (0x...). "
            "Esta app NUNCA pide ni maneja tu private key: ejecutar ordenes en Polymarket "
            "requiere firmar con la clave privada, y hacerlo desde una app web seria un riesgo "
            "de seguridad grave. Para operar usa la web oficial de Polymarket."
        )
        addr = st.text_input("Direccion wallet Polymarket (0x...)", key="pm_addr")
        if st.button("Ver posiciones Polymarket", key="pm_btn") and addr:
            try:
                pos = wallet_mod.polymarket_positions(addr)
                if not pos:
                    st.info("Sin posiciones o wallet sin actividad.")
                else:
                    rows = []
                    for p in pos[:50]:
                        rows.append({
                            "Mercado": str(p.get("title") or p.get("market") or "?")[:60],
                            "Resultado": p.get("outcome"),
                            "Tamano": p.get("size"),
                            "Valor actual": p.get("currentValue") or p.get("value"),
                            "P&L": p.get("cashPnl") or p.get("pnl"),
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            except wallet_mod.WalletError as e:
                st.error(str(e))


def _render_news_list(items):
    if not items:
        st.caption("Sin titulares recientes para este filtro.")
        return
    for a in items:
        dom = a.get("domain", "")
        date = a.get("date", "")
        title = a.get("title", "")
        url = a.get("url", "")
        st.markdown(
            f"""<div style="background-color:#181818;border-left:3px solid {SPOTIFY_GREEN};
            border-radius:5px;padding:0.6rem 0.9rem;margin-bottom:0.45rem;">
            <a href="{url}" target="_blank" style="color:#FFFFFF;font-weight:600;
            text-decoration:none;font-size:0.95rem;">{title}</a><br>
            <span style="color:#B3B3B3;font-size:0.78rem;">{dom} · {date}</span>
            </div>""",
            unsafe_allow_html=True,
        )


def render_news(inputs):
    st.markdown("### Monitor de noticias global")
    st.caption(
        "Agregador en tiempo casi real via GDELT (miles de medios mundiales, gratis). "
        "Mercados, macro, geopolitica y materias primas. No es un Bloomberg Terminal "
        "(sin datos propietarios ni precios en vivo): es un radar de titulares global."
    )
    if st.button("Actualizar titulares", key="news_refresh"):
        _cached_news.clear()
        st.rerun()

    cats = list(news_mod.CATEGORIES.items())
    company = (inputs or {}).get("company", "")
    tab_labels = [c[0] for c in cats]
    if company:
        tab_labels.append(f"Tu empresa: {company[:18]}")
    ntabs = st.tabs(tab_labels)
    for i, (name, query) in enumerate(cats):
        with ntabs[i]:
            try:
                _render_news_list(_cached_news(query))
            except news_mod.NewsError as e:
                st.warning(str(e))
    if company:
        with ntabs[-1]:
            try:
                q = f'"{company.split()[0]}" {inputs.get("ticker", "")}'.strip()
                _render_news_list(_cached_news(q, 14))
            except news_mod.NewsError as e:
                st.warning(str(e))
    st.caption("Titulares cacheados 10 min. Pulsa Actualizar para forzar refresco.")


def render_glossary():
    with st.expander("Diccionario: que significa cada termino"):
        for term, meaning in explanations.GLOSSARY.items():
            st.markdown(f"**{term}** — {meaning}")


def render_simple_verdict(inputs, scenarios):
    ccy = inputs["currency"]
    current = inputs["market_data"]["current_price_eur"]
    base_price = scenarios["base"]["dcf"]["implied_share_price"]
    bear_price = scenarios["bear"]["dcf"]["implied_share_price"]
    bull_price = scenarios["bull"]["dcf"]["implied_share_price"]
    upside = (base_price / current - 1) * 100 if current else 0
    tv_pct = scenarios["base"]["dcf"]["tv_pct_of_ev"]

    meta = scenarios.get("_meta") or {}
    badge, color, parrafo = explanations.verdict(upside, tv_pct, ccy, base_price, current, meta)

    # Audit fix: si DCF no aplica (banco/aseguradora/REIT/perdidas), mostrar SOLO el
    # aviso. Nada de precio objetivo ni escenarios: serian senales enganosas.
    if meta.get("dcf_applicable") is False:
        st.markdown(
            f"""
            <div style="background-color:#181818;border-radius:12px;padding:2rem;border:2px solid {color};margin-bottom:1rem;">
                <div style="color:{color};font-size:1.5rem;font-weight:900;">{badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.warning(parrafo)
        return False

    st.markdown(
        f"""
        <div style="background-color:#181818;border-radius:12px;padding:2rem;border:2px solid {color};margin-bottom:1.5rem;">
            <div style="color:{color};font-size:1.5rem;font-weight:900;letter-spacing:0.02em;">{badge}</div>
            <div style="display:flex;gap:2rem;margin:1.2rem 0;flex-wrap:wrap;">
                <div style="min-width:120px;">
                    <div style="color:#B3B3B3;font-size:0.8rem;text-transform:uppercase;">Precio hoy</div>
                    <div style="font-size:clamp(1.1rem,2vw,1.6rem);font-weight:700;color:#FFF;white-space:nowrap;">{ccy} {current:,.2f}</div>
                </div>
                <div style="min-width:120px;">
                    <div style="color:#B3B3B3;font-size:0.8rem;text-transform:uppercase;">Valor estimado</div>
                    <div style="font-size:clamp(1.1rem,2vw,1.6rem);font-weight:700;color:{color};white-space:nowrap;">{ccy} {base_price:,.2f}</div>
                </div>
                <div style="min-width:90px;">
                    <div style="color:#B3B3B3;font-size:0.8rem;text-transform:uppercase;">Potencial</div>
                    <div style="font-size:clamp(1.1rem,2vw,1.6rem);font-weight:700;color:{color};white-space:nowrap;">{upside:+.0f}%</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(parrafo)

    try:
        g1 = scenarios["base"]["projection"]["revenue"]
        hkeys = sorted(inputs["historical"].keys())
        base_rev = inputs["historical"][hkeys[-1]]["revenue"] if hkeys else 0
        y1_g = (g1[0] / base_rev - 1) * 100 if base_rev else 0
        st.info(
            f"Supuesto clave: este modelo asume que la empresa crece **{y1_g:+.0f}%** el "
            f"primer ano, anclado en su crecimiento historico reciente. Es deliberadamente "
            f"prudente. Si crees que va a **acelerar** (lanzamientos, nuevos mercados), "
            f"sube el slider de crecimiento en **Modo Experto** y recalcula: el valor cambia mucho."
        )
    except Exception:
        pass

    st.markdown("**Rango segun escenario:**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Si va mal (Pesimista)", f"{ccy} {bear_price:,.2f}", f"{(bear_price/current-1)*100:+.0f}%" if current else "")
    c2.metric("Lo mas probable (Base)", f"{ccy} {base_price:,.2f}", f"{upside:+.0f}%")
    c3.metric("Si va muy bien (Optimista)", f"{ccy} {bull_price:,.2f}", f"{(bull_price/current-1)*100:+.0f}%" if current else "")
    return True


def render_simple_sidebar():
    labels, lookup = load_companies()
    with st.sidebar:
        st.header("Elige una empresa")
        st.caption(f"{len(labels)} empresas. Escribe el nombre o el ticker para buscar.")
        default_target = next((l for l in labels if "(AAPL)" in l), labels[0] if labels else "")
        target_label = st.selectbox(
            "Empresa a analizar",
            options=labels,
            index=labels.index(default_target) if default_target in labels else 0,
            help="Por ejemplo: Apple, Inditex, Tesla. Escribe para filtrar.",
        )
        ticker = lookup.get(target_label, "AAPL")
        with st.expander("Otra empresa (ticker manual)"):
            custom = st.text_input("Ticker", value="", help="Si no esta en la lista. Ej: ITX.MC, NVDA")
            if custom.strip():
                ticker = custom.strip()
        analizar = st.button("Analizar", type="primary", use_container_width=True)
        return ticker, analizar


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


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch_company(ticker: str):
    """Cache 1h: a ticker fetched once is reused, dramatically cutting Yahoo calls
    and surviving rate-limit windows once data is in cache."""
    inputs = data_fetcher.fetch_company(ticker, peer_tickers=[])
    inputs.pop("peers_data", None)
    return inputs


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch_peers(peers_tuple: tuple, as_of: str):
    return data_fetcher.fetch_peers(list(peers_tuple), as_of)


def render_ticker_input():
    labels, lookup = load_companies()
    with st.sidebar:
        st.header("Empresa y comparables")
        st.caption(f"{len(labels)} empresas cotizadas en US, EU, Asia, LatAm. Escribe para buscar.")

        default_target = next((l for l in labels if "(AAPL)" in l), labels[0] if labels else "")
        # key= -> Streamlit persiste la seleccion entre reruns (fix scroll-revert).
        target_label = st.selectbox(
            "Empresa objetivo",
            options=labels,
            index=labels.index(default_target) if default_target in labels else 0,
            help="Busca por nombre o ticker.",
            key="sel_target",
        )
        ticker = lookup.get(target_label, "AAPL")

        default_peers_tickers = {"MSFT", "GOOGL", "META", "AMZN", "NFLX"}
        default_peers_labels = [l for l in labels if lookup.get(l) in default_peers_tickers]
        peer_labels = st.multiselect(
            "Empresas comparables",
            options=labels,
            default=default_peers_labels,
            help="Elige de 3 a 6 comparables. Busca por nombre o ticker.",
            key="sel_peers",
        )
        peers = [lookup[l] for l in peer_labels if l in lookup]

        manual_active = False
        with st.expander("Tickers personalizados (avanzado)"):
            st.caption("Si rellenas esto, IGNORA el desplegable de arriba y usa lo que escribas.")
            custom_target = st.text_input("Sobrescribir ticker objetivo", value="", help="Para empresas no listadas. Ej: ITX.MC", key="cust_t")
            custom_peers = st.text_input("Sobrescribir tickers comparables (coma)", value="", help="Ej: ITX.MC, HM-B.ST", key="cust_p")
            if custom_target.strip():
                ticker = custom_target.strip()
                manual_active = True
            if custom_peers.strip():
                peers = [t.strip() for t in custom_peers.split(",") if t.strip()]

        src = "manual (avanzado)" if manual_active else "desplegable"
        st.caption(f"Analizando: **{ticker}** (fuente: {src})")
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


def _abbr_m(v_millions, ccy):
    """Abbreviate a value already expressed in millions: 1_250_000 M -> 1.25T."""
    v = v_millions * 1_000_000
    a = abs(v)
    if a >= 1e12:
        s = f"{v/1e12:.2f}T"
    elif a >= 1e9:
        s = f"{v/1e9:.1f}B"
    elif a >= 1e6:
        s = f"{v/1e6:.0f}M"
    else:
        s = f"{v:,.0f}"
    return f"{ccy} {s}"


def render_market_data_summary(inputs):
    md = inputs["market_data"]
    ccy = inputs["currency"]
    nc = md["net_cash_eur_m"]
    nc_label = "Caja neta" if nc >= 0 else "Deuda neta"
    nc_val = _abbr_m(abs(nc), ccy)
    cols = st.columns(4)
    cols[0].metric("Precio", f"{ccy} {md['current_price_eur']:,.2f}")
    cols[1].metric("Capitalizacion", _abbr_m(md["market_cap_eur_m"], ccy))
    cols[2].metric(nc_label, nc_val)
    cols[3].metric("Valor empresa (EV)", _abbr_m(md["enterprise_value_eur_m"], ccy))


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


def render_historical_trend(inputs):
    ccy = inputs["currency"]
    hist = inputs["historical"]
    keys = sorted(hist.keys())
    if len(keys) < 2:
        st.info("Historico insuficiente para graficar tendencia.")
        return
    rev = [hist[k].get("revenue", 0) for k in keys]
    ebitda = [hist[k].get("ebitda", 0) for k in keys]
    fcf = [hist[k].get("fcf", 0) for k in keys]
    margin = [(e / r * 100) if r else 0 for e, r in zip(ebitda, rev)]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=keys, y=rev, name="Ingresos", marker_color=SPOTIFY_GREEN))
    fig.add_trace(go.Bar(x=keys, y=ebitda, name="EBITDA", marker_color="#1ED760"))
    fig.add_trace(go.Bar(x=keys, y=fcf, name="FCF", marker_color="#7CE3A4"))
    fig.add_trace(go.Scatter(x=keys, y=margin, name="Margen EBITDA %", yaxis="y2",
                             mode="lines+markers", line=dict(color="#E8C547", width=3)))
    _plotly_dark_layout(fig, f"Historico {len(keys)} anos ({ccy} M)")
    fig.update_layout(
        barmode="group", xaxis_title="Ano fiscal", yaxis_title=f"Importe ({ccy} M)",
        yaxis2=dict(title="Margen %", overlaying="y", side="right",
                    gridcolor=SPOTIFY_TERTIARY, color="#E8C547", range=[0, max(margin) * 1.4 if margin else 50]),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_waterfall(inputs, scenarios):
    ccy = inputs["currency"]
    d = scenarios["base"]["dcf"]
    nc = inputs["market_data"]["net_cash_eur_m"]
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative", "relative", "total", "relative", "total"],
        x=["VP Flujos<br>(Y1-Y10)", "VP Valor<br>Terminal", "Valor Empresa", "Caja - Deuda", "Valor Equity"],
        y=[round(d["sum_pv_fcf"]), round(d["pv_tv_blended"]), 0, round(nc), 0],
        text=[f"{ccy} {v:,.0f}M" for v in [d["sum_pv_fcf"], d["pv_tv_blended"], d["enterprise_value"], nc, d["equity_value"]]],
        textposition="outside",
        connector={"line": {"color": SPOTIFY_TEXT_MUTED}},
        increasing={"marker": {"color": SPOTIFY_GREEN}},
        decreasing={"marker": {"color": "#E84B4B"}},
        totals={"marker": {"color": "#1ED760"}},
    ))
    _plotly_dark_layout(fig, f"Puente de valoracion - de flujos a valor por accion ({ccy} M)")
    st.plotly_chart(fig, use_container_width=True)


def render_tornado(inputs, scenarios):
    ccy = inputs["currency"]
    current = inputs["market_data"].get("current_price_eur") or 0
    cases = [("Pesimista", "bear", "#E84B4B"), ("Base", "base", "#E8C547"), ("Optimista", "bull", SPOTIFY_GREEN)]
    fig = go.Figure()
    for label, key, color in cases:
        p = scenarios[key]["dcf"]["implied_share_price"]
        fig.add_trace(go.Bar(y=[label], x=[p], orientation="h", marker_color=color,
                             text=[f"{ccy} {p:,.2f}"], textposition="auto", name=label, showlegend=False))
    if current:
        fig.add_vline(x=current, line_dash="dash", line_color="#FFFFFF",
                      annotation_text=f"Mercado {ccy} {current:,.2f}", annotation_font_color="#FFFFFF")
    _plotly_dark_layout(fig, "Rango de valor por escenario vs precio de mercado")
    fig.update_layout(height=300, xaxis_title=f"Precio implicito ({ccy})")
    st.plotly_chart(fig, use_container_width=True)


def render_peers_scatter(inputs, peers_data):
    if not peers_data or len(peers_data) < 2:
        st.info("Anade comparables para ver el mapa de posicionamiento.")
        return
    xs, ys, sizes, names = [], [], [], []
    for p in peers_data:
        try:
            ev_ebitda = float(p.get("EV_EBITDA", 0))
            mgn = float(p.get("Operating_Margin_pct", 0))
            mcap = float(p.get("Market_Cap_LCY", 0))
        except (TypeError, ValueError):
            continue
        if ev_ebitda <= 0 or ev_ebitda > 80:
            continue
        xs.append(mgn)
        ys.append(ev_ebitda)
        sizes.append(max((mcap / 1e9) ** 0.5 * 3, 10))
        names.append(p.get("Company", "?"))
    if not xs:
        st.info("Datos de comparables insuficientes para el scatter.")
        return
    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="markers+text", text=names, textposition="top center",
        textfont=dict(color="#FFFFFF", size=10),
        marker=dict(size=sizes, color=ys, colorscale=[[0, "#1DB954"], [1, "#E84B4B"]],
                    showscale=True, colorbar=dict(title="EV/EBITDA"), line=dict(color="#FFFFFF", width=1)),
    ))
    _plotly_dark_layout(fig, "Mapa: margen operativo vs valoracion (tamano = capitalizacion)")
    fig.update_layout(xaxis_title="Margen operativo %", yaxis_title="EV / EBITDA (mas bajo = mas barato)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Abajo-derecha (alto margen, multiplo bajo) = mejor relacion calidad/precio relativo.")


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

    current = md.get("current_price_eur") or 0
    # Diverging colormap centered on TODAY's market price: rojo = sobrevalorado
    # (implied < precio), blanco ~ justo, verde = infravalorado (implied > precio).
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=[f"{w:.1f}%" for w in wacc_range],
        y=[f"{tg:.1f}%" for tg in tg_range],
        colorscale=[[0, "#E84B4B"], [0.5, "#E8E0C8"], [1, "#1DB954"]],
        zmid=current if current else None,
        text=[[f"{v:,.0f}" if v is not None else "" for v in row] for row in matrix],
        texttemplate="%{text}",
        hovertemplate="WACC: %{x}<br>g Terminal: %{y}<br>Implicito: %{z:.2f}<extra></extra>",
        colorbar=dict(title="Precio<br>implicito"),
    ))
    _plotly_dark_layout(fig, "Sensibilidad: Precio implicito vs WACC y Crecimiento Terminal")
    fig.update_layout(xaxis_title="WACC", yaxis_title="Crecimiento Terminal")
    st.plotly_chart(fig, use_container_width=True)
    if current:
        st.caption(
            f"Rojo = implicito por debajo del precio de mercado ({inputs['currency']} {current:,.2f}, sobrevalorado). "
            f"Verde = por encima (infravalorado). Centro claro = precio justo."
        )


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


def run_simple_mode():
    ticker, analizar = render_simple_sidebar()
    with st.sidebar:
        st.markdown("---")
        st.caption("Modo Simple activo. Cambia a Experto arriba para ajustar supuestos.")

    if analizar:
        with st.spinner(f"Buscando datos reales de {ticker}..."):
            try:
                inputs = cached_fetch_company(ticker)
                st.session_state.inputs = inputs
                st.session_state.peers_data = None
                st.session_state.scenarios = None
            except data_fetcher.TickerNotFound:
                st.error(
                    f"**El ticker '{ticker}' no existe** en la fuente de datos. "
                    "Revisa el simbolo o anade sufijo de bolsa (.MC Espana, .L Londres, .T Tokio, .KS Corea)."
                )
                return
            except data_fetcher.RateLimited:
                st.error(
                    "**La fuente de datos esta limitando peticiones ahora mismo.** "
                    "Espera 1-2 minutos y pulsa Analizar otra vez. Una vez cargada, la empresa queda en cache 1h."
                )
                return
            except Exception as e:
                st.error(f"No pude cargar {ticker}: tipo {type(e).__name__}. Prueba otro ticker o sufijo de bolsa (.MC, .L, .T, .KS).")
                return

    if st.session_state.inputs is None:
        st.info("Elige una empresa en la barra de la izquierda y pulsa **Analizar**.")
        st.markdown(explanations.HOW_IT_WORKS)
        render_glossary()
        st.markdown("---")
        st.markdown(explanations.DISCLAIMER_SIMPLE)
        return

    inputs = st.session_state.inputs
    try:
        scenarios = compute_dcf.run_all(inputs)
    except Exception as e:
        st.error(f"Error calculando: {e}")
        return
    st.session_state.scenarios = scenarios

    st.header(f"{inputs['company']} ({inputs['ticker']})")
    render_warnings(inputs)
    applicable = render_simple_verdict(inputs, scenarios)

    if applicable is not False:
        st.markdown("---")
        render_insights(inputs, scenarios, None)
        st.markdown("---")

        with st.expander("Como llegamos a esta estimacion"):
            st.markdown(explanations.HOW_IT_WORKS)
            st.markdown("**Resumen de la cuenta (Caso Base):**")
            d = scenarios["base"]["dcf"]
            ccy = inputs["currency"]
            bridge = pd.DataFrame({
                "Concepto": ["Dinero futuro (anos 1-10) a valor de hoy", "Valor mas alla del ano 10", "= Valor del negocio", "+ Caja - Deuda", "= Valor para accionistas"],
                f"{ccy} M": [round(d["sum_pv_fcf"]), round(d["pv_tv_blended"]), round(d["enterprise_value"]), round(inputs["market_data"]["net_cash_eur_m"]), round(d["equity_value"])],
            })
            st.dataframe(bridge, use_container_width=True, hide_index=True)

    render_glossary()

    with st.expander("Fiabilidad de estos datos"):
        st.markdown(explanations.reliability_note(inputs))

    st.markdown("---")
    st.markdown(explanations.DISCLAIMER_SIMPLE)
    st.caption("Construido con skills de Anthropic financial-services (Apache 2.0).")


def run_expert_mode():
    ticker, peers, fetch = render_ticker_input()

    if fetch:
        with st.spinner(f"Cargando {ticker} + {len(peers)} comparables..."):
            try:
                inputs = cached_fetch_company(ticker)
                peers_data = cached_fetch_peers(tuple(peers), inputs["as_of_date"]) if peers else []
                st.session_state.inputs = inputs
                st.session_state.peers_data = peers_data
                st.session_state.scenarios = None
                rl_peers = sum(1 for p in peers_data if p.get("_error") == "rate_limited")
                msg = f"Cargado {inputs['company']} ({ticker}) + {len(peers_data)} comparables"
                if rl_peers:
                    msg += f" ({rl_peers} peers sin datos por rate-limit, reintenta luego)"
                st.success(msg)
            except data_fetcher.TickerNotFound:
                st.error(
                    f"**El ticker '{ticker}' no existe** en la fuente de datos. "
                    "Revisa el simbolo o anade sufijo de bolsa (.MC, .L, .T, .KS)."
                )
                return
            except data_fetcher.RateLimited:
                st.error(
                    "**La fuente de datos esta limitando peticiones.** "
                    "Espera 1-2 min y reintenta. Tras cargar, queda en cache 1h."
                )
                return
            except Exception as e:
                st.error(f"Error en carga de datos: tipo {type(e).__name__}.")
                return

    if st.session_state.inputs is None:
        st.info("Selecciona empresa objetivo y comparables en la barra lateral, despues **Cargar datos**.")
        st.markdown("---")
        st.markdown(explanations.HOW_IT_WORKS)
        render_glossary()
        st.markdown(explanations.DISCLAIMER_SIMPLE)
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
    applicable = render_simple_verdict(inputs, scenarios)
    st.markdown("---")
    render_market_data_summary(inputs)

    if applicable is False:
        with st.expander("Diccionario: que significa cada termino"):
            for term, meaning in explanations.GLOSSARY.items():
                st.markdown(f"**{term}** - {meaning}")
        st.markdown("---")
        st.markdown(explanations.DISCLAIMER_SIMPLE)
        return

    st.markdown("### Escenarios de valoracion")
    render_scenario_cards(inputs, scenarios)

    tabs = st.tabs(["Insights", "Resumen", "Proyeccion", "Sensibilidad", "Comparables", "Historicos", "Descargas", "Mi Cartera", "Noticias", "Diccionario"])

    with tabs[0]:
        render_insights(inputs, scenarios, peers_data)

    with tabs[1]:
        render_waterfall(inputs, scenarios)
        render_tornado(inputs, scenarios)
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
                "(+) Caja - (-) Deuda neta",
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

    with tabs[2]:
        render_projection_chart(inputs, scenarios)
        st.markdown("**Tabla detallada de proyeccion**")
        render_projection_table(scenarios)

    with tabs[3]:
        render_sensitivity_heatmap(inputs, scenarios)
        st.caption(
            "Precio implicito a cada combinacion de WACC y crecimiento terminal. "
            "Mantiene FCFs explicitos al WACC base; solo varia el terminal."
        )

    with tabs[4]:
        st.markdown("**Empresas comparables**")
        render_peers_scatter(inputs, peers_data)
        render_comps_table(peers_data)

    with tabs[5]:
        st.markdown("**Financieros historicos (ultimos 5 anos disponibles)**")
        render_historical_trend(inputs)
        render_historicals_table(inputs)

    with tabs[6]:
        st.markdown("**Descargar deliverables**")
        render_downloads(inputs, scenarios, peers_data)

    with tabs[7]:
        render_wallet(inputs)

    with tabs[8]:
        render_news(inputs)

    with tabs[9]:
        for term, meaning in explanations.GLOSSARY.items():
            st.markdown(f"**{term}** — {meaning}")
        st.markdown("---")
        st.markdown(explanations.reliability_note(inputs))

    st.markdown("---")
    st.caption(
        "NO ES ASESORAMIENTO FINANCIERO. Herramienta educativa. Verificar contra reporte anual oficial. "
        "Construido con skills de Anthropic financial-services (Apache 2.0)."
    )


def main():
    init_state()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    render_header()
    st.caption(f":warning: {explanations.DISCLAIMER_BANNER}")

    col1, col2 = st.columns([2, 3])
    with col1:
        modo = st.radio(
            "Modo",
            options=["Simple", "Experto"],
            horizontal=True,
            label_visibility="collapsed",
            help="Simple: elige empresa y listo. Experto: ajusta WACC, escenarios, comparables.",
        )
    if modo != st.session_state.get("modo_prev"):
        st.session_state.inputs = None
        st.session_state.scenarios = None
        st.session_state.modo_prev = modo

    st.markdown("---")

    if modo == "Simple":
        run_simple_mode()
    else:
        run_expert_mode()


if __name__ == "__main__":
    main()
