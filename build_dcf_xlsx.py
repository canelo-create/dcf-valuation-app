"""Generate DCF xlsx for any company from inputs.json.

Usage:
    python build_dcf_xlsx.py --inputs cases/inditex/inputs.json --output cases/inditex/dcf.xlsx
"""

import argparse
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

import compute_dcf

NAVY = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
LIGHTBLUE = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
LIGHTGREY = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
CENTER_BLUE = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")

FONT_DATA = Font(name="Times New Roman", size=11, color="000000")
FONT_INPUT = Font(name="Times New Roman", size=11, color="0070C0")
FONT_HDR_WHITE = Font(name="Times New Roman", size=12, color="FFFFFF", bold=True)
FONT_HDR_BLACK = Font(name="Times New Roman", size=11, color="000000", bold=True)
FONT_TITLE = Font(name="Times New Roman", size=14, bold=True)
FONT_CENTER_BOLD = Font(name="Times New Roman", size=11, color="000000", bold=True)

CENTER = Alignment(horizontal="center", vertical="center")
LEFT = Alignment(horizontal="left", vertical="center")


def section_header(ws, row, text, ncols):
    ws.cell(row=row, column=1, value=text)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = NAVY
        cell.font = FONT_HDR_WHITE
        cell.alignment = CENTER


def label_cell(ws, row, col, text, bold=False, fill=None):
    cell = ws.cell(row=row, column=col, value=text)
    cell.font = FONT_HDR_BLACK if bold else FONT_DATA
    cell.alignment = LEFT
    if fill:
        cell.fill = fill
    return cell


def input_cell(ws, row, col, value, fmt=None, note=None):
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = FONT_INPUT
    cell.alignment = CENTER
    if fmt:
        cell.number_format = fmt
    if note:
        cell.comment = Comment(note, "Build script")
    return cell


def formula_cell(ws, row, col, formula, fmt=None, bold=False):
    cell = ws.cell(row=row, column=col, value=formula)
    cell.font = FONT_CENTER_BOLD if bold else FONT_DATA
    cell.alignment = CENTER
    if fmt:
        cell.number_format = fmt
    return cell


def build(inputs_path, output_path):
    inputs = json.loads(Path(inputs_path).read_text(encoding="utf-8"))
    wb = build_workbook(inputs)
    wb.save(output_path)
    print(f"Wrote {output_path}")


def build_workbook(inputs):
    company = inputs["company"]
    ticker = inputs["ticker"]
    ccy = inputs["currency"]
    as_of = inputs["as_of_date"]
    fy_end = inputs["fiscal_year_end"]

    wb = Workbook()
    ws = wb.active
    ws.title = f"{company} DCF"

    md = inputs["market_data"]
    wacc_d = inputs["wacc"]
    base = inputs["projection_assumptions_base"]
    hist = inputs["historical"]
    fy_keys = sorted(hist.keys())

    src_note = f"Source: see data_sources in inputs.json, accessed {as_of}"

    # Row 1-3: Title
    ws.cell(row=1, column=1, value=f"{company.upper()} ({ticker}) - DISCOUNTED CASH FLOW VALUATION")
    ws.cell(row=1, column=1).font = FONT_TITLE
    ws.cell(row=2, column=1, value=f"As of {as_of} | All figures in {ccy} Millions except per-share | Fiscal year ends {fy_end}")
    ws.cell(row=3, column=1, value=f"Base case: 10-year projection, WACC {wacc_d['wacc_pct']:.2f}%, Terminal g {base['terminal_growth_pct']:.1f}%, Exit multiple {base['exit_multiple_ev_ebitda']:.1f}x EV/EBITDA")

    # === SECTION 1: MARKET DATA ===
    section_header(ws, 5, "MARKET DATA & KEY INPUTS", 12)
    inputs_data = [
        (f"Current share price ({ccy})", md["current_price_eur"], "0.00"),
        ("Shares outstanding (M)", md["shares_outstanding_m"], "#,##0"),
        (f"Market capitalization ({ccy} M)", md["market_cap_eur_m"], "#,##0"),
        (f"Cash and ST investments ({ccy} M)", md["cash_and_st_investments_eur_m"], "#,##0"),
        (f"Total financial debt ({ccy} M)", md["total_financial_debt_eur_m"], "#,##0"),
        (f"Net cash ({ccy} M)", md["net_cash_eur_m"], "#,##0"),
        (f"Enterprise value ({ccy} M)", md["enterprise_value_eur_m"], "#,##0"),
        ("Beta (5Y)", md["beta_5y"], "0.00"),
    ]
    for i, (label, val, fmt) in enumerate(inputs_data):
        r = 6 + i
        label_cell(ws, r, 1, label)
        input_cell(ws, r, 3, val, fmt=fmt, note=src_note)
    PRICE_ROW = 6
    SHARES_ROW = 7
    NETCASH_ROW = 11

    # === SECTION 2: WACC BUILD ===
    section_header(ws, 16, "WACC BUILD (CAPM)", 12)
    wacc_data = [
        ("Risk-free rate", wacc_d["risk_free_rate_pct"] / 100, "0.00%", wacc_d["risk_free_source"]),
        ("Equity risk premium", wacc_d["equity_risk_premium_pct"] / 100, "0.00%", wacc_d["erp_source"]),
        ("Beta (5Y)", wacc_d["beta"], "0.00", "5Y monthly regression"),
    ]
    for i, (label, val, fmt, note) in enumerate(wacc_data):
        r = 17 + i
        label_cell(ws, r, 1, label)
        input_cell(ws, r, 3, val, fmt=fmt, note=note)
    RF_ROW = 17
    ERP_ROW = 18
    BETA_ROW = 19

    label_cell(ws, 20, 1, "Cost of equity = Rf + Beta * ERP", bold=True)
    formula_cell(ws, 20, 3, f"=C{RF_ROW}+C{BETA_ROW}*C{ERP_ROW}", fmt="0.00%", bold=True)

    label_cell(ws, 21, 1, "Pretax cost of debt")
    input_cell(ws, 21, 3, wacc_d["pretax_cost_of_debt_pct"] / 100, fmt="0.00%")

    label_cell(ws, 22, 1, "Tax rate")
    input_cell(ws, 22, 3, wacc_d["tax_rate_pct"] / 100, fmt="0.00%")
    TAX_ROW = 22

    label_cell(ws, 23, 1, "After-tax cost of debt", bold=True)
    formula_cell(ws, 23, 3, f"=C21*(1-C{TAX_ROW})", fmt="0.00%", bold=True)

    label_cell(ws, 24, 1, f"WACC ({wacc_d.get('note', 'see input')[:60]})", bold=True, fill=LIGHTBLUE)
    formula_cell(ws, 24, 3, f"=C20", fmt="0.00%", bold=True).fill = LIGHTBLUE
    WACC_ROW = 24

    # === SECTION 3: HISTORICAL ===
    section_header(ws, 27, f"HISTORICAL FINANCIALS ({len(fy_keys)}Y)", 12)
    hist_headers = ["Metric"] + fy_keys + [f"{len(fy_keys)}Y CAGR"]
    for c, label in enumerate(hist_headers):
        cell = ws.cell(row=28, column=c + 1, value=label)
        cell.fill = LIGHTBLUE
        cell.font = FONT_HDR_BLACK
        cell.alignment = CENTER
    hist_rows = [
        ("Revenue", "revenue", "#,##0"),
        ("EBITDA", "ebitda", "#,##0"),
        ("EBIT", "ebit", "#,##0"),
        ("D&A", "da", "#,##0"),
        ("CapEx", "capex", "#,##0"),
        ("FCF", "fcf", "#,##0"),
        ("Net Income", "net_income", "#,##0"),
    ]
    base_rev_col = get_column_letter(1 + len(fy_keys))  # Last historical column = FY2025
    base_rev_row = 29  # Revenue row
    for i, (label, key, fmt) in enumerate(hist_rows):
        r = 29 + i
        label_cell(ws, r, 1, label, bold=True)
        for j, fy in enumerate(fy_keys):
            val = hist[fy].get(key, 0)
            input_cell(ws, r, 2 + j, val, fmt=fmt, note=f"{fy}: {src_note}")
        # CAGR computation
        first_col = get_column_letter(2)
        last_col = get_column_letter(1 + len(fy_keys))
        n = len(fy_keys) - 1
        formula_cell(ws, r, 2 + len(fy_keys), f"=({last_col}{r}/{first_col}{r})^(1/{n})-1", fmt="0.0%")
    margin_rows = [
        ("EBITDA margin", "ebitda", "revenue"),
        ("FCF margin", "fcf", "revenue"),
    ]
    for i, (label, num_key, den_key) in enumerate(margin_rows):
        r = 36 + i
        label_cell(ws, r, 1, label, bold=True, fill=LIGHTGREY)
        for j, fy in enumerate(fy_keys):
            num_idx = next(idx for idx, t in enumerate(hist_rows) if t[1] == num_key)
            den_idx = next(idx for idx, t in enumerate(hist_rows) if t[1] == den_key)
            num_row = 29 + num_idx
            den_row = 29 + den_idx
            col = get_column_letter(2 + j)
            formula_cell(ws, r, 2 + j, f"={col}{num_row}/{col}{den_row}", fmt="0.0%")
            ws.cell(row=r, column=2 + j).fill = LIGHTGREY

    # === SECTION 4: PROJECTION ===
    section_header(ws, 40, "PROJECTION - BASE CASE (10Y EXPLICIT)", 12)
    years = list(range(1, 11))
    proj_headers = ["Metric"] + [f"Y{y}" for y in years] + ["Sum"]
    for c, label in enumerate(proj_headers):
        cell = ws.cell(row=41, column=c + 1, value=label)
        cell.fill = LIGHTBLUE
        cell.font = FONT_HDR_BLACK
        cell.alignment = CENTER

    GROWTH_ROW = 42
    REV_ROW = 43
    EBMARG_ROW = 44
    EBITDA_ROW = 45
    DA_PCT_ROW = 46
    DA_ROW = 47
    EBIT_ROW = 48
    NOPAT_ROW = 49
    CAPEX_PCT_ROW = 50
    CAPEX_ROW = 51
    NWC_ROW = 52
    FCF_ROW = 53
    DISC_PERIOD_ROW = 54
    PV_FACTOR_ROW = 55
    PV_FCF_ROW = 56

    label_cell(ws, GROWTH_ROW, 1, "Revenue growth %")
    for i in range(10):
        input_cell(ws, GROWTH_ROW, 2 + i, base["revenue_growth_yoy_pct"][i] / 100, fmt="0.0%")

    label_cell(ws, REV_ROW, 1, f"Revenue ({ccy} M)", bold=True)
    base_rev_cell_addr = f"{base_rev_col}{base_rev_row}"
    for i in range(10):
        if i == 0:
            formula = f"={base_rev_cell_addr}*(1+B{GROWTH_ROW})"
        else:
            prev = get_column_letter(2 + i - 1)
            cur = get_column_letter(2 + i)
            formula = f"={prev}{REV_ROW}*(1+{cur}{GROWTH_ROW})"
        formula_cell(ws, REV_ROW, 2 + i, formula, fmt="#,##0", bold=True)

    label_cell(ws, EBMARG_ROW, 1, "EBITDA margin %")
    for i in range(10):
        input_cell(ws, EBMARG_ROW, 2 + i, base["ebitda_margin_pct"][i] / 100, fmt="0.0%")

    label_cell(ws, EBITDA_ROW, 1, "EBITDA", bold=True)
    for i in range(10):
        col = get_column_letter(2 + i)
        formula_cell(ws, EBITDA_ROW, 2 + i, f"={col}{REV_ROW}*{col}{EBMARG_ROW}", fmt="#,##0", bold=True)

    label_cell(ws, DA_PCT_ROW, 1, "D&A % of revenue")
    for i in range(10):
        input_cell(ws, DA_PCT_ROW, 2 + i, base["da_pct_of_revenue"][i] / 100, fmt="0.0%")

    label_cell(ws, DA_ROW, 1, "D&A")
    for i in range(10):
        col = get_column_letter(2 + i)
        formula_cell(ws, DA_ROW, 2 + i, f"={col}{REV_ROW}*{col}{DA_PCT_ROW}", fmt="#,##0")

    label_cell(ws, EBIT_ROW, 1, "EBIT (= EBITDA - D&A)")
    for i in range(10):
        col = get_column_letter(2 + i)
        formula_cell(ws, EBIT_ROW, 2 + i, f"={col}{EBITDA_ROW}-{col}{DA_ROW}", fmt="#,##0")

    label_cell(ws, NOPAT_ROW, 1, "NOPAT (= EBIT * (1-tax))")
    for i in range(10):
        col = get_column_letter(2 + i)
        formula_cell(ws, NOPAT_ROW, 2 + i, f"={col}{EBIT_ROW}*(1-$C${TAX_ROW})", fmt="#,##0")

    label_cell(ws, CAPEX_PCT_ROW, 1, "CapEx % of revenue")
    for i in range(10):
        input_cell(ws, CAPEX_PCT_ROW, 2 + i, base["capex_pct_of_revenue"][i] / 100, fmt="0.0%")

    label_cell(ws, CAPEX_ROW, 1, "CapEx")
    for i in range(10):
        col = get_column_letter(2 + i)
        formula_cell(ws, CAPEX_ROW, 2 + i, f"={col}{REV_ROW}*{col}{CAPEX_PCT_ROW}", fmt="#,##0")

    nwc_pct = base["nwc_change_pct_of_revenue_change"] / 100
    label_cell(ws, NWC_ROW, 1, f"Change in NWC ({nwc_pct*100:.1f}% of Δrev)")
    for i in range(10):
        col = get_column_letter(2 + i)
        if i == 0:
            prev_cell = base_rev_cell_addr
        else:
            prev_cell = f"{get_column_letter(2 + i - 1)}{REV_ROW}"
        formula_cell(ws, NWC_ROW, 2 + i, f"=({col}{REV_ROW}-{prev_cell})*{nwc_pct}", fmt="#,##0")

    label_cell(ws, FCF_ROW, 1, "Unlevered FCF (= NOPAT + D&A - CapEx - ΔNWC)", bold=True, fill=LIGHTBLUE)
    for i in range(10):
        col = get_column_letter(2 + i)
        formula_cell(ws, FCF_ROW, 2 + i, f"={col}{NOPAT_ROW}+{col}{DA_ROW}-{col}{CAPEX_ROW}-{col}{NWC_ROW}", fmt="#,##0", bold=True).fill = LIGHTBLUE

    label_cell(ws, DISC_PERIOD_ROW, 1, "Discount period (mid-year)")
    for i in range(10):
        formula_cell(ws, DISC_PERIOD_ROW, 2 + i, i + 0.5, fmt="0.0")

    label_cell(ws, PV_FACTOR_ROW, 1, "Discount factor")
    for i in range(10):
        col = get_column_letter(2 + i)
        formula_cell(ws, PV_FACTOR_ROW, 2 + i, f"=1/((1+$C${WACC_ROW})^{col}{DISC_PERIOD_ROW})", fmt="0.0000")

    label_cell(ws, PV_FCF_ROW, 1, "PV of FCF", bold=True, fill=LIGHTBLUE)
    for i in range(10):
        col = get_column_letter(2 + i)
        formula_cell(ws, PV_FCF_ROW, 2 + i, f"={col}{FCF_ROW}*{col}{PV_FACTOR_ROW}", fmt="#,##0", bold=True).fill = LIGHTBLUE
    formula_cell(ws, PV_FCF_ROW, 12, f"=SUM(B{PV_FCF_ROW}:K{PV_FCF_ROW})", fmt="#,##0", bold=True).fill = LIGHTBLUE

    # === SECTION 5: TV + EQUITY BRIDGE ===
    section_header(ws, 58, "TERMINAL VALUE & EQUITY BRIDGE", 12)

    label_cell(ws, 59, 1, "Final year FCF (Y10)")
    formula_cell(ws, 59, 3, f"=K{FCF_ROW}", fmt="#,##0")

    label_cell(ws, 60, 1, "Final year EBITDA (Y10)")
    formula_cell(ws, 60, 3, f"=K{EBITDA_ROW}", fmt="#,##0")

    label_cell(ws, 61, 1, "Terminal growth rate")
    input_cell(ws, 61, 3, base["terminal_growth_pct"] / 100, fmt="0.0%")
    TG_ROW = 61

    label_cell(ws, 62, 1, "Exit multiple (EV/EBITDA)")
    input_cell(ws, 62, 3, base["exit_multiple_ev_ebitda"], fmt='0.0"x"')
    EM_ROW = 62

    label_cell(ws, 63, 1, "Terminal Value (perpetuity, gross)")
    formula_cell(ws, 63, 3, f"=C59*(1+C{TG_ROW})/($C${WACC_ROW}-C{TG_ROW})", fmt="#,##0")

    label_cell(ws, 64, 1, "Terminal Value (exit multiple, gross)")
    formula_cell(ws, 64, 3, f"=C60*C{EM_ROW}", fmt="#,##0")

    label_cell(ws, 65, 1, "PV of Terminal (blended avg)", bold=True)
    formula_cell(ws, 65, 3, f"=AVERAGE(C63,C64)/((1+$C${WACC_ROW})^K{DISC_PERIOD_ROW})", fmt="#,##0", bold=True)

    label_cell(ws, 67, 1, "Sum PV FCFs (Y1-Y10)", bold=True)
    formula_cell(ws, 67, 3, f"=L{PV_FCF_ROW}", fmt="#,##0", bold=True)

    label_cell(ws, 68, 1, "Enterprise Value", bold=True, fill=LIGHTBLUE)
    formula_cell(ws, 68, 3, f"=C67+C65", fmt="#,##0", bold=True).fill = LIGHTBLUE

    label_cell(ws, 69, 1, "Net cash (add back)")
    formula_cell(ws, 69, 3, f"=C{NETCASH_ROW}", fmt="#,##0")

    label_cell(ws, 70, 1, "Equity Value", bold=True, fill=LIGHTBLUE)
    formula_cell(ws, 70, 3, f"=C68+C69", fmt="#,##0", bold=True).fill = LIGHTBLUE

    label_cell(ws, 71, 1, "Shares outstanding (M)")
    formula_cell(ws, 71, 3, f"=C{SHARES_ROW}", fmt="#,##0")

    label_cell(ws, 72, 1, f"IMPLIED SHARE PRICE ({ccy})", bold=True, fill=CENTER_BLUE)
    formula_cell(ws, 72, 3, f"=C70/C71", fmt="0.00", bold=True).fill = CENTER_BLUE

    label_cell(ws, 73, 1, f"Current market price ({ccy})")
    formula_cell(ws, 73, 3, f"=C{PRICE_ROW}", fmt="0.00")

    label_cell(ws, 74, 1, "Upside / (Downside) vs market", bold=True, fill=CENTER_BLUE)
    formula_cell(ws, 74, 3, f"=C72/C73-1", fmt="0.0%", bold=True).fill = CENTER_BLUE

    label_cell(ws, 75, 1, "Terminal % of EV (sanity 50-70%)")
    formula_cell(ws, 75, 3, f"=C65/C68", fmt="0.0%")

    label_cell(ws, 76, 1, "Implied EV/EBITDA (current EBITDA)")
    formula_cell(ws, 76, 3, f"=C68/{base_rev_col}30", fmt='0.00"x"')  # row 30 = EBITDA

    # === SENSITIVITY ===
    section_header(ws, 79, "SENSITIVITY: IMPLIED SHARE PRICE - WACC vs TERMINAL GROWTH", 12)
    wacc_range = inputs["sensitivity_ranges"]["wacc_pct"]
    tg_range = inputs["sensitivity_ranges"]["terminal_growth_pct"]
    ws.cell(row=80, column=1, value="Terminal g \\ WACC").font = FONT_HDR_BLACK
    ws.cell(row=80, column=1).fill = LIGHTBLUE
    for c, w in enumerate(wacc_range):
        cell = ws.cell(row=80, column=2 + c, value=w / 100)
        cell.fill = LIGHTBLUE
        cell.font = FONT_HDR_BLACK
        cell.number_format = "0.00%"
        cell.alignment = CENTER
    base_wacc = wacc_d["wacc_pct"]
    base_tg = base["terminal_growth_pct"]
    for ri, tg in enumerate(tg_range):
        cell = ws.cell(row=81 + ri, column=1, value=tg / 100)
        cell.font = FONT_HDR_BLACK
        cell.fill = LIGHTBLUE
        cell.number_format = "0.00%"
        cell.alignment = CENTER
        for ci, w in enumerate(wacc_range):
            wf = w / 100
            tgf = tg / 100
            formula = (
                f"=((K{FCF_ROW}*(1+{tgf}))/({wf}-{tgf})/((1+{wf})^9.5) + C67 + C{NETCASH_ROW})/C{SHARES_ROW}"
            )
            cell2 = ws.cell(row=81 + ri, column=2 + ci, value=formula)
            cell2.number_format = "0.00"
            cell2.font = FONT_DATA
            cell2.alignment = CENTER
            if abs(w - base_wacc) < 0.5 and abs(tg - base_tg) < 0.3:
                cell2.fill = CENTER_BLUE
                cell2.font = FONT_CENTER_BOLD

    # === SCENARIOS ===
    section_header(ws, 90, "SCENARIO SUMMARY - Bear / Base / Bull", 12)
    headers = ["Scenario", "Revenue Y10", "EBITDA Margin Y10", "Terminal g", "Exit mult", f"Implied Share ({ccy})", "Upside vs market"]
    for c, h in enumerate(headers):
        cell = ws.cell(row=91, column=c + 1, value=h)
        cell.fill = LIGHTBLUE
        cell.font = FONT_HDR_BLACK
        cell.alignment = CENTER

    scens = compute_dcf.run_all(inputs)
    current = md["current_price_eur"]
    for i, case in enumerate(["bear", "base", "bull"]):
        s = scens[case]
        p = s["projection"]
        d = s["dcf"]
        tg = s["tg"]
        em = s["em"]
        row = 92 + i
        label_cell(ws, row, 1, case.upper(), bold=True)
        input_cell(ws, row, 2, p["revenue"][-1], fmt="#,##0")
        input_cell(ws, row, 3, p["ebitda"][-1] / p["revenue"][-1], fmt="0.0%")
        input_cell(ws, row, 4, tg / 100, fmt="0.0%")
        input_cell(ws, row, 5, em, fmt='0.0"x"')
        input_cell(ws, row, 6, d["implied_share_price"], fmt="0.00")
        input_cell(ws, row, 7, d["implied_share_price"] / current - 1, fmt="0.0%")
        if case == "base":
            for c in range(1, 8):
                ws.cell(row=row, column=c).fill = CENTER_BLUE

    # === NOTES ===
    section_header(ws, 99, "NOTES & METHODOLOGY", 12)
    notes = [
        f"Company: {company} ({ticker}). Currency: {ccy}. Fiscal year ends {fy_end}. As of {as_of}.",
        f"Methodology: 10-year explicit Unlevered FCF projection, discounted at WACC {wacc_d['wacc_pct']:.2f}%. Terminal value blended (perpetuity growth + exit multiple).",
        f"WACC: Cost of equity via CAPM (Rf {wacc_d['risk_free_rate_pct']}% + Beta {wacc_d['beta']} * ERP {wacc_d['equity_risk_premium_pct']}%) = {wacc_d['cost_of_equity_pct']:.2f}%.",
        f"Net cash position: {ccy} {md['net_cash_eur_m']:,}M. Equity weight {wacc_d['equity_weight_pct']}%, debt weight {wacc_d['debt_weight_pct']}%.",
        "Inputs source: see data_sources block in inputs.json. Built using Anthropic financial-services skill `dcf-model` (Apache 2.0).",
        "Limitations: Sensitivity table varies only terminal, holds sum PV FCFs at base WACC. For full sensitivity, modify inputs.json and rerun.",
        "DISCLAIMER: Nothing herein is investment advice. Analyst work product for review by qualified professional. Verify against primary annual report.",
    ]
    for i, n in enumerate(notes):
        ws.cell(row=100 + i, column=1, value=n).font = FONT_DATA
        ws.merge_cells(start_row=100 + i, start_column=1, end_row=100 + i, end_column=12)

    ws.column_dimensions["A"].width = 45
    for c in range(2, 13):
        ws.column_dimensions[get_column_letter(c)].width = 14

    return wb


def main():
    parser = argparse.ArgumentParser(description="Build DCF xlsx from inputs JSON")
    parser.add_argument("--inputs", required=True, help="Path to inputs.json")
    parser.add_argument("--output", required=True, help="Path to output xlsx")
    args = parser.parse_args()
    build(args.inputs, args.output)


if __name__ == "__main__":
    main()
