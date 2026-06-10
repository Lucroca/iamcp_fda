from odoo_client import odoo
from datetime import date as _date


def _date_domain(field: str, date_from: str, date_to: str) -> list:
    domain = []
    if date_from:
        domain.append([field, ">=", date_from])
    if date_to:
        domain.append([field, "<=", date_to])
    return domain


def get_trazabilidad_parcelas(
    agricultor_nombre: str = "",
    finca_nombre: str = "",
    familia_nombre: str = "",
    eco: bool | None = None,
) -> list[dict]:
    domain: list = []
    if agricultor_nombre:
        domain.append(["partner_id.name", "ilike", agricultor_nombre])
    if finca_nombre:
        domain.append(["farm_id.name", "ilike", finca_nombre])
    if familia_nombre:
        domain.append(["family_id.name", "ilike", familia_nombre])
    if eco is not None:
        domain.append(["eco", "=", eco])

    records = odoo.search_read(
        "alfinf.trace",
        domain,
        ["name", "partner_id", "farm_id", "plot_id", "family_id", "variety_id",
         "hectares", "eco", "campaign_id", "pallet_account_id"],
        limit=200,
        order="partner_id asc, name asc",
    )
    return [
        {
            "trazabilidad": r["name"],
            "agricultor": r["partner_id"][1] if r["partner_id"] else "",
            "finca": r["farm_id"][1] if r["farm_id"] else "",
            "parcela": r["plot_id"][1] if r["plot_id"] else "",
            "familia": r["family_id"][1] if r["family_id"] else "",
            "variedad": r["variety_id"][1] if r["variety_id"] else "",
            "hectareas": r["hectares"],
            "eco": r["eco"],
            "campana": r["campaign_id"][1] if r["campaign_id"] else "",
        }
        for r in records
    ]


def get_trazabilidad_kilos_por_parcela(
    date_from: str = "",
    date_to: str = "",
    agricultor_nombre: str = "",
    familia_nombre: str = "",
    limit: int = 30,
) -> list[dict]:
    if not date_from and not date_to:
        date_from = f"{_date.today().year}-01-01"

    domain: list = [["analytic_account_id", "!=", False]]
    domain += _date_domain("date", date_from, date_to)
    if agricultor_nombre:
        domain.append(["farmer_id.name", "ilike", agricultor_nombre])
    if familia_nombre:
        domain.append(["family_id.name", "ilike", familia_nombre])

    groups = odoo._models.execute_kw(
        odoo.db, odoo.uid, odoo.api_key,
        "alfinf.pallet.out.line", "read_group",
        [domain],
        {
            "fields": ["analytic_account_id", "kilos:sum", "ammount_euro:sum", "box_quantity:sum"],
            "groupby": ["analytic_account_id"],
            "orderby": "kilos desc",
            "limit": limit,
        },
    )

    result = []
    for g in groups:
        if not g.get("analytic_account_id"):
            continue
        account_id = g["analytic_account_id"][0]
        account_name = g["analytic_account_id"][1]

        # Buscar info de la traza
        trace = odoo.search_read(
            "alfinf.trace",
            [["pallet_account_id", "=", account_id]],
            ["partner_id", "farm_id", "family_id", "variety_id", "hectares"],
            limit=1,
        )
        t = trace[0] if trace else {}

        kilos = g.get("kilos") or 0
        euros = g.get("ammount_euro") or 0
        result.append({
            "trazabilidad": account_name,
            "agricultor": t.get("partner_id", [None, ""])[1] if t.get("partner_id") else "",
            "finca": t.get("farm_id", [None, ""])[1] if t.get("farm_id") else "",
            "familia": t.get("family_id", [None, ""])[1] if t.get("family_id") else "",
            "variedad": t.get("variety_id", [None, ""])[1] if t.get("variety_id") else "",
            "hectareas": t.get("hectares", 0),
            "total_kg": round(kilos, 2),
            "total_cajas": round(g.get("box_quantity") or 0, 0),
            "importe_total": round(euros, 2),
            "precio_medio_kg": round(euros / kilos, 4) if kilos else 0,
        })
    return result


def get_trazabilidad_detalle_parcela(trazabilidad: str) -> dict:
    traces = odoo.search_read(
        "alfinf.trace",
        [["name", "=", trazabilidad]],
        ["name", "partner_id", "farm_id", "plot_id", "family_id", "variety_id",
         "hectares", "eco", "campaign_id", "pallet_account_id", "cost_account_id"],
        limit=1,
    )
    if not traces:
        return {"error": f"Trazabilidad '{trazabilidad}' no encontrada"}

    t = traces[0]
    account_id = t["pallet_account_id"][0] if t.get("pallet_account_id") else None

    pallets_lines = []
    if account_id:
        lines = odoo.search_read(
            "alfinf.pallet.out.line",
            [["analytic_account_id", "=", account_id]],
            ["pallet_id", "sale_order_name", "sale_order_partner", "sale_order_date",
             "kilos", "box_quantity", "euro_unit", "ammount_euro", "date", "state"],
            limit=200,
            order="date desc",
        )
        for l in lines:
            pallets_lines.append({
                "pallet": l["pallet_id"][1] if l["pallet_id"] else "",
                "albaran": l["sale_order_name"] or "",
                "cliente": l["sale_order_partner"] or "",
                "fecha_albaran": l["sale_order_date"] or "",
                "fecha": l["date"] or "",
                "kilos": l["kilos"],
                "cajas": l["box_quantity"],
                "euro_kg": l["euro_unit"],
                "importe": l["ammount_euro"],
                "estado": l["state"] or "",
            })

    total_kg = sum(l["kilos"] for l in pallets_lines)
    total_euros = sum(l["importe"] for l in pallets_lines)

    return {
        "trazabilidad": t["name"],
        "agricultor": t["partner_id"][1] if t["partner_id"] else "",
        "finca": t["farm_id"][1] if t["farm_id"] else "",
        "parcela": t["plot_id"][1] if t["plot_id"] else "",
        "familia": t["family_id"][1] if t["family_id"] else "",
        "variedad": t["variety_id"][1] if t["variety_id"] else "",
        "hectareas": t["hectares"],
        "eco": t["eco"],
        "campana": t["campaign_id"][1] if t["campaign_id"] else "",
        "total_kg": round(total_kg, 2),
        "importe_total": round(total_euros, 2),
        "precio_medio_kg": round(total_euros / total_kg, 4) if total_kg else 0,
        "movimientos": pallets_lines,
    }
