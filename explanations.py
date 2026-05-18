"""Explicaciones en lenguaje sencillo + generador de veredicto.

Para que cualquier persona (experto o amateur) entienda el análisis.
"""

GLOSSARY = {
    "DCF": "Descuento de Flujos de Caja. Calcula cuánto vale una empresa sumando todo el dinero que generará en el futuro, traído a valor de hoy (un euro mañana vale menos que un euro hoy).",
    "WACC": "Coste medio del capital. La rentabilidad mínima que exige un inversor por asumir el riesgo de esta empresa. Cuanto más arriesgada, más alto. Es como el tipo de interés de un préstamo ajustado al riesgo.",
    "EBITDA": "Beneficio del negocio puro: lo que gana antes de pagar intereses, impuestos y el desgaste de sus activos (máquinas, tiendas). Mide la salud operativa real.",
    "FCF": "Flujo de Caja Libre. El dinero de verdad que sobra después de pagar gastos e inversiones. Es lo que la empresa puede repartir a accionistas o reinvertir.",
    "FCF Unlevered": "Flujo de caja libre antes de pagar deuda. Sirve para valorar el negocio completo, sin importar cómo está financiado.",
    "Valor Terminal": "El valor de la empresa MÁS ALLÁ del año 10, asumiendo que sigue funcionando para siempre con crecimiento estable. Suele ser la mayor parte del valor total.",
    "EV": "Valor Empresa (Enterprise Value). Lo que costaría comprar TODA la empresa: capitalización en bolsa más deuda, menos caja.",
    "Equity Value": "Valor de las acciones. El EV menos la deuda neta. Dividido entre número de acciones da el precio por acción.",
    "Beta": "Mide cuánto se mueve la acción respecto al mercado. Beta 1 = se mueve igual que el mercado. Beta 2 = el doble de volátil. Beta 0.5 = más defensiva.",
    "Múltiplo EV/EBITDA": "Cuántas veces su beneficio operativo paga el mercado por la empresa. Como el ratio precio/alquiler de un piso. Bajo = barata, alto = cara (o con mucho crecimiento esperado).",
    "P/E": "Precio / Beneficio. Cuántos años de beneficios actuales tardarías en recuperar lo que pagas por la acción. P/E 20 = pagas 20 años de beneficios.",
    "Crecimiento Terminal": "A qué ritmo asumimos que crece la empresa para siempre después del año 10. Suele ser similar al crecimiento de la economía (2-3%).",
    "Múltiplo de Salida": "A qué múltiplo EV/EBITDA asumimos que se podría vender la empresa al final de la proyección. Lo informan las empresas comparables.",
    "Comparables (Comps)": "Empresas parecidas que cotizan en bolsa. Comparar sus múltiplos dice si tu empresa está cara o barata respecto a sus pares.",
    "ROIC": "Retorno sobre el capital invertido. Cuánto gana la empresa por cada euro invertido. Si ROIC > WACC, la empresa CREA valor. Si ROIC < WACC, lo destruye (gana menos que el coste de su capital).",
    "Crecimiento implícito": "Reverse-DCF: qué ritmo de crecimiento perpetuo tendría que cumplir la empresa para justificar el precio que el mercado paga HOY. Si es muy alto y poco creíble, la acción está cara.",
    "Caso Base": "El escenario más probable, con supuestos realistas.",
    "Caso Pesimista": "Qué pasaría si las cosas van mal: menos crecimiento, márgenes más bajos.",
    "Caso Optimista": "Qué pasaría si las cosas van muy bien: crecimiento sostenido, márgenes altos.",
    "Potencial / Upside": "Diferencia entre el precio que estima el modelo y el precio actual en bolsa. Positivo = el modelo cree que está barata.",
}

HOW_IT_WORKS = """
**Cómo funciona en 4 pasos:**

1. **Buscamos datos reales.** Descargamos las cuentas de la empresa (ingresos, beneficios, caja) de los últimos 5 años vía Financial Modeling Prep.

2. **Proyectamos el futuro.** Estimamos cuánto dinero generará los próximos 10 años, con 3 escenarios: pesimista, base y optimista.

3. **Traemos ese dinero a hoy.** Un euro dentro de 10 años vale menos que hoy. Lo ajustamos con el WACC (coste del riesgo).

4. **Comparamos con el mercado.** Sumamos todo, lo dividimos entre el número de acciones, y comparamos con el precio actual en bolsa. Si el modelo estima más que el precio actual, la acción podría estar barata.
"""

DISCLAIMER_SIMPLE = """
**Importante:** Herramienta educativa, NO recomendación de inversión. Un modelo
vale solo lo que sus supuestos. El DCF NO aplica a bancos, aseguradoras, REITs ni
empresas en pérdidas. El mercado puede tener razón y el modelo equivocarse.
Verifica el reporte anual oficial y diversifica. Rendimientos pasados no garantizan futuros.
"""

DISCLAIMER_BANNER = (
    "Herramienta educativa, no es asesoramiento financiero. El DCF no aplica a "
    "bancos, aseguradoras, REITs ni empresas con pérdidas."
)


def verdict(upside_pct: float, tv_pct: float, currency: str, base_price: float, current_price: float, meta: dict = None):
    """Devuelve (badge, color_hex, parrafo_explicativo). meta opcional con implied_growth/ROIC."""
    # Audit fix: bancos/aseguradoras/REITs/empresas en perdidas -> DCF no aplica.
    if meta and meta.get("dcf_applicable") is False:
        reason = meta.get("not_applicable_reason") or "El DCF no aplica a esta empresa."
        parrafo = (
            f"**No se puede valorar esta empresa con este modelo.**\n\n{reason}\n\n"
            f"El número que saldría de un DCF aquí sería engañoso. No lo uses como señal de compra o venta."
        )
        return "NO VALORABLE CON DCF", "#9AA0A6", parrafo

    if upside_pct > 25:
        badge = "POSIBLEMENTE INFRAVALORADA"
        color = "#1DB954"
        gut = "el modelo cree que vale bastante más de lo que cuesta hoy"
    elif 10 <= upside_pct <= 25:
        badge = "LIGERAMENTE BARATA"
        color = "#5FD68A"
        gut = "el modelo ve algo de recorrido al alza, pero moderado"
    elif -10 < upside_pct < 10:
        badge = "PRECIO JUSTO"
        color = "#E8C547"
        gut = "el mercado y el modelo están prácticamente de acuerdo"
    elif -25 <= upside_pct <= -10:
        badge = "LIGERAMENTE CARA"
        color = "#E8954B"
        gut = "el modelo sugiere que el precio actual es algo exigente"
    else:
        badge = "POSIBLEMENTE SOBREVALORADA"
        color = "#E84B4B"
        gut = "el modelo cree que cuesta bastante más de lo que vale según sus flujos"

    if -10 < upside_pct < 10:
        simple = "el mercado y el modelo coinciden: no hay una diferencia material para actuar"
    elif upside_pct >= 10:
        simple = "según los flujos esperados, la acción debería valer **MÁS** de lo que cuesta ahora"
    else:
        simple = "según los flujos esperados, la acción debería valer **MENOS** de lo que cuesta ahora"
    parrafo = (
        f"El modelo estima un valor de **{currency} {base_price:,.2f}** por acción. "
        f"Hoy cotiza a **{currency} {current_price:,.2f}**. "
        f"Eso es un **{upside_pct:+.0f}%** de diferencia: {gut}.\n\n"
        f"En palabras simples: {simple}. "
    )

    if tv_pct > 75:
        parrafo += (
            f"\n\n**Ojo:** más del 75% del valor depende de lo que pase después del año 10 (valor terminal). "
            f"Eso hace la estimación más frágil: pequeños cambios en supuestos mueven mucho el resultado."
        )
    elif 50 <= tv_pct <= 70:
        parrafo += f"\n\nLa estimación es robusta: el valor terminal ({tv_pct:.0f}% del total) está en rango sano."

    if meta:
        g_impl = meta.get("implied_growth_pct")
        if g_impl is not None:
            if g_impl > 6:
                cred = "muy exigente: el mercado descuenta un crecimiento difícil de sostener para siempre"
            elif g_impl < 0:
                cred = "pesimista: el mercado prácticamente no espera crecimiento"
            else:
                cred = "razonable y creíble a largo plazo"
            parrafo += (
                f"\n\n**Lo que el mercado descuenta:** para justificar el precio actual, la empresa tendría que crecer "
                f"un **{g_impl:.1f}% perpetuo**. Eso es {cred}."
            )
        roic = meta.get("roic_pct")
        rvw = meta.get("roic_vs_wacc")
        if roic is not None and rvw:
            parrafo += (
                f"\n\n**Calidad del negocio:** ROIC aproximado {roic:.1f}% vs WACC {meta.get('wacc_pct', 0):.1f}% -> "
                f"la empresa **{rvw}** (gana {'más' if 'crea' in rvw else 'menos'} que el coste de su capital)."
            )

    return badge, color, parrafo


def reliability_note(inputs: dict) -> str:
    md = inputs["market_data"]
    n_years = len(inputs.get("historical", {}))
    flags = []
    if not md.get("current_price_eur"):
        flags.append("precio actual no disponible")
    if not md.get("market_cap_eur_m"):
        flags.append("capitalización no disponible")
    if n_years < 4:
        flags.append(f"solo {n_years} años de histórico (ideal 5)")

    quality = "Alta" if not flags else ("Media" if len(flags) == 1 else "Baja")
    base = (
        f"**Fiabilidad de datos: {quality}** | Fuente: Financial Modeling Prep (fallback yfinance) | "
        f"Histórico: {n_years} años | Fecha: {inputs.get('as_of_date', 'n/d')}"
    )
    if flags:
        base += f"\n\nLimitaciones detectadas: {', '.join(flags)}. Verifica contra el reporte anual oficial."
    else:
        base += "\n\nDatos completos. Aun así, verifica siempre contra el reporte anual oficial antes de decidir."
    return base
