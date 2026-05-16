"""Fetch financial data for a ticker via yfinance (primary).

Returns a dict matching the inputs.json schema used by compute_dcf.py.

Usage:
    from data_fetcher import fetch_company, fetch_peers

    inputs = fetch_company("AAPL", peer_tickers=["MSFT", "GOOG", "META", "AMZN"])
"""

import datetime as dt
import os
import time
from typing import Optional

import requests
import yfinance as yf

FMP_BASE = "https://financialmodelingprep.com/stable"


def _fmp_key() -> Optional[str]:
    """Resolve FMP API key from env var or Streamlit secrets. Never hardcoded."""
    k = os.environ.get("FMP_API_KEY")
    if k:
        return k.strip()
    try:
        import streamlit as st
        return st.secrets.get("FMP_API_KEY")
    except Exception:
        return None


def _fmp_get(path: str, symbol: str, key: str, limit: Optional[int] = None, retries: int = 2):
    params = {"symbol": symbol, "apikey": key}
    if limit:
        params["limit"] = limit
    delay = 1.0
    for attempt in range(retries + 1):
        r = requests.get(f"{FMP_BASE}/{path}", params=params, timeout=20)
        if r.status_code == 429:
            if attempt < retries:
                time.sleep(delay)
                delay *= 2  # backoff: 1s, 2s
                continue
            raise RateLimited(f"FMP rate-limit on {path} for {symbol}")
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and data.get("Error Message"):
            raise ValueError(f"FMP error: {data['Error Message'][:120]}")
        return data


def _num(v, default=0):
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def fetch_company_fmp(ticker: str, as_of_date: str) -> dict:
    """Build inputs dict from FMP stable endpoints. Raises if key missing or data unusable."""
    key = _fmp_key()
    if not key:
        raise RuntimeError("no FMP key")

    profile = _fmp_get("profile", ticker, key)
    if not profile:
        raise TickerNotFound(ticker)
    p = profile[0]
    inc = _fmp_get("income-statement", ticker, key, limit=5)
    cf = _fmp_get("cash-flow-statement", ticker, key, limit=5)
    bs = _fmp_get("balance-sheet-statement", ticker, key, limit=1)
    if not inc:
        raise ValueError(f"FMP: sin income statement para {ticker}")

    company = p.get("companyName") or ticker
    currency = p.get("currency") or "USD"
    price = _num(p.get("price"))
    mcap = _num(p.get("marketCap"))
    beta = _num(p.get("beta"), 1.0)

    bs0 = bs[0] if bs else {}
    cash = _num(bs0.get("cashAndCashEquivalents")) + _num(bs0.get("shortTermInvestments"))
    debt = _num(bs0.get("totalDebt"))
    book_equity = _num(bs0.get("totalStockholdersEquity"))
    net_cash = cash - debt
    ev = mcap - net_cash

    cf_by_year = {}
    for row in cf:
        cf_by_year[str(row.get("fiscalYear") or row.get("date", "")[:4])] = row

    shares = 0
    historical = {}
    for row in sorted(inc, key=lambda x: str(x.get("fiscalYear") or x.get("date", ""))):
        fy = str(row.get("fiscalYear") or row.get("date", "")[:4])
        if not fy:
            continue
        rev = _num(row.get("revenue"))
        ebit = _num(row.get("operatingIncome"))
        ebitda = _num(row.get("ebitda")) or ebit
        da = _num(row.get("depreciationAndAmortization")) or max(ebitda - ebit, 0)
        ni = _num(row.get("netIncome"))
        tax = _num(row.get("incomeTaxExpense"))
        pretax = _num(row.get("incomeBeforeTax")) or (ni + tax)
        shares = _num(row.get("weightedAverageShsOut")) or shares
        c = cf_by_year.get(fy, {})
        capex = abs(_num(c.get("capitalExpenditure")))
        ocf = _num(c.get("operatingCashFlow"))
        fcf = _num(c.get("freeCashFlow")) or (ocf - capex)
        historical[f"FY{fy}"] = {
            "period_end": row.get("date", ""),
            "revenue": round(rev / 1_000_000),
            "ebitda": round(ebitda / 1_000_000),
            "ebit": round(ebit / 1_000_000),
            "da": round(da / 1_000_000),
            "capex": round(capex / 1_000_000),
            "ocf": round(ocf / 1_000_000),
            "fcf": round(fcf / 1_000_000),
            "tax": round(tax / 1_000_000),
            "pretax": round(pretax / 1_000_000),
            "net_income": round(ni / 1_000_000),
        }

    if not historical:
        raise ValueError(f"FMP: sin historico utilizable para {ticker}")
    if not shares and price:
        shares = mcap / price if price else 0

    fy_end_str = "December 31"
    try:
        last_date = inc[0].get("date", "")
        if last_date:
            fy_end_str = dt.datetime.strptime(last_date, "%Y-%m-%d").strftime("%B %d")
    except Exception:
        pass

    # Seed Base scenario from observed history (audit fix: defaults were generically
    # conservative -> quality companies always "overvalued").
    fy_sorted = sorted(historical.keys())
    margins = [
        h["ebitda"] / h["revenue"] * 100
        for h in (historical[k] for k in fy_sorted)
        if h.get("revenue")
    ]
    hist_margin = round(sorted(margins)[len(margins) // 2], 1) if margins else None
    hist_cagr = None
    if len(fy_sorted) >= 2:
        r0 = historical[fy_sorted[0]].get("revenue", 0)
        rn = historical[fy_sorted[-1]].get("revenue", 0)
        if r0 > 0 and rn > 0:
            hist_cagr = round(((rn / r0) ** (1 / (len(fy_sorted) - 1)) - 1) * 100, 1)

    sector = (p.get("sector") or "").strip()
    industry = (p.get("industry") or "").strip()

    return {
        "company": company,
        "ticker": ticker,
        "currency": currency,
        "as_of_date": as_of_date,
        "fiscal_year_end": fy_end_str,
        "sector": sector,
        "industry": industry,
        "data_sources": {
            "income_statement": f"Financial Modeling Prep stable ({ticker})",
            "cash_flow": f"Financial Modeling Prep stable ({ticker})",
            "balance_sheet": f"Financial Modeling Prep stable ({ticker})",
            "comps": "peers (in memory)",
            "risk_free_source": "Default. Override in app.",
            "erp_source": "Damodaran default. Override in app.",
        },
        "historical": historical,
        "market_data": {
            "shares_outstanding_m": round(shares / 1_000_000) if shares else 0,
            "current_price_eur": price,
            "market_cap_eur_m": round(mcap / 1_000_000) if mcap else 0,
            "cash_and_st_investments_eur_m": round(cash / 1_000_000) if cash else 0,
            "total_financial_debt_eur_m": round(debt / 1_000_000) if debt else 0,
            "net_cash_eur_m": round(net_cash / 1_000_000),
            "enterprise_value_eur_m": round(ev / 1_000_000) if ev else 0,
            "book_equity_eur_m": round(book_equity / 1_000_000) if book_equity else 0,
            "beta_5y": beta,
        },
        "wacc": _default_wacc(beta, currency, mcap, debt, cash),
        "projection_assumptions_base": _default_projection("base", hist_margin, hist_cagr),
        "projection_assumptions_bear": _default_projection("bear", hist_margin, hist_cagr),
        "projection_assumptions_bull": _default_projection("bull", hist_margin, hist_cagr),
        "sensitivity_ranges": {
            "wacc_pct": [6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5],
            "terminal_growth_pct": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
            "exit_multiple": [9.0, 10.5, 12.0, 13.5, 15.0],
        },
    }


def fetch_peer_fmp(ticker: str, as_of_date: str) -> dict:
    key = _fmp_key()
    if not key:
        raise RuntimeError("no FMP key")
    profile = _fmp_get("profile", ticker, key)
    if not profile:
        raise ValueError(f"FMP: sin profile peer {ticker}")
    p = profile[0]
    inc = _fmp_get("income-statement", ticker, key, limit=1)
    i0 = inc[0] if inc else {}
    bs = _fmp_get("balance-sheet-statement", ticker, key, limit=1)
    b0 = bs[0] if bs else {}
    rev = _num(i0.get("revenue"))
    ebitda = _num(i0.get("ebitda"))
    ni = _num(i0.get("netIncome"))
    mcap = _num(p.get("marketCap"))
    cash = _num(b0.get("cashAndCashEquivalents")) + _num(b0.get("shortTermInvestments"))
    debt = _num(b0.get("totalDebt"))
    ev = mcap - (cash - debt)
    price = _num(p.get("price"))
    return {
        "Company": p.get("companyName") or ticker,
        "Ticker": ticker,
        "Currency": p.get("currency") or "USD",
        "Revenue_TTM_LCY": rev,
        "Gross_Profit_TTM_LCY": _num(i0.get("grossProfit")),
        "EBITDA_TTM_LCY": ebitda,
        "Net_Income_TTM_LCY": ni,
        "Operating_Margin_pct": (_num(i0.get("operatingIncome")) / rev * 100) if rev else 0,
        "Net_Margin_pct": (ni / rev * 100) if rev else 0,
        "Market_Cap_LCY": mcap,
        "Enterprise_Value_LCY": ev,
        "EV_Sales": (ev / rev) if rev else 0,
        "EV_EBITDA": (ev / ebitda) if ebitda else 0,
        "PE_Trailing": (mcap / ni) if ni else 0,
        "PE_Forward": 0,
        "Beta_5Y": _num(p.get("beta"), 1.0),
        "Shares_Outstanding": _num(i0.get("weightedAverageShsOut")),
        "Stock_Price_LCY": price,
        "Total_Cash_LCY": cash,
        "Total_Debt_LCY": debt,
        "As_of_Date": as_of_date,
    }


class RateLimited(Exception):
    """Raised when the upstream data source rate-limits us."""


class TickerNotFound(Exception):
    """Raised when the ticker does not exist in the data source (not a rate-limit)."""


def _yf_info_with_retry(ticker: str, retries: int = 3, base_delay: float = 1.5):
    """Fetch yfinance .info with exponential backoff on rate limits."""
    last_err = None
    for attempt in range(retries):
        try:
            yt = yf.Ticker(ticker)
            info = yt.info or {}
            # yfinance returns a near-empty dict on soft rate-limit
            if info and (info.get("currentPrice") or info.get("regularMarketPrice") or info.get("marketCap")):
                return yt, info
            last_err = "empty info (possible soft rate-limit)"
        except Exception as e:
            last_err = str(e)
            if "too many requests" in last_err.lower() or "429" in last_err or "rate" in last_err.lower():
                pass  # fall through to backoff
        time.sleep(base_delay * (2 ** attempt))
    raise RateLimited(f"yfinance failed for {ticker} after {retries} tries: {last_err}")


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

    # PRIMARY: Financial Modeling Prep (dedicated key, no shared-IP rate-limit).
    # FALLBACK: yfinance (only if FMP key absent or FMP fails for this ticker).
    if _fmp_key():
        try:
            inputs = fetch_company_fmp(ticker, as_of_date)
            if peer_tickers:
                inputs["peers_data"] = fetch_peers(peer_tickers, as_of_date)
            return inputs
        except RateLimited:
            raise
        except TickerNotFound:
            raise  # do NOT fall back to yfinance for a non-existent ticker
        except Exception:
            pass  # FMP failed for this ticker -> fall back to yfinance below

    yt, info = _yf_info_with_retry(ticker)
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
    """Fetch comps data for a single peer. FMP primary, yfinance fallback, empty row on hard fail."""
    if _fmp_key():
        try:
            return fetch_peer_fmp(ticker, as_of_date)
        except Exception:
            pass  # fall back to yfinance
    try:
        yt, info = _yf_info_with_retry(ticker, retries=2)
    except RateLimited:
        return {
            "Company": ticker, "Ticker": ticker, "Currency": "USD",
            "Revenue_TTM_LCY": 0, "Gross_Profit_TTM_LCY": 0, "EBITDA_TTM_LCY": 0,
            "Net_Income_TTM_LCY": 0, "Operating_Margin_pct": 0, "Net_Margin_pct": 0,
            "Market_Cap_LCY": 0, "Enterprise_Value_LCY": 0, "EV_Sales": 0, "EV_EBITDA": 0,
            "PE_Trailing": 0, "PE_Forward": 0, "Beta_5Y": 1.0, "Shares_Outstanding": 0,
            "Stock_Price_LCY": 0, "Total_Cash_LCY": 0, "Total_Debt_LCY": 0,
            "As_of_Date": as_of_date, "_error": "rate_limited",
        }
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


def _default_wacc(beta: float, currency: str, mcap: float = 0, debt: float = 0, cash: float = 0) -> dict:
    """WACC with real D/V weighting from balance (audit fix: was Ke only).

    Net-cash firms -> ~100% equity (correct). Net-debt firms -> weighted with
    after-tax cost of debt. User can still override in UI.
    """
    if currency == "EUR":
        rf, rf_src = 3.2, "Spain/Germany 10Y bond (avg)"
    elif currency == "GBP":
        rf, rf_src = 4.2, "UK 10Y Gilt"
    elif currency == "JPY":
        rf, rf_src = 1.5, "Japan 10Y JGB"
    else:
        rf, rf_src = 4.0, "US 10Y Treasury"

    erp = 5.5
    cost_of_equity = rf + beta * erp
    tax = 22.0
    pretax_debt = rf + 1.5  # rough investment-grade spread over risk-free
    after_tax_debt = pretax_debt * (1 - tax / 100)

    net_debt = max(debt - cash, 0)  # only weight debt if firm is net-debt
    v = (mcap or 0) + net_debt
    if v > 0 and net_debt > 0:
        e_w = mcap / v
        d_w = net_debt / v
    else:
        e_w, d_w = 1.0, 0.0
    wacc = e_w * cost_of_equity + d_w * after_tax_debt

    return {
        "risk_free_rate_pct": rf,
        "risk_free_source": rf_src,
        "equity_risk_premium_pct": erp,
        "erp_source": "Damodaran current ERP",
        "beta": beta,
        "cost_of_equity_pct": round(cost_of_equity, 2),
        "pretax_cost_of_debt_pct": round(pretax_debt, 2),
        "tax_rate_pct": tax,
        "after_tax_cost_of_debt_pct": round(after_tax_debt, 2),
        "equity_weight_pct": round(e_w * 100, 1),
        "debt_weight_pct": round(d_w * 100, 1),
        "wacc_pct": round(wacc, 2),
        "note": "WACC ponderado E/V + D/V (after-tax kd). Ajustable en UI.",
    }


def _default_projection(scenario: str, hist_margin: float = None, hist_cagr: float = None) -> dict:
    # Seed Base from observed history when available (audit fix).
    base_margin = hist_margin if hist_margin is not None else 25.0
    base_g1 = max(min(hist_cagr, 15.0), 2.0) if hist_cagr is not None else 7.0

    if scenario == "base":
        # decay observed growth toward a mature long-run rate
        g_end = max(min(base_g1 * 0.35, 4.0), 2.0)
        growth = [round(base_g1 + (g_end - base_g1) * i / 9, 1) for i in range(10)]
        margin = [round(base_margin, 1)] * 10
        capex = [6.0, 6.0, 5.5, 5.5, 5.0, 5.0, 4.5, 4.5, 4.0, 4.0]
        tg = 2.5
        em = 12.0
    elif scenario == "bear":
        # Bear realista, no apocaliptico: desaceleracion + leve compresion margen,
        # no combinatoria de todos los peores inputs a la vez (auditoria 2).
        g1 = max(base_g1 * 0.6, 1.5)
        growth = [round(max(g1 - 0.1 * i, 1.5), 1) for i in range(10)]
        margin = [round(max(base_margin - 3, 10), 1)] * 10
        capex = [6.0, 6.0, 5.5, 5.5, 5.0, 5.0, 4.5, 4.5, 4.0, 4.0]
        tg = 1.8
        em = 10.0
    else:  # bull
        g1 = min(base_g1 * 1.3, 18.0)
        g_end = max(min(g1 * 0.4, 5.0), 3.0)
        growth = [round(g1 + (g_end - g1) * i / 9, 1) for i in range(10)]
        margin = [round(base_margin + 3, 1)] * 10
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
