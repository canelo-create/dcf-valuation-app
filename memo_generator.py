"""Genera memo de análisis DCF en español desde inputs + scenarios."""

from typing import Optional


SCENARIO_LABELS = {"bear": "Pesimista", "base": "Base", "bull": "Optimista"}


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

    recommendation = _recommend(upside_base, tv_pct)

    lines = [
        f"# Valoración DCF: {company} ({ticker})",
        "",
        f"**Fecha: {as_of}** | Metodología: Proyección explícita 10 años de FCF Unlevered, valor terminal mezclado (crecimiento perpetuo + múltiplo de salida). Cifras en {ccy}.",
        "",
        "## Resumen Ejecutivo",
        "",
        "| Métrica | Valor |",
        "|---|---:|",
        f"| Precio actual | {ccy} {current:.2f} |",
        f"| Precio implícito Base | {ccy} {base_price:.2f} |",
        f"| **Potencial vs mercado** | **{upside_base:+.1f}%** |",
        f"| Caso Pesimista | {ccy} {bear_price:.2f} ({upside_bear:+.1f}%) |",
        f"| Caso Optimista | {ccy} {bull_price:.2f} ({upside_bull:+.1f}%) |",
        f"| WACC | {wacc_d['wacc_pct']:.2f}% |",
        f"| Terminal % del EV | {tv_pct:.1f}% ({'dentro' if 50 <= tv_pct <= 70 else 'FUERA'} banda 50-70%) |",
        "",
        f"**Recomendación:** {recommendation}",
        "",
        "## Metodología",
        "",
        "### Financieros históricos",
        "",
        "| Métrica | " + " | ".join(sorted(inputs["historical"].keys())) + " |",
        "|---|" + "---:|" * len(inputs["historical"]),
    ]
    fy_keys = sorted(inputs["historical"].keys())
    label_map = [("Ingresos", "revenue"), ("EBITDA", "ebitda"), ("EBIT", "ebit"), ("D&A", "da"), ("CapEx", "capex"), ("FCF", "fcf")]
    for label, key in label_map:
        row = f"| {label} | " + " | ".join(f"{inputs['historical'][fy].get(key, 0):,}" for fy in fy_keys) + " |"
        lines.append(row)
    lines.append("")

    lines.extend([
        "### Construcción del WACC (CAPM)",
        "",
        "| Componente | Valor | Fuente |",
        "|---|---:|---|",
        f"| Tasa libre de riesgo | {wacc_d['risk_free_rate_pct']:.2f}% | {wacc_d['risk_free_source']} |",
        f"| Prima de riesgo del mercado | {wacc_d['equity_risk_premium_pct']:.2f}% | {wacc_d['erp_source']} |",
        f"| Beta (5 años) | {wacc_d['beta']:.2f} | yfinance |",
        f"| **Coste del Equity** | **{wacc_d['cost_of_equity_pct']:.2f}%** | Rf + Beta * ERP |",
        f"| Tipo impositivo | {wacc_d['tax_rate_pct']:.1f}% | |",
        f"| **WACC** | **{wacc_d['wacc_pct']:.2f}%** | Aplicado a todos los escenarios |",
        "",
        f"Posición financiera: {ccy} {md['net_cash_eur_m']:,}M {'(caja neta)' if md['net_cash_eur_m'] > 0 else '(deuda neta)'}.",
        "",
        "### Proyección (Caso Base, 10 años explícitos)",
        "",
        "| Año | " + " | ".join(f"Y{y}" for y in range(1, 11)) + " |",
        "|---|" + "---:|" * 10,
    ])

    proj = base["projection"]
    base_rev = inputs["historical"][fy_keys[-1]]["revenue"]
    growth_row = "| Crecimiento % |"
    prev = base_rev
    for r in proj["revenue"]:
        g = (r / prev - 1) * 100 if prev else 0
        growth_row += f" {g:+.1f}% |"
        prev = r
    lines.append(growth_row)
    lines.append("| Ingresos | " + " | ".join(f"{r:,.0f}" for r in proj["revenue"]) + " |")
    lines.append("| EBITDA | " + " | ".join(f"{e:,.0f}" for e in proj["ebitda"]) + " |")
    lines.append("| FCF | " + " | ".join(f"{f:,.0f}" for f in proj["fcf"]) + " |")
    lines.append("| VP(FCF) | " + " | ".join(f"{p:,.0f}" for p in proj["pv_fcf"]) + " |")
    lines.append("")

    lines.extend([
        "### Valor Terminal",
        "",
        "| Método | TV Bruto | VP del TV |",
        "|---|---:|---:|",
        f"| Crecimiento perpetuo ({base['tg']:.1f}%) | {base['dcf']['tv_perpetuity']:,.0f} | {base['dcf']['pv_tv_perpetuity']:,.0f} |",
        f"| Múltiplo salida ({base['em']:.1f}x EBITDA Y10) | {base['dcf']['tv_exit_multiple']:,.0f} | {base['dcf']['pv_tv_exit']:,.0f} |",
        f"| **VP mezclado** | | **{base['dcf']['pv_tv_blended']:,.0f}** |",
        "",
        "### Resumen de Valoración",
        "",
        "| Componente | Valor |",
        "|---|---:|",
        f"| Suma VP de FCF explícitos (Y1-Y10) | {ccy} {base['dcf']['sum_pv_fcf']:,.0f}M |",
        f"| VP del Valor Terminal | {ccy} {base['dcf']['pv_tv_blended']:,.0f}M |",
        f"| **Valor Empresa (EV)** | **{ccy} {base['dcf']['enterprise_value']:,.0f}M** |",
        f"| (+) Caja neta | {ccy} {md['net_cash_eur_m']:,}M |",
        f"| **Valor Equity** | **{ccy} {base['dcf']['equity_value']:,.0f}M** |",
        f"| (/) Acciones en circulación (M) | {md['shares_outstanding_m']:,} |",
        f"| **Precio implícito por acción** | **{ccy} {base_price:.2f}** |",
        "",
        "## Escenarios",
        "",
        "| Escenario | Crec. Terminal | Múltiplo salida | Precio implícito | Potencial |",
        "|---|---:|---:|---:|---:|",
        f"| Pesimista | {bear['tg']:.1f}% | {bear['em']:.1f}x | {ccy} {bear_price:.2f} | {upside_bear:+.1f}% |",
        f"| **Base** | **{base['tg']:.1f}%** | **{base['em']:.1f}x** | **{ccy} {base_price:.2f}** | **{upside_base:+.1f}%** |",
        f"| Optimista | {bull['tg']:.1f}% | {bull['em']:.1f}x | {ccy} {bull_price:.2f} | {upside_bull:+.1f}% |",
        "",
    ])

    if peers_data:
        lines.extend([
            "## Cross-check con comparables",
            "",
            "Múltiplos peer (TTM):",
            "",
            "| Empresa | EV/Ventas | EV/EBITDA | P/E (TTM) |",
            "|---|---:|---:|---:|",
        ])
        for p in peers_data:
            lines.append(
                f"| {p['Company']} | {p.get('EV_Sales', 0):.2f}x | {p.get('EV_EBITDA', 0):.2f}x | {p.get('PE_Trailing', 0):.2f}x |"
            )
        lines.append("")

    try:
        import insights as _insights_mod
        _ins = _insights_mod.generate_insights(inputs, scenarios, peers_data)
    except Exception:
        _ins = []
    if _ins:
        lines.extend(["## Insights del análisis", "", _insights_mod.insights_summary_line(_ins), ""])
        cats = {}
        for it in _ins:
            cats.setdefault(it["categoria"], []).append(it)
        sent_tag = {"positivo": "[+]", "neutro": "[~]", "alerta": "[!]"}
        for cat, group in cats.items():
            lines.append(f"### {cat}")
            lines.append("")
            for it in group:
                lines.append(f"- {sent_tag.get(it['sentimiento'], '[-]')} **{it['titulo']}** — {it['detalle']}")
            lines.append("")

    meta = scenarios.get("_meta", {})
    if meta:
        lines.extend([
            "## Reverse-DCF y calidad del negocio",
            "",
            "| Indicador | Valor | Lectura |",
            "|---|---:|---|",
        ])
        g_impl = meta.get("implied_growth_pct")
        if g_impl is not None:
            lectura_g = "exigente" if g_impl > 6 else ("pesimista" if g_impl < 0 else "creíble")
            lines.append(f"| Crecimiento perpetuo implícito en el precio | {g_impl:.1f}% | {lectura_g} |")
        roic = meta.get("roic_pct")
        if roic is not None:
            lines.append(f"| ROIC aproximado | {roic:.1f}% | vs WACC {meta.get('wacc_pct', 0):.1f}% -> {meta.get('roic_vs_wacc', 'n/d')} |")
        lines.append("")
        lines.append("Método reverse-DCF (IE Corporate Finance): g = WACC - FCF_next / TV. ROIC > WACC implica creación de valor.")
        lines.append("")

    lines.extend([
        "## Sanity checks",
        "",
        f"- Terminal % del EV: {tv_pct:.1f}% ({'PASS' if 50 <= tv_pct <= 70 else 'FLAG - fuera del rango típico 50-70%'})",
        f"- Spread Pesimista/Optimista: {abs(upside_bull - upside_bear):.0f}pp ({'razonable' if 50 <= abs(upside_bull - upside_bear) <= 150 else 'verificar supuestos'})",
        f"- WACC: {wacc_d['wacc_pct']:.2f}% ({'razonable' if 6 <= wacc_d['wacc_pct'] <= 15 else 'verificar'})",
        "",
        "## Limitaciones",
        "",
        "1. Datos vía API yfinance. Verificar contra reporte anual oficial para deliverable de producción.",
        "2. Tablas de sensibilidad en xlsx varían solo el terminal al WACC base. Para sensibilidad completa de WACC, modificar inputs y recalcular.",
        "3. Sin integración 3-statement. Operating lease liabilities (IFRS 16) embebidos en EBITDA.",
        "4. Supuestos de proyección por defecto genéricos. Revisar según industria / guidance de la empresa.",
        "5. Inputs WACC usan defaults si no se personalizan en UI. Country risk premium y beta deben ser company-specific.",
        "",
        "## AVISO LEGAL",
        "",
        "NO ES ASESORAMIENTO FINANCIERO. Case study educativo y producto analista. Verificar contra reporte anual oficial. Rendimientos pasados no predicen futuros.",
        "",
        "Construido con skills open-source de Anthropic financial-services (Apache 2.0). Repositorio: https://github.com/anthropics/financial-services.",
        "Convenciones metodológicas alineadas con IE Business School Corporate Finance: TV = FCF_next/(WACC-g) con g < WACC estricto, beta sin término (1-t), WACC a valores de mercado, EV->Equity = EV - deuda + caja, reverse-DCF para crecimiento implícito, ROIC vs WACC para creación de valor.",
        "",
        f"Generado: {as_of}",
    ])

    return "\n".join(lines)


def _recommend(upside: float, tv_pct: float) -> str:
    if upside > 30:
        rec = "**Potencial significativo.** Escenario optimista implícito; verificar durabilidad de la tesis."
    elif 10 <= upside <= 30:
        rec = "**Potencial moderado.** Balance calidad/valoración equilibrado. Considerar entrada en corrección."
    elif -10 <= upside < 10:
        rec = "**Valor justo.** Mercado alineado con valor intrínseco. Sin margen de seguridad claro."
    elif -30 < upside < -10:
        rec = "**Sobrevalorado.** Mercado paga premium no respaldado por flujos del caso base."
    else:
        rec = "**Muy sobrevalorado por DCF.** Territorio caso pesimista. Tesis débil o sentiment es el driver."

    if tv_pct > 75:
        rec += " IMPORTANTE: El valor terminal domina (>75% del EV), el resultado depende fuertemente de los supuestos terminales."

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
