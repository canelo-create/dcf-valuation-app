"""Generate dcf-analysis.md memo from inputs + scenarios."""

from typing import Optional


def generate_memo(inputs: dict, scenarios: dict, peers_data: Optional[list] = None) -> str:
    company = inputs["company"]
    ticker = inputs["ticker"]
    ccy = inputs["currency"]
    as_of = inputs["as_of_date"]
    md = inputs["market_data"]
    wacc_d = inputs["wacc"]
    current = md["current_price_eur"]

    base = scenarios["base"]
    bear = scenarios["bear"]
    bull = scenarios["bull"]

    base_price = base["dcf"]["implied_share_price"]
    bear_price = bear["dcf"]["implied_share_price"]
    bull_price = bull["dcf"]["implied_share_price"]
    upside_base = (base_price / current - 1) * 100 if current else 0
    upside_bear = (bear_price / current - 1) * 100 if current else 0
    upside_bull = (bull_price / current - 1) * 100 if current else 0
    tv_pct = base["dcf"]["tv_pct_of_ev"]

    recommendation = _recommend(upside_base, tv_pct, current, base_price)

    lines = [
        f"# {company} ({ticker}) DCF Valuation",
        "",
        f"**As of {as_of}** | Methodology: 10-year explicit Unlevered FCF projection, blended terminal (perpetuity growth + exit multiple). All figures {ccy}.",
        "",
        "## Executive Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Current share price | {ccy} {current:.2f} |",
        f"| Base case implied price | {ccy} {base_price:.2f} |",
        f"| **Upside vs market** | **{upside_base:+.1f}%** |",
        f"| Bear case implied | {ccy} {bear_price:.2f} ({upside_bear:+.1f}%) |",
        f"| Bull case implied | {ccy} {bull_price:.2f} ({upside_bull:+.1f}%) |",
        f"| WACC | {wacc_d['wacc_pct']:.2f}% |",
        f"| Terminal % of EV | {tv_pct:.1f}% ({'within' if 50 <= tv_pct <= 70 else 'OUTSIDE'} 50-70% sanity band) |",
        "",
        f"**Recommendation:** {recommendation}",
        "",
        "## Methodology",
        "",
        "### Historical financials",
        "",
        "| Metric | " + " | ".join(sorted(inputs["historical"].keys())) + " |",
        "|---|" + "---:|" * len(inputs["historical"]),
    ]
    fy_keys = sorted(inputs["historical"].keys())
    for label, key in [("Revenue", "revenue"), ("EBITDA", "ebitda"), ("EBIT", "ebit"), ("D&A", "da"), ("CapEx", "capex"), ("FCF", "fcf")]:
        row = f"| {label} | " + " | ".join(f"{inputs['historical'][fy].get(key, 0):,}" for fy in fy_keys) + " |"
        lines.append(row)
    lines.append("")

    lines.extend([
        "### WACC build (CAPM)",
        "",
        "| Component | Value | Source |",
        "|---|---:|---|",
        f"| Risk-free rate | {wacc_d['risk_free_rate_pct']:.2f}% | {wacc_d['risk_free_source']} |",
        f"| Equity risk premium | {wacc_d['equity_risk_premium_pct']:.2f}% | {wacc_d['erp_source']} |",
        f"| Beta (5Y) | {wacc_d['beta']:.2f} | yfinance |",
        f"| **Cost of equity** | **{wacc_d['cost_of_equity_pct']:.2f}%** | Rf + Beta * ERP |",
        f"| Tax rate | {wacc_d['tax_rate_pct']:.1f}% | |",
        f"| **WACC** | **{wacc_d['wacc_pct']:.2f}%** | Applied to all scenarios |",
        "",
        f"Net position: {ccy} {md['net_cash_eur_m']:,}M {'(net cash)' if md['net_cash_eur_m'] > 0 else '(net debt)'}.",
        "",
        "### Projection (Base case, 10Y explicit)",
        "",
        "| Year | " + " | ".join(f"Y{y}" for y in range(1, 11)) + " |",
        "|---|" + "---:|" * 10,
    ])

    proj = base["projection"]
    base_rev = inputs["historical"][fy_keys[-1]]["revenue"]
    growth_row = "| Growth % |"
    prev = base_rev
    for r in proj["revenue"]:
        g = (r / prev - 1) * 100 if prev else 0
        growth_row += f" {g:+.1f}% |"
        prev = r
    lines.append(growth_row)
    lines.append("| Revenue | " + " | ".join(f"{r:,.0f}" for r in proj["revenue"]) + " |")
    lines.append("| EBITDA | " + " | ".join(f"{e:,.0f}" for e in proj["ebitda"]) + " |")
    lines.append("| FCF | " + " | ".join(f"{f:,.0f}" for f in proj["fcf"]) + " |")
    lines.append("| PV(FCF) | " + " | ".join(f"{p:,.0f}" for p in proj["pv_fcf"]) + " |")
    lines.append("")

    lines.extend([
        "### Terminal value",
        "",
        "| Method | Gross TV | PV TV |",
        "|---|---:|---:|",
        f"| Perpetuity growth ({base['tg']:.1f}%) | {base['dcf']['tv_perpetuity']:,.0f} | {base['dcf']['pv_tv_perpetuity']:,.0f} |",
        f"| Exit multiple ({base['em']:.1f}x EBITDA Y10) | {base['dcf']['tv_exit_multiple']:,.0f} | {base['dcf']['pv_tv_exit']:,.0f} |",
        f"| **Blended PV** | | **{base['dcf']['pv_tv_blended']:,.0f}** |",
        "",
        "### Valuation summary",
        "",
        "| Component | Value |",
        "|---|---:|",
        f"| Sum PV of explicit FCFs (Y1-Y10) | {ccy} {base['dcf']['sum_pv_fcf']:,.0f}M |",
        f"| PV of Terminal value | {ccy} {base['dcf']['pv_tv_blended']:,.0f}M |",
        f"| **Enterprise Value** | **{ccy} {base['dcf']['enterprise_value']:,.0f}M** |",
        f"| (+) Net cash | {ccy} {md['net_cash_eur_m']:,}M |",
        f"| **Equity Value** | **{ccy} {base['dcf']['equity_value']:,.0f}M** |",
        f"| (/) Shares outstanding (M) | {md['shares_outstanding_m']:,} |",
        f"| **Implied share price** | **{ccy} {base_price:.2f}** |",
        "",
        "## Scenarios",
        "",
        "| Scenario | Terminal g | Exit mult | Implied price | Upside |",
        "|---|---:|---:|---:|---:|",
        f"| Bear | {bear['tg']:.1f}% | {bear['em']:.1f}x | {ccy} {bear_price:.2f} | {upside_bear:+.1f}% |",
        f"| **Base** | **{base['tg']:.1f}%** | **{base['em']:.1f}x** | **{ccy} {base_price:.2f}** | **{upside_base:+.1f}%** |",
        f"| Bull | {bull['tg']:.1f}% | {bull['em']:.1f}x | {ccy} {bull_price:.2f} | {upside_bull:+.1f}% |",
        "",
    ])

    if peers_data:
        lines.extend([
            "## Comps cross-check",
            "",
            "Peer multiples (TTM):",
            "",
            "| Company | EV/Sales | EV/EBITDA | P/E (TTM) |",
            "|---|---:|---:|---:|",
        ])
        for p in peers_data:
            lines.append(
                f"| {p['Company']} | {p.get('EV_Sales', 0):.2f}x | {p.get('EV_EBITDA', 0):.2f}x | {p.get('PE_Trailing', 0):.2f}x |"
            )
        lines.append("")

    lines.extend([
        "## Sanity checks",
        "",
        f"- Terminal % of EV: {tv_pct:.1f}% ({'PASS' if 50 <= tv_pct <= 70 else 'FLAG - outside typical 50-70% range'})",
        f"- Bear/Bull spread: {abs(upside_bull - upside_bear):.0f}pp ({'reasonable' if 50 <= abs(upside_bull - upside_bear) <= 150 else 'flag - check assumptions'})",
        f"- WACC: {wacc_d['wacc_pct']:.2f}% ({'reasonable' if 6 <= wacc_d['wacc_pct'] <= 15 else 'verify'})",
        "",
        "## Limitations",
        "",
        "1. Data sourced via yfinance API. Verify against company official annual report for production deliverable.",
        "2. Sensitivity tables in xlsx vary only terminal at base WACC. For full WACC sensitivity, modify inputs and rerun.",
        "3. No 3-statement integration. Operating lease liabilities (IFRS 16) embedded in EBITDA.",
        "4. Default projection assumptions are generic. Review per industry / company guidance.",
        "5. WACC inputs use defaults if not customized in UI. Country risk premium and beta should be company-specific.",
        "",
        "## DISCLAIMER",
        "",
        "NOT INVESTMENT ADVICE. Educational case study and analyst work product. Verify all figures against company official annual report. Past performance does not predict future results.",
        "",
        "Built using Anthropic financial-services skill prompts (Apache 2.0). Repository: https://github.com/anthropics/financial-services.",
        "",
        f"Generated: {as_of}",
    ])

    return "\n".join(lines)


def _recommend(upside: float, tv_pct: float, current: float, implied: float) -> str:
    if upside > 30:
        rec = "**Significant upside.** Bull case implied; verify thesis durability."
    elif 10 <= upside <= 30:
        rec = "**Moderate upside.** Quality / valuation tradeoff balanced. Consider entry on drawdown."
    elif -10 <= upside < 10:
        rec = "**Fair value.** Market roughly aligned with intrinsic. No clear margin of safety."
    elif -30 < upside < -10:
        rec = "**Overvalued.** Market pays premium not supported by base case cash flows."
    else:
        rec = "**Significantly overvalued by DCF.** Bear case territory. Either thesis weak or sentiment is the driver."

    if tv_pct > 75:
        rec += " ALSO: terminal value dominates (>75% of EV) so result hinges heavily on terminal assumptions."

    return rec


if __name__ == "__main__":
    import argparse
    import json
    import compute_dcf

    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True)
    args = parser.parse_args()
    inputs = json.loads(open(args.inputs, encoding="utf-8").read())
    scens = compute_dcf.run_all(inputs)
    memo = generate_memo(inputs, scens)
    print(memo[:2000])
