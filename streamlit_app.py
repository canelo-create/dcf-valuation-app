"""Equity Valuation Web App — DCF + Comps for any listed company.

Built on Anthropic financial-services skills (Apache 2.0).

Deploy on Streamlit Cloud:
  1. Push repo to GitHub
  2. Connect Streamlit Cloud to repo
  3. Set main file: streamlit_app.py

Run locally (requires pyarrow which lacks Win ARM64 wheels):
  pip install -r requirements.txt
  streamlit run streamlit_app.py
"""

import io
import json
from copy import deepcopy

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
    page_title="Equity Valuation Toolkit",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)


def init_state():
    if "inputs" not in st.session_state:
        st.session_state.inputs = None
    if "peers_data" not in st.session_state:
        st.session_state.peers_data = None
    if "scenarios" not in st.session_state:
        st.session_state.scenarios = None


def render_header():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Equity Valuation Toolkit")
        st.caption("DCF + Comparable Company Analysis for any listed company. Powered by Anthropic financial-services skills (Apache 2.0).")
    with col2:
        st.markdown(
            """
            [![GitHub](https://img.shields.io/badge/GitHub-Source-181717?logo=github)](https://github.com)
            [Anthropic FSI](https://github.com/anthropics/financial-services)
            """,
            unsafe_allow_html=True,
        )


def render_ticker_input():
    with st.sidebar:
        st.header("1. Target & Peers")
        ticker = st.text_input("Target ticker", value="AAPL", help="e.g. AAPL, MSFT, ITX.MC, 9983.T")
        peers_raw = st.text_input(
            "Peer tickers (comma-separated)",
            value="MSFT,GOOG,META,AMZN,NFLX",
            help="3 to 6 listed peers in same industry",
        )
        peers = [t.strip() for t in peers_raw.split(",") if t.strip()]
        fetch = st.button("Fetch data", type="primary", use_container_width=True)
        return ticker, peers, fetch


def render_wacc_controls(inputs):
    with st.sidebar:
        st.header("2. WACC")
        wacc_d = inputs["wacc"]
        rf = st.number_input("Risk-free rate (%)", min_value=0.0, max_value=15.0, value=float(wacc_d["risk_free_rate_pct"]), step=0.1)
        erp = st.number_input("Equity risk premium (%)", min_value=3.0, max_value=15.0, value=float(wacc_d["equity_risk_premium_pct"]), step=0.1)
        beta = st.number_input("Beta (5Y)", min_value=0.0, max_value=3.0, value=float(wacc_d["beta"]), step=0.05)
        tax = st.number_input("Tax rate (%)", min_value=0.0, max_value=40.0, value=float(wacc_d["tax_rate_pct"]), step=1.0)

        cost_of_equity = rf + beta * erp
        st.metric("Cost of equity (CAPM)", f"{cost_of_equity:.2f}%")
        wacc = cost_of_equity
        st.metric("WACC (all-equity simplification)", f"{wacc:.2f}%")

        wacc_d["risk_free_rate_pct"] = rf
        wacc_d["equity_risk_premium_pct"] = erp
        wacc_d["beta"] = beta
        wacc_d["tax_rate_pct"] = tax
        wacc_d["cost_of_equity_pct"] = round(cost_of_equity, 2)
        wacc_d["wacc_pct"] = round(wacc, 2)
        return inputs


def render_scenario_controls(inputs, scenario_key):
    label = scenario_key.title()
    with st.expander(f"{label} case assumptions", expanded=(scenario_key == "base")):
        a = inputs[f"projection_assumptions_{scenario_key}"]
        y1_growth = st.slider(f"{label}: Y1 revenue growth (%)", -10.0, 30.0, float(a["revenue_growth_yoy_pct"][0]), 0.5, key=f"{scenario_key}_y1g")
        y10_growth = st.slider(f"{label}: Y10 revenue growth (%)", -5.0, 15.0, float(a["revenue_growth_yoy_pct"][-1]), 0.5, key=f"{scenario_key}_y10g")
        margin_stable = st.slider(f"{label}: EBITDA margin (%)", 5.0, 50.0, float(a["ebitda_margin_pct"][0]), 0.5, key=f"{scenario_key}_mgn")
        terminal_g = st.slider(f"{label}: Terminal growth (%)", 0.0, 5.0, float(a["terminal_growth_pct"]), 0.1, key=f"{scenario_key}_tg")
        exit_mult = st.slider(f"{label}: Exit multiple (EV/EBITDA)", 4.0, 25.0, float(a["exit_multiple_ev_ebitda"]), 0.5, key=f"{scenario_key}_em")

        a["revenue_growth_yoy_pct"] = list(_interp_decay(y1_growth, y10_growth, 10))
        a["ebitda_margin_pct"] = [margin_stable] * 10
        a["terminal_growth_pct"] = terminal_g
        a["exit_multiple_ev_ebitda"] = exit_mult
    return inputs


def _interp_decay(start, end, n):
    """Linear interpolation start -> end across n periods."""
    if n <= 1:
        return [start]
    step = (end - start) / (n - 1)
    return [round(start + i * step, 2) for i in range(n)]


def render_market_data_summary(inputs):
    md = inputs["market_data"]
    ccy = inputs["currency"]
    cols = st.columns(4)
    cols[0].metric("Price", f"{ccy} {md['current_price_eur']:.2f}")
    cols[1].metric("Market cap", f"{ccy} {md['market_cap_eur_m']:,.0f}M")
    cols[2].metric("Net cash / (debt)", f"{ccy} {md['net_cash_eur_m']:,.0f}M")
    cols[3].metric("Enterprise value", f"{ccy} {md['enterprise_value_eur_m']:,.0f}M")


def render_scenario_cards(inputs, scenarios):
    ccy = inputs["currency"]
    current = inputs["market_data"]["current_price_eur"]
    cols = st.columns(3)
    for i, case in enumerate(["bear", "base", "bull"]):
        s = scenarios[case]["dcf"]
        upside = (s["implied_share_price"] / current - 1) * 100 if current else 0
        delta_color = "normal" if abs(upside) < 5 else ("inverse" if upside < 0 else "normal")
        with cols[i]:
            st.metric(
                label=f"{case.upper()} implied",
                value=f"{ccy} {s['implied_share_price']:.2f}",
                delta=f"{upside:+.1f}% vs market",
            )


def render_projection_chart(inputs, scenarios):
    ccy = inputs["currency"]
    proj = scenarios["base"]["projection"]
    years = [f"Y{y}" for y in proj["years"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=years, y=proj["revenue"], name="Revenue", marker_color="#1F4E79"))
    fig.add_trace(go.Bar(x=years, y=proj["ebitda"], name="EBITDA", marker_color="#5B9BD5"))
    fig.add_trace(go.Bar(x=years, y=proj["fcf"], name="FCF (Unlevered)", marker_color="#70AD47"))
    fig.add_trace(go.Scatter(x=years, y=proj["pv_fcf"], name="PV of FCF", mode="lines+markers", line=dict(color="#C00000", width=3)))
    fig.update_layout(
        title=f"10-Year Projection — Base Case ({ccy} M)",
        xaxis_title="Projection year",
        yaxis_title=f"Amount ({ccy} M)",
        barmode="group",
        height=400,
    )
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
        colorscale="RdYlGn",
        text=[[f"{v:.1f}" if v is not None else "" for v in row] for row in matrix],
        texttemplate="%{text}",
        hovertemplate="WACC: %{x}<br>Terminal g: %{y}<br>Implied: %{z:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title="Sensitivity: Implied Share Price vs WACC and Terminal Growth",
        xaxis_title="WACC",
        yaxis_title="Terminal Growth",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_historicals_table(inputs):
    hist = inputs["historical"]
    fy_keys = sorted(hist.keys())
    rows = []
    for label, key in [("Revenue", "revenue"), ("EBITDA", "ebitda"), ("EBIT", "ebit"), ("D&A", "da"), ("CapEx", "capex"), ("FCF", "fcf"), ("Net Income", "net_income")]:
        rows.append({"Metric": label, **{fy: hist[fy].get(key, 0) for fy in fy_keys}})
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_projection_table(scenarios):
    base = scenarios["base"]["projection"]
    df = pd.DataFrame({
        "Year": [f"Y{y}" for y in base["years"]],
        "Revenue": [round(v) for v in base["revenue"]],
        "EBITDA": [round(v) for v in base["ebitda"]],
        "EBIT": [round(v) for v in base["ebit"]],
        "FCF": [round(v) for v in base["fcf"]],
        "Discount Factor": [round(v, 4) for v in base["pv_factor"]],
        "PV of FCF": [round(v) for v in base["pv_fcf"]],
    })
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_comps_table(peers_data):
    if not peers_data:
        st.info("No peer data fetched. Add peer tickers in sidebar and re-fetch.")
        return
    df = pd.DataFrame(peers_data)
    display_cols = ["Company", "Ticker", "Currency", "Revenue_TTM_LCY", "EBITDA_TTM_LCY", "EV_Sales", "EV_EBITDA", "PE_Trailing", "Beta_5Y"]
    display_df = df[display_cols].copy()
    display_df["Revenue_TTM_LCY"] = (display_df["Revenue_TTM_LCY"] / 1_000_000).round().astype(int)
    display_df["EBITDA_TTM_LCY"] = (display_df["EBITDA_TTM_LCY"] / 1_000_000).round().astype(int)
    display_df = display_df.rename(columns={
        "Revenue_TTM_LCY": "Revenue (M LCY)",
        "EBITDA_TTM_LCY": "EBITDA (M LCY)",
        "EV_Sales": "EV/Sales",
        "EV_EBITDA": "EV/EBITDA",
        "PE_Trailing": "P/E (TTM)",
        "Beta_5Y": "Beta",
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Stats
    st.markdown("**Multiples statistics (peers only)**")
    nums = pd.DataFrame(peers_data)[["EV_Sales", "EV_EBITDA", "PE_Trailing"]].apply(pd.to_numeric, errors="coerce")
    stats = pd.DataFrame({
        "EV/Sales": [nums["EV_Sales"].max(), nums["EV_Sales"].quantile(0.75), nums["EV_Sales"].median(), nums["EV_Sales"].quantile(0.25), nums["EV_Sales"].min()],
        "EV/EBITDA": [nums["EV_EBITDA"].max(), nums["EV_EBITDA"].quantile(0.75), nums["EV_EBITDA"].median(), nums["EV_EBITDA"].quantile(0.25), nums["EV_EBITDA"].min()],
        "P/E TTM": [nums["PE_Trailing"].max(), nums["PE_Trailing"].quantile(0.75), nums["PE_Trailing"].median(), nums["PE_Trailing"].quantile(0.25), nums["PE_Trailing"].min()],
    }, index=["Max", "75th Pct", "Median", "25th Pct", "Min"])
    st.dataframe(stats.round(2), use_container_width=True)


def render_downloads(inputs, scenarios, peers_data):
    company = inputs["company"]
    safe_name = company.replace(" ", "_").replace(".", "").lower()

    # DCF xlsx
    dcf_wb = build_dcf_xlsx.build_workbook(inputs)
    dcf_buffer = io.BytesIO()
    dcf_wb.save(dcf_buffer)
    dcf_buffer.seek(0)

    # Comps xlsx (if peers)
    comps_buffer = None
    if peers_data:
        comps_wb = build_comps.build_workbook(inputs, peers_data)
        comps_buffer = io.BytesIO()
        comps_wb.save(comps_buffer)
        comps_buffer.seek(0)

    # Memo
    memo = memo_generator.generate_memo(inputs, scenarios, peers_data)

    # Inputs JSON
    inputs_json = json.dumps(inputs, indent=2, default=str)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.download_button("DCF model (.xlsx)", data=dcf_buffer, file_name=f"{safe_name}_dcf.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with col2:
        if comps_buffer:
            st.download_button("Comps (.xlsx)", data=comps_buffer, file_name=f"{safe_name}_comps.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.button("Comps (.xlsx)", disabled=True, help="Add peers in sidebar first")
    with col3:
        st.download_button("Memo (.md)", data=memo, file_name=f"{safe_name}_analysis.md", mime="text/markdown")
    with col4:
        st.download_button("Inputs (.json)", data=inputs_json, file_name=f"{safe_name}_inputs.json", mime="application/json")


def render_warnings(inputs):
    md = inputs["market_data"]
    hist_keys = sorted(inputs["historical"].keys())
    latest = inputs["historical"][hist_keys[-1]] if hist_keys else None

    if not md["current_price_eur"]:
        st.warning("Current price is zero. Verify ticker is correct.")
    if not md["market_cap_eur_m"]:
        st.warning("Market cap is zero. Data may be incomplete.")
    if not latest or latest["revenue"] == 0:
        st.error("Could not fetch revenue history. Check ticker spelling or try a different exchange suffix (e.g. .L, .MC, .T).")


def main():
    init_state()
    render_header()
    ticker, peers, fetch = render_ticker_input()

    if fetch:
        with st.spinner(f"Fetching {ticker} + {len(peers)} peers..."):
            try:
                inputs = data_fetcher.fetch_company(ticker, peer_tickers=peers)
                peers_data = inputs.pop("peers_data", None) if "peers_data" in inputs else data_fetcher.fetch_peers(peers, inputs["as_of_date"])
                st.session_state.inputs = inputs
                st.session_state.peers_data = peers_data
                st.session_state.scenarios = None
                st.success(f"Fetched {inputs['company']} ({ticker}) + {len(peers_data)} peers")
            except Exception as e:
                st.error(f"Fetch failed: {e}")
                return

    if st.session_state.inputs is None:
        st.info("Enter a target ticker and peer list in the sidebar, then click **Fetch data**.")
        st.markdown("---")
        st.markdown(
            """
            ### What this app does
            1. Pulls 5Y historicals + current market data via Yahoo Finance
            2. Builds a 10-year unlevered FCF projection (Bear / Base / Bull)
            3. Discounts at WACC via CAPM
            4. Blended terminal value (perpetuity growth + exit multiple)
            5. Cross-checks against 3 to 5 listed peers
            6. Exports institutional-grade xlsx + memo

            ### Disclaimer
            NOT INVESTMENT ADVICE. Educational tool. Verify against company annual report. Past performance does not predict future results.

            ### Powered by
            [Anthropic financial-services](https://github.com/anthropics/financial-services) (Apache 2.0). DCF, comps, and audit skill methodology.
            """
        )
        return

    inputs = st.session_state.inputs
    peers_data = st.session_state.peers_data

    # Sidebar controls
    inputs = render_wacc_controls(inputs)

    with st.sidebar:
        st.header("3. Scenarios")
    for scen in ["bear", "base", "bull"]:
        with st.sidebar:
            inputs = render_scenario_controls(inputs, scen)

    # Compute scenarios
    try:
        scenarios = compute_dcf.run_all(inputs)
    except Exception as e:
        st.error(f"DCF compute failed: {e}")
        return
    st.session_state.scenarios = scenarios

    # Main panel
    company = inputs["company"]
    ticker = inputs["ticker"]
    st.header(f"{company} ({ticker})")

    render_warnings(inputs)
    render_market_data_summary(inputs)

    st.markdown("### Valuation scenarios")
    render_scenario_cards(inputs, scenarios)

    tabs = st.tabs(["Overview", "Projection", "Sensitivity", "Comps", "Historicals", "Downloads"])

    with tabs[0]:
        st.markdown(f"**Base case implied price: {inputs['currency']} {scenarios['base']['dcf']['implied_share_price']:.2f}**")
        upside = (scenarios["base"]["dcf"]["implied_share_price"] / inputs["market_data"]["current_price_eur"] - 1) * 100
        st.markdown(f"**Upside vs market: {upside:+.1f}%**")
        st.markdown("---")
        st.markdown("**Valuation bridge (Base case)**")
        bridge_data = {
            "Component": ["Sum PV(FCF) Y1-Y10", "PV Terminal Value", "(=) Enterprise Value", "(+) Net Cash", "(=) Equity Value"],
            "Value": [
                scenarios["base"]["dcf"]["sum_pv_fcf"],
                scenarios["base"]["dcf"]["pv_tv_blended"],
                scenarios["base"]["dcf"]["enterprise_value"],
                inputs["market_data"]["net_cash_eur_m"],
                scenarios["base"]["dcf"]["equity_value"],
            ],
        }
        bridge_df = pd.DataFrame(bridge_data)
        bridge_df["Value"] = bridge_df["Value"].round(0).astype(int)
        st.dataframe(bridge_df, use_container_width=True, hide_index=True)
        tv_pct = scenarios["base"]["dcf"]["tv_pct_of_ev"]
        if 50 <= tv_pct <= 70:
            st.success(f"Sanity check: Terminal % of EV = {tv_pct:.1f}% (within 50-70% acceptable band)")
        else:
            st.warning(f"Sanity check: Terminal % of EV = {tv_pct:.1f}% (OUTSIDE 50-70% typical range)")

    with tabs[1]:
        render_projection_chart(inputs, scenarios)
        st.markdown("**Detailed projection table**")
        render_projection_table(scenarios)

    with tabs[2]:
        render_sensitivity_heatmap(inputs, scenarios)
        st.caption(
            "Implied share price at each combination of WACC and terminal growth rate. "
            "Holds explicit FCFs constant at base WACC; varies only terminal."
        )

    with tabs[3]:
        st.markdown("**Peer companies**")
        render_comps_table(peers_data)

    with tabs[4]:
        st.markdown("**Historical financials (last 5 fiscal years available)**")
        render_historicals_table(inputs)

    with tabs[5]:
        st.markdown("**Download analysis deliverables**")
        render_downloads(inputs, scenarios, peers_data)

    st.markdown("---")
    st.caption(
        "NOT INVESTMENT ADVICE. Educational tool. Verify against official annual report. "
        "Built on Anthropic financial-services skills (Apache 2.0)."
    )


if __name__ == "__main__":
    main()
