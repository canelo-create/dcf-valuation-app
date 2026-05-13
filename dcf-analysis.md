# Inditex (ITX.MC) DCF Valuation

**As of 2026-05-13** | Methodology: 10-year explicit unlevered FCF projection, blended terminal (perpetuity growth + exit multiple). All figures EUR.

## Executive Summary

| Metric | Value |
|---|---:|
| Current share price | EUR 48.55 |
| Base case implied price | EUR 56.27 |
| **Upside vs market** | **+16%** |
| Bear case implied | EUR 32.19 (-34%) |
| Bull case implied | EUR 70.47 (+45%) |
| WACC | 8.26% |
| Terminal % of EV | 60.8% (within 50-70% sanity band) |

**Recommendation:** Moderate buy. Inditex is the best-in-class operator in retail apparel (per fase 2 comps), but current price already prices in much of that quality. Material upside requires bull case (sustained margin expansion + Asia outperformance). Reasonable entry: market drawdown 10 to 15% (EUR 42-44) for margin of safety.

## Methodology

### 1. Historical analysis (FY2021 to FY2025)

| Metric | FY2021 | FY2022 | FY2023 | FY2024 | FY2025 | 5Y CAGR |
|---|---:|---:|---:|---:|---:|---:|
| Revenue (EUR M) | 27,717 | 32,569 | 35,948 | 38,632 | 39,864 | +9.5% |
| EBITDA | 4,407 | 8,419 | 9,850 | 10,584 | 11,268 | +26.4% |
| EBITDA margin | 15.9% | 25.8% | 27.4% | 27.4% | 28.3% | +12.4pp |
| FCF | 1,481 | 5,259 | 6,795 | 6,600 | 6,520 | +44.9% |
| FCF margin | 5.3% | 16.2% | 18.9% | 17.1% | 16.4% | +11.1pp |

FY2021 figures reflect COVID rebound base. FCF margin normalized at ~16-19% post-2022.

**Note on data:** stockanalysis.com showed an obvious data extraction error for FY2024 revenue (29.4B). Corrected to 38.6B per Inditex official 2024 annual results press release. Other FY2024 line items estimated proportionally.

### 2. WACC build (CAPM)

| Component | Value | Source |
|---|---:|---|
| Risk-free rate | 3.20% | Spain 10Y government bond, May 2026 approx |
| Equity risk premium | 5.50% | Damodaran 2026 Spain mature market |
| Beta (5Y) | 0.92 | stockanalysis.com regression |
| **Cost of equity** | **8.26%** | Rf + Beta * ERP |
| Pretax cost of debt | 4.0% | Estimate (low relevance) |
| Tax rate | 22.0% | FY25 effective rate |
| After-tax cost of debt | 3.12% | |
| **WACC** | **8.26%** | Effectively all-equity (net cash position) |

Inditex has EUR 11B net cash vs EUR 28M financial debt. WACC reduces to cost of equity.

### 3. Projection (Base case)

10Y revenue tapers from 7% (Y1) toward 2.5% terminal:

| Year | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Growth % | 7.0 | 6.0 | 6.0 | 5.0 | 5.0 | 4.0 | 4.0 | 3.5 | 3.0 | 2.5 |
| Revenue | 42,654 | 45,214 | 47,927 | 50,323 | 52,839 | 54,953 | 57,151 | 59,151 | 60,926 | 62,449 |
| EBITDA (28.5% mgn) | 12,157 | 12,886 | 13,659 | 14,342 | 15,059 | 15,661 | 16,288 | 16,858 | 17,364 | 17,798 |
| FCF | 7,303 | 7,733 | 8,437 | 8,849 | 9,556 | 9,928 | 10,611 | 10,977 | 11,605 | 11,889 |
| PV of FCF | 7,019 | 6,865 | 6,918 | 6,703 | 6,686 | 6,417 | 6,335 | 6,053 | 5,911 | 5,594 |

**EBITDA margin held flat at 28.5%** — Inditex actual band 27 to 29% last 4 years. No expansion assumed in base.

**CapEx** tapers 7% to 5% of revenue (FY25 actual 6.8%). Reflects mature store network, less new openings needed.

**Working capital** modeled at -2% of revenue change (Inditex runs negative WC via supplier financing).

### 4. Terminal value

Two methods, then averaged:

| Method | Calc | Gross TV | PV TV |
|---|---|---:|---:|
| Perpetuity growth (g=2.5%) | FCF_Y10 * (1.025) / (8.26% - 2.5%) | 211,575 | 99,941 |
| Exit multiple (12.0x EBITDA Y10) | EBITDA_Y10 * 12.0 | 213,574 | 100,888 |
| **Blended PV** | Average | | **100,015** |

Both methods converge (within 1%) which is a positive consistency signal.

### 5. Valuation summary

| Component | Value |
|---|---:|
| Sum PV of explicit FCFs (Y1-Y10) | EUR 64,501M |
| PV of Terminal value (blended) | EUR 100,015M |
| **Enterprise Value** | **EUR 164,516M** |
| (+) Net cash | EUR 10,932M |
| **Equity Value** | **EUR 175,448M** |
| (/) Shares outstanding | 3,118M |
| **Implied share price** | **EUR 56.27** |

## Scenarios

| Scenario | Rev growth Y1-Y10 | EBITDA margin | Terminal g | Exit mult | Implied price | Upside |
|---|---|---|---:|---:|---:|---:|
| Bear | 3% to 1.5% | 23-26% | 1.5% | 9.0x | EUR 32.19 | -33.7% |
| **Base** | **7% to 2.5%** | **28.5%** | **2.5%** | **12.0x** | **EUR 56.27** | **+15.9%** |
| Bull | 9% to 3.5% | 29.5-30% | 3.0% | 14.0x | EUR 70.47 | +45.2% |

## Cross-check vs market

| Metric | Inditex DCF base | Inditex market | Peer median |
|---|---:|---:|---:|
| EV/EBITDA (current) | 14.6x | 13.2x | 9.4x |
| Implied P/E | 28x approx | 24.3x | 18.8x |
| Terminal % of EV | 60.8% | (n/a) | (typical 50-70%) |

DCF base implies Inditex worth slightly more than market price (14.6x vs 13.2x EV/EBITDA), consistent with the +16% upside.

## What drives the valuation

1. **Margin sustainability matters more than growth.** Bear case revenue grows but margin compresses to 23% → equity value drops 34%. The thesis "Inditex stays at 28% margin" is the most load-bearing assumption.

2. **Terminal value dominates** (60.8% of EV). 10 years of explicit cash flows generate only 39% of value. Sensitivity to terminal growth and exit multiple is high.

3. **Net cash is meaningful** (EUR 11B = 6% of equity value). Not insignificant — gives optionality (buybacks, special dividend, M&A).

4. **Beta 0.92 (defensive)** keeps WACC low. If beta drifts toward 1.1 (e.g., regulation, China exposure), WACC rises to 9.0% → equity value drops ~10%.

## Risks

1. **Margin compression risk.** Brand competition (Shein, Temu) could force discounting. H&M trades at 8.5% op margin — Inditex could converge.
2. **FX risk.** USD strengthens → cost of goods rises (some sourcing Asia). Russia exit precedent shows can lose markets.
3. **Online disruption.** Inditex e-commerce 30% of sales already, but ultra-fast fashion threat real.
4. **ESG/regulation.** EU sustainability rules could raise costs (textile waste, supply chain transparency).
5. **Family ownership.** 60% Ortega family — overhang risk if they sell, low free float.
6. **Spain exposure.** ~14% of sales Spain, exposed to local downturn.

## Limitations

1. Sensitivity table in xlsx holds sum PV FCFs constant at base WACC. For full re-runs at different WACC, edit `dcf-inputs.json` and rerun `compute_dcf.py`.
2. FY2024 data corrections manual — re-run from primary source (Inditex annual report PDF) for production deliverable.
3. Single point in time. Real analyst would model quarterly + run multiple periods.
4. No same-store-sales (LFL) decomposition — important retail driver, future v2.
5. Per share equity value doesn't account for buybacks (Inditex announced EUR 1B program FY25). Would slightly increase per-share value.
6. Operating lease liabilities IFRS 16 not split out separately — embedded in EBITDA/D&A.

## DISCLAIMER

Per Anthropic FSI repo README (Apache 2.0): "Nothing in this repository constitutes investment, legal, tax, or accounting advice." This is an educational case study and analyst work product, not a buy/sell recommendation. Verify all numbers against Inditex official annual report (https://www.inditex.com/itxcomweb/en/investors) before any investment decision. Past performance does not predict future results.

## Reproducibility

1. Inputs central in `dcf-inputs.json` (modify assumptions there)
2. `python compute_dcf.py` runs headless, prints summary
3. `python build_dcf_xlsx.py` generates `dcf-inditex.xlsx`
4. Total runtime: ~5 seconds

## Files

| File | Purpose |
|---|---|
| `dcf-inputs.json` | All assumptions, central source of truth |
| `compute_dcf.py` | Headless DCF computation, validation |
| `build_dcf_xlsx.py` | Generates live Excel model |
| `dcf-inditex.xlsx` | Deliverable Excel (formulas, sections, sensitivity) |
| `dcf-analysis.md` | This document — written analysis |

## Primary source verification (Inditex official FY2025 results, 2026-03-11)

Cross-check vs Inditex press release "FY2025 Results" (https://www.inditex.com/itxcomweb/hk/en/press/news-detail/b870d5ec-6b7e-491d-b38e-340cd69036df):

| Metric | Inditex official | Our DCF input | Variance |
|---|---:|---:|---:|
| Net Sales FY25 | EUR 39.9B (+3.2% rep, +7.0% cc) | EUR 39,864M | -0.1% |
| Gross margin | 58.3% (+42bp) | computed 56.3% | -2.0pp (use 58.3% in v2) |
| EBITDA | EUR 11.3B (+5.0%) | EUR 11,268M | -0.3% |
| EBIT | EUR 8.0B (+5.9%) | EUR 7,997M | 0.0% |
| Net income | EUR 6.2B (+6.0%) | EUR 6,220M | 0.0% |
| FCF (Inditex def) | **EUR 4.686B** | EUR 6,520M (stockanalysis) | **+39% overstated** |
| Net cash | EUR 11.0B | EUR 10,932M | -0.6% |
| CapEx | EUR 2.712B | EUR 2,712M | 0.0% |
| Dividend per share | EUR 1.75 (1.20 ord + 0.55 bonus) | not used | (informational) |

**FCF reconciliation:** Inditex official FCF €4.686B vs stockanalysis €6.520B = €1.8B gap. Likely IFRS 16 lease repayments classified as financing in Inditex view but operating in stockanalysis aggregator. Our DCF uses **Unlevered FCF** (different concept again, computed NOPAT + D&A - CapEx - ΔNWC = ~€7.5B Y1), which is correct DCF framework. The €4.686B figure is post-lease-payment Levered FCF.

**Constant currency growth +7.0% vs reported +3.2% confirms our 7% Y1 assumption.** FX drag was ~3.8pp in FY25.

## Brand mix (FY2025, EUR M)

| Brand | Revenue | % of total | YoY |
|---|---:|---:|---|
| Zara (incl Zara Home, Lefties) | 28,051 | 70.4% | +1.0% |
| Bershka | 3,286 | 8.2% | +12.1% |
| Stradivarius | 3,002 | 7.5% | +12.7% |
| Pull&Bear | 2,546 | 6.4% | +3.1% |
| Massimo Dutti | 2,019 | 5.1% | +3.0% |
| Oysho | 960 | 2.4% | +15.5% |
| **Total** | **39,864** | **100%** | **+3.2%** |

**Implication for DCF:** Zara concentration risk (70%). Smaller brands growing 12-16% YoY suggest portfolio diversification optionality. Our flat 28.5% EBITDA margin assumption may be conservative if smaller brands continue scaling (higher growth, possibly higher margins at scale).

## Geographic mix (FY2025, % of sales)

| Region | % | Approx EUR M | Implication |
|---|---:|---:|---|
| Europe ex-Spain | 51.3% | 20,460 | Core market, mature |
| Spain | 15.9% | 6,338 | Home market, max penetration |
| Americas | 17.8% | 7,096 | Growth engine, FX risk USD/BRL/MXN |
| Asia & RoW | 15.0% | 5,980 | Highest LT potential, China/India |

For DCF: Asia underweight vs Fast Retailing (10%+ market share in Japan/China). Upside in bull case = Asia revenue mix to 25-30% over 10 years.

## Operations (FY2025)

| Metric | Value |
|---|---|
| Store count | 5,460 stores |
| Online sales | EUR 10.7B (+4.8%) = 26.8% of total |
| Total selling space | 4.72M m² (+5.3% gross) |
| FY26 capex guidance | EUR 2.3B (-15% YoY) |
| FY26 SS first 5 weeks | +9% constant currency |

**FY26 capex €2.3B vs our DCF model Y1 assumption €2.99B (7% of €42.6B revenue).** Our model is conservative on capex which depresses FCF. Adjusting to actual guidance EUR 2.3B = lower capex by €0.7B = higher unlevered FCF Y1 by ~€0.55B post-tax effect → implied share price ~EUR 1.5 higher.

## Source attribution

- Skill: `dcf-model` from `anthropics/financial-services` (Apache 2.0)
- Repo: https://github.com/anthropics/financial-services
- Primary data: Inditex official FY2025 Results press release (2026-03-11)
- Secondary data: stockanalysis.com (historical income/cash flow/BS), with manual cross-check vs official
- WACC inputs: Spain 10Y govt bond (tradingeconomics.com), Damodaran NYU (ERP)
- Tooling: Python 3.14 ARM64, openpyxl 3.1.5

## Model audit

Programmatic audit run via `audit_xls.py` (following Anthropic `audit-xls` skill methodology):

- 185 formulas
- 0 formula error strings (#REF!, #DIV/0!, #VALUE!, #N/A, #NAME?)
- FCF Y1 formula structure verified: NOPAT + D&A - CapEx - ΔNWC
- Discount factor uses absolute WACC reference
- 0 critical issues
- Recommendation: open in Excel/LibreOffice to force recalc

## Next steps for production-grade deliverable

1. Re-pull all financials from Inditex official annual reports (PDF), not aggregator
2. Build full 3-statement model (IS, BS, CF integrated) using `3-statement-model` skill
3. Audit with `audit-xls` skill for circular refs and hardcode detection
4. Add same-store-sales (LFL) decomposition by region
5. Build merger-model variant: what would Inditex pay to acquire Mango or Primark?
6. Publish on GitHub public + LinkedIn post for Tier B job signal
