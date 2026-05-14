# Equity Valuation Toolkit (DCF + Comps + Web App)

End-to-end equity valuation toolkit built on Anthropic's open-source [financial-services](https://github.com/anthropics/financial-services) skills (Apache 2.0). Works for **any listed equity**.

**Two ways to use:**
1. **Web app** (Streamlit): enter ticker, get instant DCF + comps + downloads. Deploy free on Streamlit Cloud. See [DEPLOY.md](DEPLOY.md).
2. **CLI scripts**: fill JSON + CSV manually, run Python scripts. See "Quick start" below.

## What it does

For a given company + 5 listed peers, generates:

1. **Comps analysis** — operating metrics + valuation multiples + statistics (max / 75th / median / 25th / min) in a publication-grade Excel file
2. **DCF model** — 10-year explicit projection, WACC build via CAPM, blended terminal value, 3 scenarios (Bear / Base / Bull), sensitivity tables
3. **Programmatic audit** — formula error check, DCF logic verification, sanity bands

Output: 2 Excel files + Python scripts to reproduce + written memo per case.

## Quick start (web app, recommended)

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open http://localhost:8501. Enter ticker (e.g. `AAPL`), peer tickers, click **Fetch data**. App auto-pulls 5Y financials, computes DCF, generates charts, downloads xlsx + memo.

For free public hosting on Streamlit Cloud see [DEPLOY.md](DEPLOY.md).

**Note:** Streamlit needs pyarrow which lacks Windows ARM64 wheels. Local dev on Win ARM64 requires WSL2 or x86 emulation. Production deploy on Streamlit Cloud (Linux) works.

## Quick start (CLI scripts)

```bash
pip install openpyxl

# Run Inditex showcase case
python compute_dcf.py --inputs cases/inditex/inputs.json
python build_dcf_xlsx.py --inputs cases/inditex/inputs.json --output cases/inditex/dcf.xlsx
python build_comps.py --inputs cases/inditex/inputs.json --output cases/inditex/comps.xlsx
python audit_xls.py --xlsx cases/inditex/dcf.xlsx
```

## Add a new company

```bash
# Copy templates
mkdir cases/microsoft
cp template/inputs.template.json cases/microsoft/inputs.json
cp template/peers.template.csv cases/microsoft/peers.csv

# Fill in financial data (see docs/adding-a-new-company.md)

# Run
python compute_dcf.py --inputs cases/microsoft/inputs.json
python build_dcf_xlsx.py --inputs cases/microsoft/inputs.json --output cases/microsoft/dcf.xlsx
```

Full step-by-step guide: [docs/adding-a-new-company.md](docs/adding-a-new-company.md).

## Showcase case: Inditex (BME:ITX)

Live example in `cases/inditex/`. Findings:

- Base case implied EUR 56 / share vs market EUR 48 → +16% moderate upside
- Best-in-class operator: 28% EBITDA margin vs peer median 13%
- Trades +40% premium to peer median EV/EBITDA, justified by margin lead
- Net cash EUR 11B, beta 0.92 → low WACC 8.26%
- Bear case EUR 32 (-34%), Bull case EUR 70 (+45%)

Full memo: `cases/inditex/dcf-analysis.md`.

## Repository structure

```
.
├── README.md                       # This file
├── LICENSE                         # Apache 2.0 + Anthropic attribution
├── LINKEDIN-POST.md                # Drafts for case study sharing
├── compute_dcf.py                  # Headless DCF computation
├── build_dcf_xlsx.py               # Generates DCF Excel
├── build_comps.py                  # Generates comps Excel
├── audit_xls.py                    # Programmatic model audit
├── template/
│   ├── inputs.template.json        # Blank DCF inputs template
│   └── peers.template.csv          # Blank peer set template
├── cases/
│   └── inditex/                    # Showcase case
│       ├── inputs.json
│       ├── peers.csv
│       ├── dcf-analysis.md
│       ├── comps-analysis.md
│       ├── dcf.xlsx
│       └── comps.xlsx
└── docs/
    └── adding-a-new-company.md     # Step-by-step guide
```

## Methodology

### DCF approach

10-year explicit projection of Unlevered Free Cash Flow:

```
EBIT * (1 - tax rate) = NOPAT
+ D&A
- CapEx
- Change in NWC
= Unlevered FCF
```

Discounted at WACC via CAPM: Cost of Equity = Rf + Beta * ERP.

Terminal value blended (perpetuity growth + exit EV/EBITDA multiple) for robustness.

Mid-year discount convention (periods 0.5, 1.5, ... 9.5).

### Comps approach

5-6 listed peers, same business model + scale + geography mix.

Operating metrics: Revenue, Gross Margin, EBITDA Margin, Op Margin, Net Margin.

Valuation multiples: EV/Sales, EV/EBITDA, P/E (TTM and Forward), Beta.

Statistics per metric: Max, 75th percentile, Median, 25th percentile, Min.

### Audit

Programmatic checks (no Excel required):
- Formula error strings (#REF!, #DIV/0!, #VALUE!, #N/A, #NAME?)
- FCF formula structure: NOPAT + D&A - CapEx - ΔNWC
- Discount factor absolute reference to WACC
- WACC formula references cost of equity
- Hardcode warnings (numeric literals in formulas)

## Stack

- Python 3.11+ (tested on 3.14 ARM64 Windows)
- openpyxl 3.1.5 (pure Python, no native deps)
- Anthropic `financial-services` skill prompts (Apache 2.0)

Pure-Python design: works on any platform including Windows ARM64.

## What this is NOT

- **Not investment advice.** Educational tool and analyst work product.
- **Not a Bloomberg replacement.** Data quality depends on what you put in.
- **Not for banks or insurance.** Use DDM or Residual Income for those.
- **Not for pre-revenue startups.** No cash flows to discount.
- **Not auto-pull data.** You fill the JSON / CSV. Future v2 could integrate APIs.

## Limitations (current)

1. Sensitivity table varies only terminal at base WACC. For full WACC sensitivity, edit inputs.json and rerun.
2. No 3-statement integration (IS/BS/CF not linked).
3. Operating lease liabilities (IFRS 16) embedded in EBITDA, not separately modeled.
4. Single snapshot, no multi-period or quarterly view.
5. Manual data entry from public sources (stockanalysis.com, IR pages, Damodaran).

See `docs/adding-a-new-company.md` for workarounds and v2 roadmap.

## Disclaimer

NOT INVESTMENT ADVICE. This toolkit produces analyst work product for review by a qualified professional. Verify all figures against the company's official annual report before any investment decision.

Per Anthropic's FSI repo README: "These agents draft analyst work product — models, memos, research notes, reconciliations — for review by a qualified professional."

## Attribution

Built on top of [anthropics/financial-services](https://github.com/anthropics/financial-services) (Apache 2.0):
- `dcf-model` skill (methodology framework)
- `comps-analysis` skill (structure + conventions)
- `audit-xls` skill (audit checklist)

Skill prompts and methodology by Anthropic. Python implementation, case data, and analytical conclusions are original work.

## License

Apache License 2.0. See `LICENSE`.

## Author

Private project.
