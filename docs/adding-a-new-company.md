# Adding a new company

Step-by-step guide to value any listed equity using this toolkit.

## Estimated time

| Step | Time |
|---|---:|
| Create case folder + copy templates | 1 min |
| Fill inputs.json (market data + historicals) | 20-40 min |
| Fill peers.csv (target + 5 peers) | 20-30 min |
| Tune WACC + projection assumptions | 15-30 min |
| Run scripts, review output | 5 min |
| Write analysis memo | 30-60 min |
| **Total** | **~90-180 min** |

## Step 1. Create case folder

```bash
mkdir cases/<companyname>
cp template/inputs.template.json cases/<companyname>/inputs.json
cp template/peers.template.csv cases/<companyname>/peers.csv
```

Example: `cases/microsoft/`, `cases/santander/`, `cases/aapl/`.

## Step 2. Fill inputs.json

### Required fields

| Field | Example | Where to find |
|---|---|---|
| company, ticker, currency | "Apple", "AAPL", "USD" | Company name + exchange ticker |
| as_of_date | "2026-05-13" | Today's date |
| fiscal_year_end | "September 30" | Annual report cover |
| market_data | All numbers | stockanalysis.com/quote/<TICKER>/statistics |
| historical (5 fiscal years) | Revenue, EBITDA, EBIT, D&A, CapEx, FCF, tax, net income | stockanalysis.com/quote/<TICKER>/financials |
| wacc inputs | RF, ERP, beta | tradingeconomics.com (RF), Damodaran (ERP), stockanalysis (beta) |
| projection assumptions | growth, margin, capex % | Your view based on history + guidance |

### WACC quick reference

| Country / sector | Risk-free rate | ERP | Typical WACC |
|---|---:|---:|---:|
| US large cap | 4.0% (10Y Treasury) | 5.0-5.5% | 8-10% |
| Spain | 3.2% (10Y SPGB) | 5.5% | 8-10% |
| UK | 4.2% (10Y Gilt) | 5.0% | 8-10% |
| Japan | 1.5% (10Y JGB) | 5.5% | 6-8% |
| Emerging market large cap | 8-12% (local bond) | 8-12% | 12-18% |

Use Damodaran's country risk premium table for latest: https://pages.stern.nyu.edu/~adamodar/

### Net cash vs net debt

| Position | Equity weight | Debt weight | Implication |
|---|---:|---:|---|
| Net cash (cash > debt) | 100% | 0% | WACC = cost of equity |
| Net debt (debt > cash, normal) | Mkt cap / EV | Net debt / EV | WACC formula full |
| Highly levered | <50% | >50% | Tax shield meaningful |

### Projection scenarios

Defaults work for mature consumer / industrials. Adjust for:

| Business type | Revenue growth | EBITDA margin |
|---|---|---|
| Mature consumer (e.g. Coca-Cola) | 3-5% | 25-30% |
| Growth tech (e.g. CRM SaaS) | 15-30% | 20-40% |
| Cyclical industrial | 0-8% | 10-20% |
| Bank | N/A use DDM/RI, not DCF |
| Commodity producer | Volatile, use mid-cycle |

## Step 3. Fill peers.csv

Pull from stockanalysis.com `/quote/<TICKER>/statistics/` for each peer:

| Column | Source field |
|---|---|
| Revenue_TTM_LCY | Revenue (TTM) |
| Gross_Profit_TTM_LCY | Gross Profit (TTM) |
| EBITDA_TTM_LCY | EBITDA (TTM) |
| Net_Income_TTM_LCY | Net Income (TTM) |
| Operating_Margin_pct | Operating Margin |
| Net_Margin_pct | Net Margin (Profit Margin) |
| Market_Cap_LCY | Market Cap |
| Enterprise_Value_LCY | Enterprise Value |
| EV_Sales | EV/Sales (TTM) |
| EV_EBITDA | EV/EBITDA (TTM) |
| PE_Trailing | Trailing P/E |
| PE_Forward | Forward P/E |
| Beta_5Y | Beta (5Y) |
| Shares_Outstanding | Shares Outstanding |
| Stock_Price_LCY | Current Stock Price |
| Total_Cash_LCY | Total Cash |
| Total_Debt_LCY | Total Debt |

Convert "B" → millions × 1000, "T" → millions × 1,000,000.

**Peer selection criteria:**
1. Same primary business (don't mix retail with banks)
2. Similar scale (within 10x revenue typically OK)
3. Listed, liquid float
4. Recent fiscal year reported
5. 4-6 peers ideal (3 min, 8 max)

## Step 4. Run scripts

```bash
# Compute headless (validate numbers)
python compute_dcf.py --inputs cases/<companyname>/inputs.json

# Generate Excel
python build_dcf_xlsx.py --inputs cases/<companyname>/inputs.json --output cases/<companyname>/dcf.xlsx
python build_comps.py --inputs cases/<companyname>/inputs.json --output cases/<companyname>/comps.xlsx

# Audit
python audit_xls.py --xlsx cases/<companyname>/dcf.xlsx
```

## Step 5. Sanity checks

Before trusting output, verify:

| Check | Acceptable range |
|---|---|
| Terminal % of EV | 50-70% (above 75% red flag) |
| Implied EV/EBITDA (current EBITDA) | Within 50% of market actual |
| Y10 revenue growth | At or near terminal g |
| Implied P/E | Within 30% of market P/E unless thesis demands |
| Bear / Bull spread | Bear -30 to -50%, Bull +30 to +60% (if wider, check assumptions) |
| WACC | 6-12% mature, 12-18% emerging or high growth |
| Beta | 0.5-2.0 (outside range, recompute) |

## Step 6. Write analysis memo

Create `cases/<companyname>/dcf-analysis.md` and `comps-analysis.md`. Use the Inditex case (`cases/inditex/`) as template structure:

- Executive summary table
- Methodology block per section
- Scenarios summary
- Cross-check vs comps
- What drives the valuation (3 to 5 bullets)
- Risks (5 to 8 specific to company)
- Limitations
- Disclaimer

## Common pitfalls

1. **Wrong currency in DCF vs comps.** DCF uses one currency. Comps can mix (multiples currency-neutral). Don't add LCY absolute values across peers.
2. **FCF definition mismatch.** Verify what your source calls "FCF". Many aggregators do OCF - CapEx. Inditex official does post-lease. DCF needs Unlevered (NOPAT + D&A - CapEx - ΔNWC).
3. **Net debt vs net cash.** Negative net debt is net cash, common for top operators (Apple, Inditex, Microsoft).
4. **Tax rate.** Effective tax rate (Tax / Pretax income) varies year-on-year. Use 3Y or 5Y average, not single year spike.
5. **Bank or insurance company.** DCF doesn't work. Use Dividend Discount Model (DDM) or Residual Income.
6. **Pre-revenue startup.** DCF doesn't work. Use VC method or scenarios with optionality.
7. **Commodity producer.** Use mid-cycle commodity price, not spot.

## When DCF is NOT the right tool

| Business type | Better method |
|---|---|
| Bank / insurance | Dividend Discount Model, P/TBV |
| Real estate (REIT) | Net Asset Value, FFO multiple |
| Pre-revenue startup | VC method, comps on user metrics |
| Mature commodity | Mid-cycle multiples |
| Pure cyclical | Through-cycle EPS * P/E |
| Distressed | Liquidation value |

For these, build a comps-only analysis or extend the toolkit.

## Next iteration ideas

- Add `build_3statement_xlsx.py` for integrated IS/BS/CF model
- Add `cases/<co>/dcf-quarterly.json` for quarterly projection
- Add multi-currency comps script with FX conversion
- Integrate Damodaran public dataset via Python script
- Add automated peer screening (input: target ticker, output: 5 best peers)
