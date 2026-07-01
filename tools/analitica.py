from odoo_client import odoo
from datetime import date


def _default_year(date_from: str, date_to: str):
    if not date_from and not date_to:
        date_from = f"{date.today().year}-01-01"
    return date_from, date_to


def _domain(date_from: str, date_to: str, familia_nombre: str = "") -> list:
    domain: list = [["category", "=", "invoice"]]
    if date_from:
        domain.append(["date", ">=", date_from])
    if date_to:
        domain.append(["date", "<=", date_to])
    if familia_nombre:
        domain.append(["family_id.name", "ilike", familia_nombre])
    return domain


def _precio(importe: float, kg: float) -> float:
    return round(importe / kg, 4) if kg else 0


def get_analitica_resumen_por_cliente(
    date_from: str = "", date_to: str = "", familia_nombre: str = "", limit: int = 20
) -> list[dict]:
    date_from, date_to = _default_year(date_from, date_to)
    groups = odoo.read_group(
        "account.analytic.line",
        _domain(date_from, date_to, familia_nombre),
        ["partner_id", "amount:sum", "unit_amount:sum"],
        ["partner_id"],
        orderby="amount desc",
    )
    result = []
    for g in groups[:limit]:
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
    date_from: str = "", date_to: str = "", familia_nombre: str = "", limit: int = 20
) -> list[dict]:
    date_from, date_to = _default_year(date_from, date_to)
    groups = odoo.read_group(
        "account.analytic.line",
        _domain(date_from, date_to, familia_nombre),
        ["farm_id", "amount:sum", "unit_amount:sum"],
        ["farm_id"],
        orderby="amount desc",
    )
    result = []
    for g in groups[:limit]:
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
    date_from: str = "", date_to: str = "", familia_nombre: str = "", limit: int = 20
) -> list[dict]:
    date_from, date_to = _default_year(date_from, date_to)
    groups = odoo.read_group(
        "account.analytic.line",
        _domain(date_from, date_to, familia_nombre),
        ["variety_id", "amount:sum", "unit_amount:sum"],
        ["variety_id"],
        orderby="amount desc",
    )
    # Enrich with family name via alfinf.variety
    var_ids = [g["variety_id"][0] for g in groups if g.get("variety_id")]
    var_map: dict = {}
    if var_ids:
        varieties = odoo.search_read(
            "alfinf.variety", [["id", "in", var_ids[:limit]]],
            ["name", "family_id"], limit=limit,
        )
        var_map = {v["id"]: v for v in varieties}

    result = []
    for g in groups[:limit]:
        if not g.get("variety_id"):
            continue
        vid = g["variety_id"][0]
        v = var_map.get(vid, {})
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
        limit=500,
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

    # Totales exactos via read_group (independiente del límite de líneas)
    totales = odoo.read_group(
        "account.analytic.line",
        [["trace_id", "=", t["id"]], ["category", "=", "invoice"]],
        ["amount:sum", "unit_amount:sum"],
        [],
    )
    total_kg = totales[0]["unit_amount"] if totales else 0
    total_eur = totales[0]["amount"] if totales else 0
    total_lineas = odoo.search_count("account.analytic.line",
                                     [["trace_id", "=", t["id"]], ["category", "=", "invoice"]])

    return {
        "trazabilidad": t["name"],
        "agricultor": t["partner_id"][1] if t["partner_id"] else "",
        "finca": t["farm_id"][1] if t["farm_id"] else "",
        "parcela": t["plot_id"][1] if t["plot_id"] else "",
        "familia": t["family_id"][1] if t["family_id"] else "",
        "variedad": t["variety_id"][1] if t["variety_id"] else "",
        "total_kg": round(total_kg, 2),
        "total_eur": round(total_eur, 2),
        "precio_medio_kg": round(total_eur / total_kg, 4) if total_kg else 0,
        "num_movimientos": total_lineas,
        "movimientos_mostrados": len(movimientos),
        "movimientos": movimientos,
    }


def get_analitica_resumen_por_parcela(
    date_from: str = "",
    date_to: str = "",
    agricultor_nombre: str = "",
    familia_nombre: str = "",
    limit: int = 30,
) -> list[dict]:
    date_from, date_to = _default_year(date_from, date_to)
    domain = _domain(date_from, date_to, familia_nombre)

    if agricultor_nombre:
        traces_filter = odoo.search_read(
            "alfinf.trace",
            [["partner_id.name", "ilike", agricultor_nombre]],
            ["id"], limit=500,
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

    # Enrich with alfinf.trace: agricultor, finca, familia, variedad
    trace_ids = [g["trace_id"][0] for g in groups[:limit] if g.get("trace_id")]
    trace_map: dict = {}
    if trace_ids:
        traces = odoo.search_read(
            "alfinf.trace",
            [["id", "in", trace_ids]],
            ["name", "partner_id", "farm_id", "family_id", "variety_id"],
            limit=limit,
        )
        trace_map = {t["id"]: t for t in traces}

    result = []
    for g in groups[:limit]:
        if not g.get("trace_id"):
            continue
        tid = g["trace_id"][0]
        t = trace_map.get(tid, {})
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
