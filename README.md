# Inditex DCF Valuation Case Study

End-to-end equity valuation of Inditex (BME:ITX) using the open-source DCF and comparable company analysis skills from Anthropic's [financial-services](https://github.com/anthropics/financial-services) repo (Apache 2.0).

**Result (base case):** Implied share price EUR 56.27 vs market EUR 48.55 = **+16% moderate upside**. Bear case EUR 32 (-34%), bull case EUR 70 (+45%).

## What this repo contains

- `comps-analysis.md` + `comps-inditex.xlsx` — Comparable company analysis vs H&M, Fast Retailing, Next, Gap, Abercrombie
- `dcf-analysis.md` + `dcf-inditex.xlsx` — 10-year discounted cash flow model with WACC build, terminal value (blended perpetuity + exit multiple), 3 scenarios, sensitivity tables
- `dcf-inputs.json` — Central source of truth for all model assumptions
- `compute_dcf.py` — Headless DCF computation script
- `build_dcf_xlsx.py` — Generates the live Excel model with formulas
- `build-comps.py` — Generates the comps Excel
- `audit_xls.py` — Programmatic audit (formula errors, hardcodes, DCF logic checks)
- `comps-raw.csv` — Input data for 6 companies

## Methodology

1. **Comps fase:** Pulled key metrics for Inditex + 5 retail apparel peers from stockanalysis.com. Computed margins, valuation multiples, peer statistics (max/75th/median/25th/min). Identified Inditex as best-in-class operator (28.3% EBITDA margin vs peer median 13.4%) cotizing at +40% premium on EV/EBITDA, justified by margin lead.

2. **DCF fase:** 10-year explicit projection of Unlevered Free Cash Flow. WACC via CAPM (Spain RF 3.2% + beta 0.92 * ERP 5.5% = 8.26%). Inditex net cash position EUR 11B simplifies to all-equity WACC. Terminal value blended (perpetuity growth 2.5% + exit multiple 12.0x EBITDA). 3 scenarios: Bear / Base / Bull with full assumption set.

3. **Audit fase:** Programmatic checks via `audit_xls.py`: 185 formulas, 0 error strings, FCF formula structure verified, discount factor references absolute WACC.

4. **Primary source verification:** Cross-checked all key inputs vs Inditex official FY2025 press release (2026-03-11). Identified FY2024 data extraction error in stockanalysis.com and corrected manually. Reconciled "FCF" definition differences (stockanalysis OCF-CapEx vs Inditex post-lease-payment vs DCF unlevered).

## Key findings

| Insight | Detail |
|---|---|
| Best-in-class margins | EBITDA margin 28.3% vs peer max 20.6% (Next) |
| Premium vs peers | +40% on EV/EBITDA, +30% on P/E |
| Premium justified | By margin lead, brand portfolio, supply chain, net cash position |
| Net cash | EUR 11B = 6% of equity value, optionality for buybacks/M&A |
| Beta 0.92 | Defensive, keeps WACC low |
| Terminal % of EV | 60.8% (within 50-70% sanity band) |
| Critical assumption | Margin sustainability > growth |
| Brand concentration | Zara 70% of revenue |
| Geographic | Europe 67%, Americas 18%, Asia 15% |
| Online | 27% of sales |

## Reproduction

```bash
python -m pip install openpyxl  # if not installed
python compute_dcf.py           # headless DCF, prints summary
python build_dcf_xlsx.py        # generates dcf-inditex.xlsx
python build-comps.py           # generates comps-inditex.xlsx
python audit_xls.py             # runs audit on the DCF xlsx
```

Modify assumptions in `dcf-inputs.json` and rerun.

## Stack

- Python 3.14 (Windows ARM64 compatible)
- openpyxl 3.1.5 (pure Python, no native bindings)
- Anthropic `financial-services` plugin (Apache 2.0), `dcf-model` + `comps-analysis` + `audit-xls` skills
- Data sources: stockanalysis.com (aggregator), Inditex official IR (primary), Damodaran NYU (ERP)

## Limitations

1. FY2024 stockanalysis.com data extraction had error (29.4B vs actual 38.6B). Corrected manually.
2. Sensitivity table holds sum PV FCFs constant at base WACC (varies only terminal). For full re-runs at different WACC, edit `dcf-inputs.json`.
3. No quarterly model, no 3-statement integration. Add for production-grade.
4. Single point in time snapshot.
5. Operating lease liabilities (IFRS 16) embedded in EBITDA/D&A, not separately modeled.

## Disclaimer

NOT INVESTMENT ADVICE. This is an educational case study and analyst work product showcasing the application of Anthropic's open-source financial-services skills to a real public company. Nothing herein constitutes a buy, sell, or hold recommendation. Past performance does not predict future results. Verify all figures against Inditex official annual report (https://www.inditex.com/itxcomweb/en/investors) before any investment decision.

Per the Anthropic FSI repo README: "These agents draft analyst work product — models, memos, research notes, reconciliations — for review by a qualified professional."

## Attribution

This work derives from [anthropics/financial-services](https://github.com/anthropics/financial-services) (Apache 2.0). The skill prompts and methodological framework are Anthropic's. The Inditex-specific data, analysis, and Python implementation are original work.

## License

Apache License 2.0. See `LICENSE` file.

## Author

Andres Lince  
IMBA Candidate, IE Business School  
linceandres7@gmail.com  
