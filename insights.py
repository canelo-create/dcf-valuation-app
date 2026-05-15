"""Motor de insights por empresa.

Genera comentario tipo analista profesional basado en los numeros reales
calculados. Metodologia alineada con IE Corporate Finance + Financial Markets
+ Financial Accounting (vault MBA del usuario).

Cada insight: {categoria, sentimiento, titulo, detalle}
sentimiento in {"positivo", "neutro", "alerta"}
"""

from statistics import median
from typing import Optional


def _cagr(first, last, years):
    if first <= 0 or last <= 0 or years <= 0:
        return None
    return ((last / first) ** (1 / years) - 1) * 100


def generate_insights(inputs: dict, scenarios: dict, peers_data: Optional[list] = None) -> list:
    out = []
    md = inputs["market_data"]
    ccy = inputs["currency"]
    hist = inputs.get("historical", {})
    fy_keys = sorted(hist.keys())
    base = scenarios["base"]
    meta = scenarios.get("_meta", {})
    wacc = inputs["wacc"]["wacc_pct"]
    current = md.get("current_price_eur", 0)
    base_price = base["dcf"]["implied_share_price"]
    upside = (base_price / current - 1) * 100 if current else 0
    tv_pct = base["dcf"]["tv_pct_of_ev"]

    latest = hist[fy_keys[-1]] if fy_keys else {}
    rev = latest.get("revenue", 0)
    ebitda = latest.get("ebitda", 0)
    ni = latest.get("net_income", 0)
    fcf = latest.get("fcf", 0)
    ebitda_margin = (ebitda / rev * 100) if rev else 0

    # --- 1. Valoracion vs mercado ---
    if upside > 25:
        out.append({"categoria": "Valoracion", "sentimiento": "positivo",
                    "titulo": f"Potencial alto ({upside:+.0f}%)",
                    "detalle": f"El modelo estima {ccy} {base_price:,.2f} vs {ccy} {current:,.2f} de mercado. Margen de seguridad amplio en el caso base, pero verifica que los supuestos de crecimiento sean creibles antes de actuar."})
    elif upside > 10:
        out.append({"categoria": "Valoracion", "sentimiento": "positivo",
                    "titulo": f"Ligero descuento ({upside:+.0f}%)",
                    "detalle": "Recorrido moderado. No es una ganga obvia; el margen de seguridad es estrecho ante errores de estimacion."})
    elif upside > -10:
        out.append({"categoria": "Valoracion", "sentimiento": "neutro",
                    "titulo": "Precio en linea con valor",
                    "detalle": "Mercado y modelo coinciden. Sin ineficiencia evidente: la tesis tendria que venir de un cambio que el modelo no captura todavia."})
    else:
        out.append({"categoria": "Valoracion", "sentimiento": "alerta",
                    "titulo": f"Cotiza con prima ({upside:+.0f}%)",
                    "detalle": "El precio actual supera lo que justifican los flujos del caso base. O el mercado espera mas crecimiento del modelado, o hay sobrevaloracion."})

    # --- 2. Crecimiento implicito (reverse-DCF) ---
    g_impl = meta.get("implied_growth_pct")
    if g_impl is not None:
        if g_impl > 6:
            out.append({"categoria": "Expectativas del mercado", "sentimiento": "alerta",
                        "titulo": f"Mercado descuenta {g_impl:.1f}% perpetuo",
                        "detalle": f"Para justificar el precio, la empresa deberia crecer {g_impl:.1f}% PARA SIEMPRE. Pocas empresas sostienen eso decadas. Riesgo de decepcion si no cumple."})
        elif g_impl < 0:
            out.append({"categoria": "Expectativas del mercado", "sentimiento": "positivo",
                        "titulo": "Mercado no espera crecimiento",
                        "detalle": f"El precio implica crecimiento perpetuo de {g_impl:.1f}%. Expectativas en suelo: cualquier sorpresa positiva tiene recorrido."})
        else:
            out.append({"categoria": "Expectativas del mercado", "sentimiento": "neutro",
                        "titulo": f"Mercado descuenta {g_impl:.1f}% perpetuo",
                        "detalle": "Crecimiento implicito razonable y alineado con una economia madura. Expectativas equilibradas."})

    # --- 3. Calidad del negocio: ROIC vs WACC ---
    roic = meta.get("roic_pct")
    if roic is not None:
        if roic > 2 * wacc:
            out.append({"categoria": "Calidad del negocio", "sentimiento": "positivo",
                        "titulo": f"Foso economico fuerte (ROIC {roic:.0f}%)",
                        "detalle": f"ROIC {roic:.0f}% mas que duplica el WACC {wacc:.1f}%. Genera retornos muy por encima del coste de capital: ventaja competitiva duradera (marca, escala, red, costes)."})
        elif roic > wacc:
            out.append({"categoria": "Calidad del negocio", "sentimiento": "positivo",
                        "titulo": f"Crea valor (ROIC {roic:.0f}% > WACC {wacc:.1f}%)",
                        "detalle": "Cada euro reinvertido genera mas que su coste. Negocio sano que crea valor al crecer."})
        elif roic > wacc - 2:
            out.append({"categoria": "Calidad del negocio", "sentimiento": "neutro",
                        "titulo": f"Sin ventaja clara (ROIC {roic:.0f}% ~ WACC {wacc:.1f}%)",
                        "detalle": "Retornos cercanos al coste de capital. Crecer no crea ni destruye valor de forma material: negocio commodity o competitivo."})
        else:
            out.append({"categoria": "Calidad del negocio", "sentimiento": "alerta",
                        "titulo": f"Destruye valor (ROIC {roic:.0f}% < WACC {wacc:.1f}%)",
                        "detalle": "Gana menos que el coste de su capital. Crecer destruye valor salvo que mejore retornos. Bandera roja para tesis de crecimiento."})

    # --- 4. Margenes (benchmark sectorial implicito) ---
    if ebitda_margin:
        if ebitda_margin > 35:
            out.append({"categoria": "Rentabilidad", "sentimiento": "positivo",
                        "titulo": f"Margen EBITDA excepcional ({ebitda_margin:.0f}%)",
                        "detalle": "Margen tipico de software, lujo o marcas con poder de fijacion de precios. Sugiere fuerte diferenciacion y barreras de entrada."})
        elif ebitda_margin > 20:
            out.append({"categoria": "Rentabilidad", "sentimiento": "positivo",
                        "titulo": f"Margen EBITDA fuerte ({ebitda_margin:.0f}%)",
                        "detalle": "Por encima de la media de la mayoria de sectores. Eficiencia operativa solida."})
        elif ebitda_margin > 10:
            out.append({"categoria": "Rentabilidad", "sentimiento": "neutro",
                        "titulo": f"Margen EBITDA normal ({ebitda_margin:.0f}%)",
                        "detalle": "Rango habitual de retail, industrial o consumo. Vigila la tendencia: estable o comprimiendose."})
        else:
            out.append({"categoria": "Rentabilidad", "sentimiento": "alerta",
                        "titulo": f"Margen EBITDA bajo ({ebitda_margin:.0f}%)",
                        "detalle": "Tipico de commodity, distribucion o sector en presion competitiva. Poca holgura ante shocks de coste."})

    # --- 5. Trayectoria de ingresos (historico vs proyectado) ---
    if len(fy_keys) >= 2:
        first_rev = hist[fy_keys[0]].get("revenue", 0)
        hist_cagr = _cagr(first_rev, rev, len(fy_keys) - 1)
        proj = base["projection"]
        proj_y1_g = (proj["revenue"][0] / rev - 1) * 100 if rev else 0
        if hist_cagr is not None:
            if hist_cagr > 15:
                out.append({"categoria": "Crecimiento", "sentimiento": "positivo",
                            "titulo": f"Historico de alto crecimiento ({hist_cagr:.0f}% CAGR)",
                            "detalle": f"Ingresos crecieron {hist_cagr:.0f}% anual ultimos {len(fy_keys)-1} anos. El modelo proyecta moderacion (normal al ganar tamano). Clave: si la moderacion asumida es realista."})
            elif hist_cagr < 2:
                out.append({"categoria": "Crecimiento", "sentimiento": "alerta",
                            "titulo": f"Crecimiento historico plano ({hist_cagr:.0f}% CAGR)",
                            "detalle": "Ingresos casi estancados. Si el modelo proyecta aceleracion, exige justificacion (nuevo producto, mercado, ciclo). Si no, la valoracion descansa en margenes o caja."})
            else:
                out.append({"categoria": "Crecimiento", "sentimiento": "neutro",
                            "titulo": f"Crecimiento historico moderado ({hist_cagr:.0f}% CAGR)",
                            "detalle": f"Trayectoria estable. El modelo asume {proj_y1_g:+.0f}% el primer ano: comparalo con el historico para sanity check."})

    # --- 6. Calidad del beneficio (FCF conversion) ---
    if ni and fcf:
        conv = fcf / ni * 100
        if conv > 95:
            out.append({"categoria": "Calidad del beneficio", "sentimiento": "positivo",
                        "titulo": f"Conversion FCF excelente ({conv:.0f}% del beneficio)",
                        "detalle": "El beneficio contable se convierte casi integro en caja real. Senal de calidad: poco working capital, capex contenido, beneficio fiable."})
        elif conv > 65:
            out.append({"categoria": "Calidad del beneficio", "sentimiento": "neutro",
                        "titulo": f"Conversion FCF sana ({conv:.0f}%)",
                        "detalle": "La mayor parte del beneficio se vuelve caja. Rango normal para negocio con algo de capex."})
        elif conv > 0:
            out.append({"categoria": "Calidad del beneficio", "sentimiento": "alerta",
                        "titulo": f"Conversion FCF baja ({conv:.0f}%)",
                        "detalle": "Poco del beneficio se convierte en caja. Posible capex pesado, drenaje de working capital o calidad de beneficio debil. Revisa de donde viene la diferencia."})
        else:
            out.append({"categoria": "Calidad del beneficio", "sentimiento": "alerta",
                        "titulo": "FCF negativo o beneficio negativo",
                        "detalle": "La empresa no genera caja libre positiva con beneficio positivo (o viceversa). DCF menos fiable: trata el resultado con cautela."})

    # --- 7. Estructura financiera ---
    net_cash = md.get("net_cash_eur_m", 0)
    if net_cash > 0:
        pct_eq = (net_cash / base["dcf"]["equity_value"] * 100) if base["dcf"].get("equity_value") else 0
        out.append({"categoria": "Balance", "sentimiento": "positivo",
                    "titulo": f"Caja neta {ccy} {net_cash:,.0f}M",
                    "detalle": f"Balance fortaleza (~{pct_eq:.0f}% del equity value). Opcionalidad no reflejada del todo en el DCF: recompras, dividendo extra, M&A o resistencia en crisis."})
    else:
        nd = -net_cash
        lev = (nd / ebitda) if ebitda else None
        if lev is not None and lev > 3:
            out.append({"categoria": "Balance", "sentimiento": "alerta",
                        "titulo": f"Apalancamiento alto ({lev:.1f}x EBITDA)",
                        "detalle": f"Deuda neta {ccy} {nd:,.0f}M = {lev:.1f}x EBITDA. Riesgo de refinanciacion si suben tipos o cae el EBITDA. El equity es mas volatil."})
        elif lev is not None:
            out.append({"categoria": "Balance", "sentimiento": "neutro",
                        "titulo": f"Apalancamiento moderado ({lev:.1f}x EBITDA)",
                        "detalle": "Deuda manejable. Estructura de capital habitual; vigila cobertura de intereses si el ciclo se deteriora."})

    # --- 8. Riesgo: beta ---
    beta = md.get("beta_5y", 1.0)
    if beta and beta < 0.8:
        out.append({"categoria": "Riesgo", "sentimiento": "positivo",
                    "titulo": f"Perfil defensivo (beta {beta:.2f})",
                    "detalle": "Menos sensible al ciclo que el mercado. Tipico de consumo estable o utilities. Cae menos en crisis, pero tambien sube menos en rallies."})
    elif beta and beta > 1.5:
        out.append({"categoria": "Riesgo", "sentimiento": "alerta",
                    "titulo": f"Perfil ciclico/agresivo (beta {beta:.2f})",
                    "detalle": "Amplifica el ciclo: sube mas en rallies, cae mas en crisis. El WACC sube con el beta, presionando la valoracion. Apto solo si toleras volatilidad."})
    elif beta:
        out.append({"categoria": "Riesgo", "sentimiento": "neutro",
                    "titulo": f"Riesgo de mercado (beta {beta:.2f})",
                    "detalle": "Se mueve aproximadamente como el mercado. Sin sesgo defensivo ni agresivo marcado."})

    # --- 9. Fragilidad de la valoracion (terminal dependency) ---
    if tv_pct > 75:
        out.append({"categoria": "Fiabilidad del modelo", "sentimiento": "alerta",
                    "titulo": f"Valoracion especulativa (terminal {tv_pct:.0f}% del EV)",
                    "detalle": "Mas de 3/4 del valor depende de lo que pase tras el ano 10. Pequenos cambios en g o WACC mueven mucho el precio. Trata el numero como orientativo, no preciso."})
    elif tv_pct > 70:
        out.append({"categoria": "Fiabilidad del modelo", "sentimiento": "neutro",
                    "titulo": f"Terminal algo elevado ({tv_pct:.0f}% del EV)",
                    "detalle": "Por encima del rango ideal 50-70%. La estimacion es sensible a los supuestos terminales; mira la tabla de sensibilidad."})
    else:
        out.append({"categoria": "Fiabilidad del modelo", "sentimiento": "positivo",
                    "titulo": f"Estructura de valor robusta (terminal {tv_pct:.0f}% del EV)",
                    "detalle": "El valor terminal esta en rango sano: una parte relevante viene de flujos explicitos, no solo del supuesto perpetuo."})

    if base["dcf"].get("terminal_g_capped"):
        out.append({"categoria": "Fiabilidad del modelo", "sentimiento": "alerta",
                    "titulo": "Crecimiento terminal ajustado automaticamente",
                    "detalle": "El crecimiento terminal introducido era >= WACC (matematicamente invalido, valor infinito). Se capo justo por debajo del WACC. Baja el crecimiento terminal a un nivel realista (2-3%)."})

    # --- 10. Comparables (si hay) ---
    if peers_data:
        ev_ebitda_vals = []
        for p in peers_data:
            v = p.get("EV_EBITDA")
            try:
                v = float(v)
                if v > 0:
                    ev_ebitda_vals.append(v)
            except (TypeError, ValueError):
                pass
        if ev_ebitda_vals and ebitda and md.get("enterprise_value_eur_m"):
            peer_med = median(ev_ebitda_vals)
            own = md["enterprise_value_eur_m"] / ebitda if ebitda else None
            if own and peer_med:
                prem = (own / peer_med - 1) * 100
                if prem > 20:
                    sent, txt = ("neutro", f"Cotiza {prem:+.0f}% sobre la mediana de pares ({own:.1f}x vs {peer_med:.1f}x EV/EBITDA). Justificado solo si margenes/ROIC/crecimiento superiores. Si no, esta cara vs sus pares.")
                elif prem < -20:
                    sent, txt = ("positivo", f"Cotiza {prem:+.0f}% bajo la mediana de pares ({own:.1f}x vs {peer_med:.1f}x EV/EBITDA). Posible ganga o problema estructural que el mercado castiga: investiga cual.")
                else:
                    sent, txt = ("neutro", f"En linea con pares ({own:.1f}x vs {peer_med:.1f}x EV/EBITDA mediana). Valoracion relativa equilibrada.")
                out.append({"categoria": "Comparables", "sentimiento": sent, "titulo": "Posicion vs pares", "detalle": txt})

    # --- 11. Dispersion de escenarios (incertidumbre) ---
    bear_up = (scenarios["bear"]["dcf"]["implied_share_price"] / current - 1) * 100 if current else 0
    bull_up = (scenarios["bull"]["dcf"]["implied_share_price"] / current - 1) * 100 if current else 0
    spread = bull_up - bear_up
    if spread > 130:
        out.append({"categoria": "Incertidumbre", "sentimiento": "alerta",
                    "titulo": f"Rango de resultados muy amplio ({spread:.0f}pp)",
                    "detalle": f"Entre pesimista ({bear_up:+.0f}%) y optimista ({bull_up:+.0f}%) hay {spread:.0f} puntos. Mucha incertidumbre: el valor depende fuerte de supuestos. Exige convicción en la tesis."})
    else:
        out.append({"categoria": "Incertidumbre", "sentimiento": "neutro",
                    "titulo": f"Rango de resultados acotado ({spread:.0f}pp)",
                    "detalle": f"Pesimista {bear_up:+.0f}% / optimista {bull_up:+.0f}%. Dispersion razonable: la valoracion es relativamente estable ante cambios de escenario."})

    return out


def insights_summary_line(insights: list) -> str:
    pos = sum(1 for i in insights if i["sentimiento"] == "positivo")
    neu = sum(1 for i in insights if i["sentimiento"] == "neutro")
    ale = sum(1 for i in insights if i["sentimiento"] == "alerta")
    return f"{pos} senales positivas | {neu} neutras | {ale} alertas"
