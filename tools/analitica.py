from odoo_client import odoo
from datetime import date

_BIG = 10000


def _default_year(date_from: str, date_to: str):
    if not date_from and not date_to:
        date_from = f"{date.today().year}-01-01"
    return date_from, date_to


def _domain(date_from: str, date_to: str, familia_nombre: str = "", empresa_nombre: str = "") -> list:
    domain: list = [["category", "=", "invoice"]]
    if date_from:
        domain.append(["date", ">=", date_from])
    if date_to:
        domain.append(["date", "<=", date_to])
    if familia_nombre:
        domain.append(["family_id.name", "ilike", familia_nombre])
    if empresa_nombre:
        domain.append(["company_id.name", "ilike", empresa_nombre])
    return domain


def _precio(importe: float, kg: float) -> float:
    return round(importe / kg, 4) if kg else 0


def get_analitica_resumen_por_cliente(
    date_from: str = "", date_to: str = "", familia_nombre: str = "", empresa_nombre: str = "", limit: int = 0
) -> list[dict]:
    date_from, date_to = _default_year(date_from, date_to)
    groups = odoo.read_group(
        "account.analytic.line",
        _domain(date_from, date_to, familia_nombre, empresa_nombre),
        ["partner_id", "amount:sum", "unit_amount:sum"],
        ["partner_id"],
        orderby="amount desc",
    )
    rows = groups if not limit else groups[:limit]
    result = []
    for g in rows:
        if not g.get("partner_id"):
            continue
        kg = g["unit_amount"] or 0
        imp = g["amount"] or 0
        result.append({
            "cliente": g["partner_id"][1],
            "importe_eur": round(imp, 2),
            "kg": round(kg, 2),
            "precio_medio_kg": _precio(imp, kg),
        })
    return result


def get_analitica_resumen_por_finca(
    date_from: str = "", date_to: str = "", familia_nombre: str = "", empresa_nombre: str = "", limit: int = 0
) -> list[dict]:
    date_from, date_to = _default_year(date_from, date_to)
    groups = odoo.read_group(
        "account.analytic.line",
        _domain(date_from, date_to, familia_nombre, empresa_nombre),
        ["farm_id", "amount:sum", "unit_amount:sum"],
        ["farm_id"],
        orderby="amount desc",
    )
    rows = groups if not limit else groups[:limit]
    result = []
    for g in rows:
        if not g.get("farm_id"):
            continue
        kg = g["unit_amount"] or 0
        imp = g["amount"] or 0
        result.append({
            "finca": g["farm_id"][1],
            "importe_eur": round(imp, 2),
            "kg": round(kg, 2),
            "precio_medio_kg": _precio(imp, kg),
        })
    return result


def get_analitica_resumen_por_variedad(
    date_from: str = "", date_to: str = "", familia_nombre: str = "", empresa_nombre: str = "", limit: int = 0
) -> list[dict]:
    date_from, date_to = _default_year(date_from, date_to)
    groups = odoo.read_group(
        "account.analytic.line",
        _domain(date_from, date_to, familia_nombre, empresa_nombre),
        ["variety_id", "amount:sum", "unit_amount:sum"],
        ["variety_id"],
        orderby="amount desc",
    )
    rows = groups if not limit else groups[:limit]

    var_ids = [g["variety_id"][0] for g in rows if g.get("variety_id")]
    var_map: dict = {}
    if var_ids:
        varieties = odoo.search_read(
            "alfinf.variety", [["id", "in", var_ids]],
            ["name", "family_id"], limit=_BIG,
        )
        var_map = {v["id"]: v for v in varieties}

    result = []
    for g in rows:
        if not g.get("variety_id"):
            continue
        v = var_map.get(g["variety_id"][0], {})
        kg = g["unit_amount"] or 0
        imp = g["amount"] or 0
        result.append({
            "variedad": g["variety_id"][1],
            "familia": v.get("family_id", [None, ""])[1] if v.get("family_id") else "",
            "importe_eur": round(imp, 2),
            "kg": round(kg, 2),
            "precio_medio_kg": _precio(imp, kg),
        })
    return result


def get_analitica_detalle_parcela(trazabilidad: str) -> dict:
    traces = odoo.search_read(
        "alfinf.trace",
        [["name", "=", trazabilidad]],
        ["name", "partner_id", "farm_id", "plot_id", "family_id", "variety_id"],
        limit=1,
    )
    if not traces:
        return {"error": f"Parcela '{trazabilidad}' no encontrada"}
    t = traces[0]

    lines = odoo.search_read(
        "account.analytic.line",
        [["trace_id", "=", t["id"]], ["category", "=", "invoice"]],
        ["name", "date", "partner_id", "sale_order_id", "invoice_number", "invoice_date",
         "pallet_number", "pallet_date", "pallet_line_id",
         "product_id", "family_id", "farm_id", "plot_id", "variety_id",
         "unit_amount", "price_unit", "amount", "loss_gain"],
        limit=_BIG,
        order="date asc",
    )

    movimientos = [
        {
            "nombre": l["name"] or "",
            "fecha": l["date"],
            "cliente": l["partner_id"][1] if l["partner_id"] else "",
            "albaran": l["sale_order_id"][1] if l["sale_order_id"] else "",
            "factura": l["invoice_number"] or "",
            "fecha_factura": l["invoice_date"] or "",
            "pallet": l["pallet_number"] or "",
            "fecha_pallet": l["pallet_date"] or "",
            "linea_pallet": l["pallet_line_id"][1] if l["pallet_line_id"] else "",
            "producto": l["product_id"][1] if l["product_id"] else "",
            "familia": l["family_id"][1] if l["family_id"] else "",
            "finca": l["farm_id"][1] if l["farm_id"] else "",
            "parcela": l["plot_id"][1] if l["plot_id"] else "",
            "variedad": l["variety_id"][1] if l["variety_id"] else "",
            "kg": l["unit_amount"],
            "precio_kg": l["price_unit"],
            "importe_eur": round(l["amount"], 2),
            "perdida_ganancia": l["loss_gain"],
        }
        for l in lines
    ]

    total_kg = sum(m["kg"] for m in movimientos)
    total_eur = sum(m["importe_eur"] for m in movimientos)

    return {
        "trazabilidad": t["name"],
        "agricultor": t["partner_id"][1] if t["partner_id"] else "",
        "finca": t["farm_id"][1] if t["farm_id"] else "",
        "parcela": t["plot_id"][1] if t["plot_id"] else "",
        "familia": t["family_id"][1] if t["family_id"] else "",
        "variedad": t["variety_id"][1] if t["variety_id"] else "",
        "total_kg": round(total_kg, 2),
        "total_eur": round(total_eur, 2),
        "precio_medio_kg": _precio(total_eur, total_kg),
        "num_movimientos": len(movimientos),
        "movimientos": movimientos,
    }


def get_analitica_resumen_por_parcela(
    date_from: str = "",
    date_to: str = "",
    agricultor_nombre: str = "",
    familia_nombre: str = "",
    limit: int = 0,
) -> list[dict]:
    date_from, date_to = _default_year(date_from, date_to)
    domain = _domain(date_from, date_to, familia_nombre)

    if agricultor_nombre:
        traces_filter = odoo.search_read(
            "alfinf.trace",
            [["partner_id.name", "ilike", agricultor_nombre]],
            ["id"], limit=_BIG,
        )
        if not traces_filter:
            return []
        domain.append(["trace_id", "in", [t["id"] for t in traces_filter]])

    groups = odoo.read_group(
        "account.analytic.line",
        domain,
        ["trace_id", "amount:sum", "unit_amount:sum"],
        ["trace_id"],
        orderby="amount desc",
    )
    rows = groups if not limit else groups[:limit]

    trace_ids = [g["trace_id"][0] for g in rows if g.get("trace_id")]
    trace_map: dict = {}
    if trace_ids:
        traces = odoo.search_read(
            "alfinf.trace",
            [["id", "in", trace_ids]],
            ["name", "partner_id", "farm_id", "family_id", "variety_id"],
            limit=_BIG,
        )
        trace_map = {t["id"]: t for t in traces}

    result = []
    for g in rows:
        if not g.get("trace_id"):
            continue
        t = trace_map.get(g["trace_id"][0], {})
        kg = g["unit_amount"] or 0
        imp = g["amount"] or 0
        result.append({
            "trazabilidad": g["trace_id"][1],
            "agricultor": t.get("partner_id", [None, ""])[1] if t.get("partner_id") else "",
            "finca": t.get("farm_id", [None, ""])[1] if t.get("farm_id") else "",
            "familia": t.get("family_id", [None, ""])[1] if t.get("family_id") else "",
            "variedad": t.get("variety_id", [None, ""])[1] if t.get("variety_id") else "",
            "importe_eur": round(imp, 2),
            "kg": round(kg, 2),
            "precio_medio_kg": _precio(imp, kg),
        })
    return result


def get_analitica_evolucion_mensual(
    date_from: str = "",
    date_to: str = "",
    familia_nombre: str = "",
    empresa_nombre: str = "",
) -> list[dict]:
    date_from, date_to = _default_year(date_from, date_to)
    lines = odoo.search_read(
        "account.analytic.line",
        _domain(date_from, date_to, familia_nombre, empresa_nombre),
        ["date", "amount", "unit_amount"],
        limit=_BIG,
    )
    by_month: dict = {}
    for l in lines:
        mes = l["date"][:7]  # YYYY-MM
        if mes not in by_month:
            by_month[mes] = {"importe_eur": 0.0, "kg": 0.0}
        by_month[mes]["importe_eur"] += l["amount"] or 0
        by_month[mes]["kg"] += l["unit_amount"] or 0

    return [
        {
            "mes": mes,
            "importe_eur": round(datos["importe_eur"], 2),
            "kg": round(datos["kg"], 2),
            "precio_medio_kg": _precio(datos["importe_eur"], datos["kg"]),
        }
        for mes, datos in sorted(by_month.items())
    ]


def get_analitica_variedad_por_cliente(
    variedad_nombre: str,
    date_from: str = "",
    date_to: str = "",
    empresa_nombre: str = "",
) -> list[dict]:
    date_from, date_to = _default_year(date_from, date_to)
    domain = _domain(date_from, date_to, empresa_nombre=empresa_nombre)
    domain.append(["variety_id.name", "ilike", variedad_nombre])

    groups = odoo.read_group(
        "account.analytic.line",
        domain,
        ["partner_id", "amount:sum", "unit_amount:sum"],
        ["partner_id"],
        orderby="amount desc",
    )
    result = []
    for g in groups:
        if not g.get("partner_id"):
            continue
        kg = g["unit_amount"] or 0
        imp = g["amount"] or 0
        result.append({
            "cliente": g["partner_id"][1],
            "importe_eur": round(imp, 2),
            "kg": round(kg, 2),
            "precio_medio_kg": _precio(imp, kg),
        })
    return result


def get_rentabilidad_global(
    date_from: str = "",
    date_to: str = "",
    empresa_nombre: str = "",
) -> dict:
    date_from, date_to = _default_year(date_from, date_to)

    # Ingresos: account.analytic.line (ventas facturadas)
    ing_groups = odoo.read_group(
        "account.analytic.line",
        _domain(date_from, date_to, empresa_nombre=empresa_nombre),
        ["family_id", "amount:sum", "unit_amount:sum"],
        ["family_id"],
        orderby="amount desc",
    )

    # Costes: facturas de compra (liquidación al agricultor)
    cost_domain: list = [
        ["move_id.move_type", "=", "in_invoice"],
        ["move_id.state", "=", "posted"],
        ["display_type", "=", "product"],
    ]
    if date_from:
        cost_domain.append(["move_id.invoice_date", ">=", date_from])
    if date_to:
        cost_domain.append(["move_id.invoice_date", "<=", date_to])
    if empresa_nombre:
        cost_domain.append(["company_id.name", "ilike", empresa_nombre])

    cost_groups = odoo.read_group(
        "account.move.line",
        cost_domain,
        ["family_id", "price_subtotal:sum", "quantity:sum"],
        ["family_id"],
        orderby="price_subtotal desc",
    )

    # Construir mapa costes por familia
    coste_por_familia: dict = {}
    for g in cost_groups:
        if g.get("family_id"):
            nombre = g["family_id"][1]
            coste_por_familia[nombre] = {
                "coste_eur": round(g["price_subtotal"] or 0, 2),
                "kg_compra": round(g["quantity"] or 0, 2),
            }

    # Construir resultado por familia
    familias = []
    total_ingresos = 0.0
    total_costes = 0.0
    total_kg = 0.0

    for g in ing_groups:
        familia = g["family_id"][1] if g.get("family_id") else "Sin familia"
        ing = g["amount"] or 0
        kg = g["unit_amount"] or 0
        coste_data = coste_por_familia.get(familia, {})
        coste = coste_data.get("coste_eur", 0)
        margen = ing - coste
        margen_pct = round(margen / ing * 100, 2) if ing else 0

        total_ingresos += ing
        total_costes += coste
        total_kg += kg

        familias.append({
            "familia": familia,
            "ingresos_eur": round(ing, 2),
            "coste_eur": coste,
            "margen_eur": round(margen, 2),
            "margen_pct": margen_pct,
            "kg_vendidos": round(kg, 2),
            "precio_venta_kg": _precio(ing, kg),
            "coste_kg": _precio(coste, coste_data.get("kg_compra", 0)),
        })

    margen_total = total_ingresos - total_costes
    return {
        "periodo": {"desde": date_from, "hasta": date_to or "hoy"},
        "empresa": empresa_nombre or "todas",
        "resumen": {
            "ingresos_eur": round(total_ingresos, 2),
            "costes_eur": round(total_costes, 2),
            "margen_eur": round(margen_total, 2),
            "margen_pct": round(margen_total / total_ingresos * 100, 2) if total_ingresos else 0,
            "kg_totales": round(total_kg, 2),
        },
        "por_familia": familias,
    }
