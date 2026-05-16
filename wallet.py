"""Conexion de cartera: Alpaca (acciones) + Polymarket (read-only).

SEGURIDAD:
- Claves API NUNCA se hardcodean ni se commitean. Vienen de st.secrets o input
  de sesion del usuario (no persistido). .gitignore cubre .streamlit/secrets.toml.
- Alpaca: por defecto PAPER trading (dinero ficticio). Live exige toggle explicito.
- Polymarket: SOLO lectura por direccion publica de wallet. NUNCA se maneja la
  private key del usuario en esta app (riesgo critico). Ordenes Polymarket no
  se ejecutan desde aqui a proposito.
"""

import requests

ALPACA_PAPER = "https://paper-api.alpaca.markets/v2"
ALPACA_LIVE = "https://api.alpaca.markets/v2"
POLYMARKET_DATA = "https://data-api.polymarket.com"


class WalletError(Exception):
    pass


def _alpaca_headers(key: str, secret: str):
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}


def _alpaca_base(paper: bool):
    return ALPACA_PAPER if paper else ALPACA_LIVE


def alpaca_account(key: str, secret: str, paper: bool = True) -> dict:
    try:
        r = requests.get(f"{_alpaca_base(paper)}/account", headers=_alpaca_headers(key, secret), timeout=15)
    except requests.RequestException as e:
        raise WalletError(f"Conexion Alpaca fallo: {e}")
    if r.status_code in (401, 403):
        raise WalletError("Claves Alpaca invalidas o sin permiso (revisa key/secret y si son de paper o live).")
    if r.status_code != 200:
        raise WalletError(f"Alpaca devolvio HTTP {r.status_code}.")
    return r.json()


def alpaca_positions(key: str, secret: str, paper: bool = True) -> list:
    r = requests.get(f"{_alpaca_base(paper)}/positions", headers=_alpaca_headers(key, secret), timeout=15)
    if r.status_code != 200:
        raise WalletError(f"No pude leer posiciones (HTTP {r.status_code}).")
    return r.json()


def make_order_tag(verdict: str, upside_pct: float) -> str:
    """Codifica el veredicto del modelo en el client_order_id de Alpaca.

    Persiste en la cuenta del usuario (sin DB propia). Permite luego medir si
    seguir el modelo en paper money funciona. Formato: dcf|<VERDICT>|<+up>
    """
    v = "".join(c for c in (verdict or "NA").upper() if c.isalpha())[:12] or "NA"
    return f"dcf|{v}|{upside_pct:+.0f}|{int(__import__('time').time())}"


def parse_order_tag(client_order_id: str):
    """Devuelve (verdict, upside_pct) o (None, None) si no es una orden etiquetada."""
    if not client_order_id or not client_order_id.startswith("dcf|"):
        return None, None
    parts = client_order_id.split("|")
    if len(parts) < 3:
        return None, None
    try:
        return parts[1], float(parts[2])
    except (ValueError, IndexError):
        return parts[1], None


def alpaca_place_order(key: str, secret: str, symbol: str, qty: float, side: str,
                       paper: bool = True, order_type: str = "market",
                       time_in_force: str = "day", client_order_id: str = None) -> dict:
    """Coloca una orden. Solo se debe llamar tras confirmacion explicita en la UI.
    side: 'buy' | 'sell'. paper=True por defecto (dinero ficticio).
    client_order_id: tag opcional (veredicto del modelo) para medir resultados luego.
    """
    if side not in ("buy", "sell"):
        raise WalletError("side debe ser 'buy' o 'sell'.")
    if qty <= 0:
        raise WalletError("Cantidad debe ser > 0.")
    payload = {
        "symbol": symbol.upper(),
        "qty": str(qty),
        "side": side,
        "type": order_type,
        "time_in_force": time_in_force,
    }
    if client_order_id:
        payload["client_order_id"] = client_order_id[:48]
    r = requests.post(f"{_alpaca_base(paper)}/orders", headers=_alpaca_headers(key, secret),
                      json=payload, timeout=20)
    if r.status_code not in (200, 201):
        msg = r.text[:200]
        raise WalletError(f"Orden rechazada (HTTP {r.status_code}): {msg}")
    return r.json()


def alpaca_recent_orders(key: str, secret: str, paper: bool = True, limit: int = 20) -> list:
    r = requests.get(f"{_alpaca_base(paper)}/orders",
                      headers=_alpaca_headers(key, secret),
                      params={"status": "all", "limit": limit, "direction": "desc"},
                      timeout=15)
    if r.status_code != 200:
        return []
    return r.json()


def polymarket_positions(address: str) -> list:
    """Read-only: posiciones de una wallet publica de Polymarket. Sin private key."""
    addr = address.strip()
    if not (addr.startswith("0x") and len(addr) == 42):
        raise WalletError("Direccion EVM invalida (formato esperado 0x... de 42 caracteres).")
    try:
        r = requests.get(f"{POLYMARKET_DATA}/positions", params={"user": addr}, timeout=15)
    except requests.RequestException as e:
        raise WalletError(f"Conexion Polymarket fallo: {e}")
    if r.status_code != 200:
        raise WalletError(f"Polymarket devolvio HTTP {r.status_code}.")
    data = r.json()
    return data if isinstance(data, list) else []
