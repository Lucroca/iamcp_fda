from odoo_client import odoo
from datetime import date

_BIG = 10000


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
    date_from: str = "", date_to: str = "", familia_nombre: str = "", limit: int = 0
) -> list[dict]:
    date_from, date_to = _default_year(date_from, date_to)
    groups = odoo.read_group(
        "account.analytic.line",
        _domain(date_from, date_to, familia_nombre),
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
    date_from: str = "", date_to: str = "", familia_nombre: str = "", limit: int = 0
) -> list[dict]:
    date_from, date_to = _default_year(date_from, date_to)
    groups = odoo.read_group(
        "account.analytic.line",
        _domain(date_from, date_to, familia_nombre),
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
    date_from: str = "", date_to: str = "", familia_nombre: str = "", limit: int = 0
) -> list[dict]:
    date_from, date_to = _default_year(date_from, date_to)
    groups = odoo.read_group(
        "account.analytic.line",
        _domain(date_from, date_to, familia_nombre),
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
