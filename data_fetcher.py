"""Fetch financial data for a ticker via yfinance (primary).

Returns a dict matching the inputs.json schema used by compute_dcf.py.

Usage:
    from data_fetcher import fetch_company, fetch_peers

    inputs = fetch_company("AAPL", peer_tickers=["MSFT", "GOOG", "META", "AMZN"])
"""

import datetime as dt
from typing import Optional

import yfinance as yf


def _safe(d, key, default=0):
    """Get value from dict, treat None as default."""
    v = d.get(key) if d else None
    return default if v is None else v


def _to_millions(value):
    if value is None:
        return 0
    try:
        return float(value) / 1_000_000
    except (TypeError, ValueError):
        return 0


def _coerce_int(value, default=0):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def fetch_company(ticker: str, peer_tickers: Optional[list] = None, as_of_date: Optional[str] = None) -> dict:
    """Fetch all data needed for DCF + comps for a ticker.

    Args:
        ticker: e.g. "AAPL", "ITX.MC"
        peer_tickers: list of peer tickers for comps
        as_of_date: ISO date string, defaults to today

    Returns:
        dict matching inputs.json schema
    """
    if as_of_date is None:
        as_of_date = dt.date.today().isoformat()

    yt = yf.Ticker(ticker)
    info = yt.info or {}
    company = info.get("longName") or info.get("shortName") or ticker
    currency = info.get("currency") or "USD"
    fy_end = info.get("lastFiscalYearEnd")
    fy_end_str = "December 31"
    if fy_end:
        try:
            fy_end_str = dt.datetime.fromtimestamp(fy_end).strftime("%B %d")
        except Exception:
            pass

    # Market data
    shares = _coerce_int(_safe(info, "sharesOutstanding"))
    price = _safe(info, "currentPrice") or _safe(info, "regularMarketPrice", 0)
    mcap = _coerce_int(_safe(info, "marketCap"))
    cash = _coerce_int(_safe(info, "totalCash"))
    debt = _coerce_int(_safe(info, "totalDebt"))
    ev = _coerce_int(_safe(info, "enterpriseValue"))
    beta = _safe(info, "beta", 1.0)
    book_equity = _coerce_int(_safe(info, "bookValue", 0) * shares) if _safe(info, "bookValue") else 0

    net_cash = cash - debt
    if not ev:
        ev = mcap - net_cash if mcap else 0

    # Historical financials (5 years if available)
    income = yt.income_stmt
    cash_flow = yt.cash_flow
    historical = {}
    if income is not None and not income.empty:
        cols = sorted(income.columns)[-5:]
        for col in cols:
            year = col.year if hasattr(col, "year") else int(str(col)[:4])
            fy_key = f"FY{year}"
            rev = _coerce_int(income.get(col, {}).get("Total Revenue") if hasattr(income.get(col, {}), "get") else income[col].get("Total Revenue") if col in income.columns else None)
            try:
                rev = int(income.loc["Total Revenue", col]) if "Total Revenue" in income.index else 0
            except (KeyError, ValueError, TypeError):
                rev = 0
            try:
                ebit = int(income.loc["EBIT", col]) if "EBIT" in income.index else 0
            except (KeyError, ValueError, TypeError):
                ebit = 0
            try:
                ebitda = int(income.loc["EBITDA", col]) if "EBITDA" in income.index else ebit
            except (KeyError, ValueError, TypeError):
                ebitda = ebit
            try:
                da = ebitda - ebit if ebitda and ebit else 0
            except (TypeError, ValueError):
                da = 0
            try:
                net_income = int(income.loc["Net Income", col]) if "Net Income" in income.index else 0
            except (KeyError, ValueError, TypeError):
                net_income = 0
            try:
                tax = int(income.loc["Tax Provision", col]) if "Tax Provision" in income.index else 0
            except (KeyError, ValueError, TypeError):
                tax = 0
            try:
                pretax = int(income.loc["Pretax Income", col]) if "Pretax Income" in income.index else net_income + tax
            except (KeyError, ValueError, TypeError):
                pretax = net_income + tax

            capex = 0
            ocf = 0
            fcf = 0
            if cash_flow is not None and not cash_flow.empty and col in cash_flow.columns:
                try:
                    capex = abs(int(cash_flow.loc["Capital Expenditure", col])) if "Capital Expenditure" in cash_flow.index else 0
                except (KeyError, ValueError, TypeError):
                    capex = 0
                try:
                    ocf = int(cash_flow.loc["Operating Cash Flow", col]) if "Operating Cash Flow" in cash_flow.index else 0
                except (KeyError, ValueError, TypeError):
                    ocf = 0
                try:
                    fcf = int(cash_flow.loc["Free Cash Flow", col]) if "Free Cash Flow" in cash_flow.index else ocf - capex
                except (KeyError, ValueError, TypeError):
                    fcf = ocf - capex

            historical[fy_key] = {
                "period_end": str(col)[:10] if hasattr(col, "year") else str(col),
                "revenue": rev // 1_000_000 if rev else 0,
                "ebitda": ebitda // 1_000_000 if ebitda else 0,
                "ebit": ebit // 1_000_000 if ebit else 0,
                "da": da // 1_000_000 if da else 0,
                "capex": capex // 1_000_000 if capex else 0,
                "ocf": ocf // 1_000_000 if ocf else 0,
                "fcf": fcf // 1_000_000 if fcf else 0,
                "tax": tax // 1_000_000 if tax else 0,
                "pretax": pretax // 1_000_000 if pretax else 0,
                "net_income": net_income // 1_000_000 if net_income else 0,
            }

    if not historical:
        # Fallback: synthetic single year from current TTM
        rev_ttm = _safe(info, "totalRevenue", 0)
        ebitda_ttm = _safe(info, "ebitda", 0)
        ni_ttm = _safe(info, "netIncomeToCommon", 0)
        fy_key = f"FY{dt.date.today().year - 1}"
        historical[fy_key] = {
            "period_end": as_of_date,
            "revenue": rev_ttm // 1_000_000 if rev_ttm else 0,
            "ebitda": ebitda_ttm // 1_000_000 if ebitda_ttm else 0,
            "ebit": (ebitda_ttm or 0) * 70 // 100 // 1_000_000,
            "da": (ebitda_ttm or 0) * 30 // 100 // 1_000_000,
            "capex": 0,
            "ocf": 0,
            "fcf": (ni_ttm or 0) // 1_000_000,
            "tax": 0,
            "pretax": (ni_ttm or 0) // 1_000_000,
            "net_income": (ni_ttm or 0) // 1_000_000,
        }

    # Build inputs dict matching schema
    inputs = {
        "company": company,
        "ticker": ticker,
        "currency": currency,
        "as_of_date": as_of_date,
        "fiscal_year_end": fy_end_str,
        "data_sources": {
            "income_statement": f"yfinance ({ticker})",
            "cash_flow": f"yfinance ({ticker})",
            "balance_sheet": f"yfinance ({ticker})",
            "comps": "peers.csv (in memory)",
            "risk_free_source": "Default 4.0% (US 10Y). Override in app.",
            "erp_source": "Damodaran 5.5% default. Override in app.",
        },
        "historical": historical,
        "market_data": {
            "shares_outstanding_m": shares // 1_000_000 if shares else 0,
            "current_price_eur": float(price),
            "market_cap_eur_m": mcap // 1_000_000 if mcap else 0,
            "cash_and_st_investments_eur_m": cash // 1_000_000 if cash else 0,
            "total_financial_debt_eur_m": debt // 1_000_000 if debt else 0,
            "net_cash_eur_m": net_cash // 1_000_000,
            "enterprise_value_eur_m": ev // 1_000_000 if ev else 0,
            "book_equity_eur_m": book_equity // 1_000_000 if book_equity else 0,
            "beta_5y": float(beta),
        },
        "wacc": _default_wacc(beta, currency),
        "projection_assumptions_base": _default_projection("base"),
        "projection_assumptions_bear": _default_projection("bear"),
        "projection_assumptions_bull": _default_projection("bull"),
        "sensitivity_ranges": {
            "wacc_pct": [6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5],
            "terminal_growth_pct": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
            "exit_multiple": [9.0, 10.5, 12.0, 13.5, 15.0],
        },
    }

    if peer_tickers:
        inputs["peers_data"] = fetch_peers(peer_tickers, as_of_date)

    return inputs


def fetch_peer(ticker: str, as_of_date: str) -> dict:
    """Fetch comps data for a single peer."""
    yt = yf.Ticker(ticker)
    info = yt.info or {}
    name = info.get("longName") or info.get("shortName") or ticker
    currency = info.get("currency") or "USD"

    return {
        "Company": name,
        "Ticker": ticker,
        "Currency": currency,
        "Revenue_TTM_LCY": _safe(info, "totalRevenue", 0),
        "Gross_Profit_TTM_LCY": _safe(info, "grossProfits", 0),
        "EBITDA_TTM_LCY": _safe(info, "ebitda", 0),
        "Net_Income_TTM_LCY": _safe(info, "netIncomeToCommon", 0),
        "Operating_Margin_pct": _safe(info, "operatingMargins", 0) * 100,
        "Net_Margin_pct": _safe(info, "profitMargins", 0) * 100,
        "Market_Cap_LCY": _safe(info, "marketCap", 0),
        "Enterprise_Value_LCY": _safe(info, "enterpriseValue", 0),
        "EV_Sales": _safe(info, "enterpriseToRevenue", 0),
        "EV_EBITDA": _safe(info, "enterpriseToEbitda", 0),
        "PE_Trailing": _safe(info, "trailingPE", 0),
        "PE_Forward": _safe(info, "forwardPE", 0),
        "Beta_5Y": _safe(info, "beta", 1.0),
        "Shares_Outstanding": _safe(info, "sharesOutstanding", 0),
        "Stock_Price_LCY": _safe(info, "currentPrice", 0) or _safe(info, "regularMarketPrice", 0),
        "Total_Cash_LCY": _safe(info, "totalCash", 0),
        "Total_Debt_LCY": _safe(info, "totalDebt", 0),
        "As_of_Date": as_of_date,
    }


def fetch_peers(tickers: list, as_of_date: str) -> list:
    """Fetch comps data for multiple peers."""
    return [fetch_peer(t, as_of_date) for t in tickers]


def _default_wacc(beta: float, currency: str) -> dict:
    """Sensible defaults; user should override in UI."""
    if currency == "EUR":
        rf = 3.2
        rf_src = "Spain/Germany 10Y bond (avg)"
    elif currency == "GBP":
        rf = 4.2
        rf_src = "UK 10Y Gilt"
    elif currency == "JPY":
        rf = 1.5
        rf_src = "Japan 10Y JGB"
    else:
        rf = 4.0
        rf_src = "US 10Y Treasury"

    erp = 5.5
    cost_of_equity = rf + beta * erp
    tax = 22.0
    pretax_debt = 5.0
    after_tax_debt = pretax_debt * (1 - tax / 100)

    return {
        "risk_free_rate_pct": rf,
        "risk_free_source": rf_src,
        "equity_risk_premium_pct": erp,
        "erp_source": "Damodaran current ERP",
        "beta": beta,
        "cost_of_equity_pct": round(cost_of_equity, 2),
        "pretax_cost_of_debt_pct": pretax_debt,
        "tax_rate_pct": tax,
        "after_tax_cost_of_debt_pct": round(after_tax_debt, 2),
        "equity_weight_pct": 100.0,
        "debt_weight_pct": 0.0,
        "wacc_pct": round(cost_of_equity, 2),
        "note": "Default WACC; review and adjust in UI.",
    }


def _default_projection(scenario: str) -> dict:
    if scenario == "base":
        growth = [7.0, 6.0, 6.0, 5.0, 5.0, 4.0, 4.0, 3.5, 3.0, 2.5]
        margin = [25.0] * 10
        capex = [6.0, 6.0, 5.5, 5.5, 5.0, 5.0, 4.5, 4.5, 4.0, 4.0]
        tg = 2.5
        em = 12.0
    elif scenario == "bear":
        growth = [3.0, 2.0, 2.0, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5]
        margin = [22.0, 21.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0]
        capex = [6.0, 6.0, 5.5, 5.5, 5.0, 5.0, 4.5, 4.5, 4.0, 4.0]
        tg = 1.5
        em = 9.0
    else:  # bull
        growth = [9.0, 8.0, 7.0, 7.0, 6.0, 6.0, 5.0, 5.0, 4.0, 3.5]
        margin = [27.0, 28.0, 28.0, 28.0, 28.0, 28.0, 28.0, 28.0, 28.0, 28.0]
        capex = [6.0, 6.0, 5.5, 5.5, 5.0, 5.0, 4.5, 4.5, 4.0, 4.0]
        tg = 3.0
        em = 14.0

    return {
        "horizon_years": 10,
        "revenue_growth_yoy_pct": growth,
        "ebitda_margin_pct": margin,
        "da_pct_of_revenue": [5.0] * 10,
        "capex_pct_of_revenue": capex,
        "nwc_change_pct_of_revenue_change": 2.0,
        "tax_rate_pct": 22.0,
        "terminal_growth_pct": tg,
        "exit_multiple_ev_ebitda": em,
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--peers", default="", help="Comma-separated peer tickers")
    args = parser.parse_args()
    peers = [t.strip() for t in args.peers.split(",") if t.strip()] if args.peers else None
    inputs = fetch_company(args.ticker, peer_tickers=peers)
    print(json.dumps(inputs, indent=2, default=str)[:2000])
