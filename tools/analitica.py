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
