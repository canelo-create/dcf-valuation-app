"""Monitor de noticias global via GDELT (gratis, sin API key).

GDELT indexa miles de medios mundiales en tiempo casi real. Cubre mercados,
macro y geopolitica. NO es un Bloomberg Terminal (sin datos propietarios ni
precios en vivo): es un agregador honesto de noticias global y gratuito.
"""

import datetime as dt
import time

import requests

GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"


class NewsError(Exception):
    pass


def _parse_seendate(s: str) -> str:
    # GDELT formato: 20260516T030200Z
    try:
        d = dt.datetime.strptime(s, "%Y%m%dT%H%M%SZ")
        return d.strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, TypeError):
        return s or ""


def gdelt_query(query: str, max_records: int = 20, timespan: str = "3d",
                english_only: bool = True) -> list:
    """Devuelve lista de {title, url, domain, date} ordenada por fecha desc."""
    q = query
    if english_only:
        q = f"({query}) sourcelang:eng"
    params = {
        "query": q,
        "mode": "artlist",
        "maxrecords": max_records,
        "timespan": timespan,
        "format": "json",
        "sort": "datedesc",
    }
    delay = 1.5
    r = None
    for attempt in range(3):
        try:
            r = requests.get(GDELT, params=params, timeout=20,
                             headers={"User-Agent": "Mozilla/5.0 (news-monitor)"})
        except requests.RequestException as e:
            raise NewsError(f"Conexion GDELT fallo: {e}")
        if r.status_code == 429:
            if attempt < 2:
                time.sleep(delay)
                delay *= 2
                continue
            raise NewsError("GDELT esta limitando peticiones. Reintenta en un minuto.")
        break
    if r is None or r.status_code != 200:
        raise NewsError(f"GDELT HTTP {r.status_code if r else 'sin respuesta'}")
    try:
        data = r.json()
    except ValueError:
        return []  # GDELT a veces devuelve texto vacio si no hay resultados
    arts = data.get("articles", []) if isinstance(data, dict) else []
    out, seen = [], set()
    for a in arts:
        title = (a.get("title") or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        out.append({
            "title": title,
            "url": a.get("url", ""),
            "domain": a.get("domain", ""),
            "date": _parse_seendate(a.get("seendate", "")),
        })
    return out


# Consultas curadas por categoria (un inversor profesional)
CATEGORIES = {
    "Mercados": '"stock market" OR equities OR "S&P 500" OR Nasdaq OR "bond yields" OR "earnings"',
    "Macro y Economia": '"central bank" OR "interest rates" OR inflation OR recession OR GDP OR "Federal Reserve" OR ECB',
    "Geopolitica": 'geopolitics OR sanctions OR "trade war" OR election OR conflict OR OPEC OR tariffs',
    "Materias primas y FX": '"crude oil" OR gold OR "currency" OR "dollar index" OR commodities OR copper',
}
