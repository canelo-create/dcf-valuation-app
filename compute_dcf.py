"""Compute DCF for any company.

Usage:
    python compute_dcf.py --inputs cases/inditex/inputs.json

Reads all assumptions from inputs.json. Prints valuation summary.
Returns scenarios dict for import by build_dcf_xlsx.py.
"""

import argparse
import json
from pathlib import Path


def load_inputs(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def project_scenario(base_rev, assumptions, tax_rate, wacc, nwc_pct):
    growth = assumptions["revenue_growth_yoy_pct"]
    ebmgn = assumptions["ebitda_margin_pct"]
    da_pct = assumptions.get("da_pct_of_revenue", [8.0] * 10)
    capex_pct = assumptions.get("capex_pct_of_revenue", [6.0] * 10)
    years = list(range(1, 11))
    revs = []
    prev = base_rev
    for g in growth:
        prev = prev * (1 + g / 100)
        revs.append(prev)
    ebitdas = [r * m / 100 for r, m in zip(revs, ebmgn)]
    das = [r * d / 100 for r, d in zip(revs, da_pct)]
    ebits = [e - d for e, d in zip(ebitdas, das)]
    nopats = [e * (1 - tax_rate / 100) for e in ebits]
    capexs = [r * c / 100 for r, c in zip(revs, capex_pct)]
    prev_rev = base_rev
    nwc_changes = []
    for r in revs:
        nwc_changes.append((r - prev_rev) * nwc_pct / 100)
        prev_rev = r
    fcfs = [n + d - cx - nwc for n, d, cx, nwc in zip(nopats, das, capexs, nwc_changes)]
    pv_factors = [1 / ((1 + wacc / 100) ** (y - 0.5)) for y in years]
    pv_fcfs = [f * df for f, df in zip(fcfs, pv_factors)]
    return {
        "years": years,
        "revenue": revs,
        "ebitda": ebitdas,
        "ebit": ebits,
        "nopat": nopats,
        "da": das,
        "capex": capexs,
        "nwc_change": nwc_changes,
        "fcf": fcfs,
        "pv_factor": pv_factors,
        "pv_fcf": pv_fcfs,
    }


def compute_dcf(scenario, wacc, terminal_g, exit_multiple, net_cash, shares):
    sum_pv_fcf = sum(scenario["pv_fcf"])
    final_fcf = scenario["fcf"][-1]
    final_ebitda = scenario["ebitda"][-1]
    n = len(scenario["fcf"])
    discount_period_terminal = n - 0.5

    # IE Corporate Finance rule: stable growth g must be strictly < WACC.
    # Cap g at WACC - 0.5pp to avoid division by zero / negative (infinite) TV.
    wacc_f = wacc / 100
    tg_f = terminal_g / 100
    g_capped = False
    if tg_f >= wacc_f:
        tg_f = wacc_f - 0.005
        g_capped = True

    tv_perpetuity = final_fcf * (1 + tg_f) / (wacc_f - tg_f)
    pv_tv_perpetuity = tv_perpetuity / ((1 + wacc_f) ** discount_period_terminal)

    tv_exit_multiple = final_ebitda * exit_multiple
    pv_tv_exit = tv_exit_multiple / ((1 + wacc_f) ** discount_period_terminal)

    pv_tv_blended = (pv_tv_perpetuity + pv_tv_exit) / 2

    ev = sum_pv_fcf + pv_tv_blended
    equity_value = ev + net_cash
    implied_share_price = equity_value / shares if shares else 0

    return {
        "sum_pv_fcf": sum_pv_fcf,
        "tv_perpetuity": tv_perpetuity,
        "pv_tv_perpetuity": pv_tv_perpetuity,
        "tv_exit_multiple": tv_exit_multiple,
        "pv_tv_exit": pv_tv_exit,
        "pv_tv_blended": pv_tv_blended,
        "enterprise_value": ev,
        "equity_value": equity_value,
        "implied_share_price": implied_share_price,
        "tv_pct_of_ev": pv_tv_blended / ev * 100 if ev else 0,
        "terminal_g_capped": g_capped,
    }


def implied_growth(current_price, shares, net_cash, sum_pv_fcf, final_fcf, wacc, discount_period):
    """Reverse DCF: what perpetual growth g does the current market price imply?

    From IE CF: TV = FCF_next/(WACC-g) -> g = WACC - FCF_next/TV.
    Solve for the TV the market implies given today's price, then back out g.
    """
    if not current_price or not shares:
        return None
    market_equity = current_price * shares
    market_ev = market_equity - net_cash
    implied_pv_tv = market_ev - sum_pv_fcf
    if implied_pv_tv <= 0:
        return None
    wacc_f = wacc / 100
    implied_tv = implied_pv_tv * ((1 + wacc_f) ** discount_period)
    if implied_tv <= 0:
        return None
    g = wacc_f - final_fcf / implied_tv
    return g * 100


def compute_roic(inputs):
    """ROIC = EBIT*(1-t) / (Book Equity + Book Debt - Cash). IE CF uses book values.

    yfinance does not reliably give book equity here; approximate with latest FY
    EBIT, tax rate, and balance proxies. Returns None if data insufficient.
    """
    fy_keys = sorted(inputs.get("historical", {}).keys())
    if not fy_keys:
        return None
    latest = inputs["historical"][fy_keys[-1]]
    ebit = latest.get("ebit", 0)
    if not ebit:
        return None
    tax_rate = inputs["wacc"].get("tax_rate_pct", 22) / 100
    nopat = ebit * (1 - tax_rate)
    md = inputs["market_data"]
    # IE CF: ROIC denominator uses BOOK values (book equity + book debt - cash), NOT market.
    book_equity = md.get("book_equity_eur_m")
    if not book_equity:
        return None  # No book equity available -> do not show a misleading market-based ROIC
    invested = book_equity + md.get("total_financial_debt_eur_m", 0) - md.get("cash_and_st_investments_eur_m", 0)
    if invested <= 0:
        return None
    return nopat / invested * 100


def run_all(inputs):
    fy_keys = sorted(inputs["historical"].keys())
    base_fy = fy_keys[-1]
    base_rev = inputs["historical"][base_fy]["revenue"]
    wacc = inputs["wacc"]["wacc_pct"]
    nwc_pct = inputs["projection_assumptions_base"]["nwc_change_pct_of_revenue_change"]
    tax = inputs["projection_assumptions_base"]["tax_rate_pct"]
    net_cash = inputs["market_data"]["net_cash_eur_m"]
    shares = inputs["market_data"]["shares_outstanding_m"]
    current_price = inputs["market_data"]["current_price_eur"]
    company = inputs["company"]
    ticker = inputs["ticker"]
    ccy = inputs["currency"]

    scenarios = {}
    for case in ["base", "bear", "bull"]:
        assumptions = inputs[f"projection_assumptions_{case}"]
        if case == "base":
            tg = assumptions["terminal_growth_pct"]
            em = assumptions["exit_multiple_ev_ebitda"]
        else:
            tg = assumptions["terminal_growth_pct"]
            em = assumptions["exit_multiple_ev_ebitda"]
        scen = project_scenario(base_rev, assumptions, tax, wacc, nwc_pct)
        dcf = compute_dcf(scen, wacc, tg, em, net_cash, shares)
        scenarios[case] = {"projection": scen, "dcf": dcf, "tg": tg, "em": em}

    # Reverse DCF (IE CF: implied growth) + ROIC value-creation, computed off base case
    base_scen = scenarios["base"]
    n = len(base_scen["projection"]["fcf"])
    g_impl = implied_growth(
        current_price, shares, net_cash,
        base_scen["dcf"]["sum_pv_fcf"], base_scen["projection"]["fcf"][-1],
        wacc, n - 0.5,
    )
    roic = compute_roic(inputs)
    scenarios["_meta"] = {
        "implied_growth_pct": g_impl,
        "roic_pct": roic,
        "wacc_pct": wacc,
        "roic_vs_wacc": (None if roic is None else ("crea valor" if roic > wacc else "destruye valor")),
    }

    print(f"{'='*80}\n{company} ({ticker}) DCF VALUATION SUMMARY\n{'='*80}")
    print(f"Current share price: {ccy} {current_price:.2f}")
    print(f"WACC: {wacc:.2f}% | Net cash: {ccy} {net_cash:,}M | Shares: {shares:,}M")
    print(f"Base year: {base_fy} revenue {ccy} {base_rev:,}M")
    print(f"\n{'Scenario':<10} {'Term g':>8} {'Exit mult':>10} {'EV':>14} {'Equity Val':>14} {'Per share':>11} {'Upside':>10}")
    for case in ["bear", "base", "bull"]:
        dcf = scenarios[case]["dcf"]
        tg = scenarios[case]["tg"]
        em = scenarios[case]["em"]
        up = (dcf["implied_share_price"] / current_price - 1) * 100
        print(f"{case.upper():<10} {tg:>7.1f}% {em:>9.1f}x {dcf['enterprise_value']:>14,.0f} {dcf['equity_value']:>14,.0f} {dcf['implied_share_price']:>10.2f} {up:>+9.1f}%")

    print(f"\nBASE case 10Y projection ({ccy} M):")
    p = scenarios["base"]["projection"]
    print(f"{'Year':<6} {'Revenue':>12} {'Growth':>8} {'EBITDA':>11} {'Margin':>8} {'FCF':>10} {'PV(FCF)':>10}")
    prev = base_rev
    for i, y in enumerate(p["years"]):
        g = (p["revenue"][i] / prev - 1) * 100
        margin = p["ebitda"][i] / p["revenue"][i] * 100
        print(f"Y{y:<5} {p['revenue'][i]:>12,.0f} {g:>+7.1f}% {p['ebitda'][i]:>11,.0f} {margin:>7.1f}% {p['fcf'][i]:>10,.0f} {p['pv_fcf'][i]:>10,.0f}")
        prev = p["revenue"][i]
    dcf_base = scenarios["base"]["dcf"]
    print(f"\nSum PV FCFs (Y1-Y10): {ccy} {dcf_base['sum_pv_fcf']:,.0f}M")
    print(f"Terminal value (perpetuity, gross): {ccy} {dcf_base['tv_perpetuity']:,.0f}M")
    print(f"Terminal value (exit multiple, gross): {ccy} {dcf_base['tv_exit_multiple']:,.0f}M")
    print(f"PV of Terminal (blended): {ccy} {dcf_base['pv_tv_blended']:,.0f}M")
    print(f"Enterprise Value: {ccy} {dcf_base['enterprise_value']:,.0f}M")
    print(f"Equity Value (EV + net cash {net_cash:,}M): {ccy} {dcf_base['equity_value']:,.0f}M")
    print(f"Implied share price: {ccy} {dcf_base['implied_share_price']:.2f}")
    print(f"Terminal % of EV: {dcf_base['tv_pct_of_ev']:.1f}%")

    return scenarios


def main():
    parser = argparse.ArgumentParser(description="Compute DCF from inputs JSON")
    parser.add_argument("--inputs", required=True, help="Path to inputs.json")
    args = parser.parse_args()
    inputs = load_inputs(args.inputs)
    return run_all(inputs)


if __name__ == "__main__":
    main()
