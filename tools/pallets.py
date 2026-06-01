from odoo_client import odoo
from datetime import date


def _date_domain(field: str, date_from: str, date_to: str) -> list:
    domain = []
    if date_from:
        domain.append([field, ">=", date_from])
    if date_to:
        domain.append([field, "<=", date_to])
    return domain


def get_pallets_sin_albaran(limit: int = 50, date_from: str = "", date_to: str = "") -> list[dict]:
    domain = [["sale_order_id", "=", False]] + _date_domain("date", date_from, date_to)
    records = odoo.search_read(
        "alfinf.pallet.out",
        domain,
        ["name", "partner_id", "pallet_type_id", "total_kilos", "kg_net", "date", "operating_unit_id"],
        limit=limit,
        order="date desc",
    )
    return [
        {
            "pallet": r["name"],
            "cliente": r["partner_id"][1] if r["partner_id"] else "",
            "tipo": r["pallet_type_id"][1] if r["pallet_type_id"] else "",
            "kilos_bruto": r["total_kilos"],
            "kilos_neto": r["kg_net"],
            "fecha": r["date"],
            "centro": r["operating_unit_id"][1] if r["operating_unit_id"] else "",
        }
        for r in records
    ]


def get_pallets_con_albaran(limit: int = 50, date_from: str = "", date_to: str = "") -> list[dict]:
    if not date_from and not date_to:
        date_from = f"{date.today().year}-01-01"
    domain = [["sale_order_id", "!=", False]] + _date_domain("date", date_from, date_to)
    records = odoo.search_read(
        "alfinf.pallet.out",
        domain,
        ["name", "partner_id", "sale_order_name", "sale_order_partner", "sale_order_date",
         "total_kilos", "kg_net", "date", "state", "operating_unit_id"],
        limit=limit,
        order="date desc",
    )
    return [
        {
            "pallet": r["name"],
            "albaran": r["sale_order_name"] or "",
            "cliente": r["partner_id"][1] if r["partner_id"] else r["sale_order_partner"] or "",
            "fecha_pallet": r["date"],
            "fecha_albaran": r["sale_order_date"] or "",
            "kilos_bruto": r["total_kilos"],
            "kilos_neto": r["kg_net"],
            "estado": r["state"] or "",
            "centro": r["operating_unit_id"][1] if r["operating_unit_id"] else "",
        }
        for r in records
    ]


def get_pallet_trazabilidad(referencia: str) -> dict:
    pallets = odoo.search_read(
        "alfinf.pallet.out",
        [["name", "=", referencia]],
        ["name", "partner_id", "sale_order_name", "sale_order_date", "total_kilos",
         "kg_net", "date", "state", "pallet_type_id", "operating_unit_id", "observations"],
        limit=1,
    )
    if not pallets:
        return {"error": f"Pallet '{referencia}' no encontrado"}

    p = pallets[0]
    lines = odoo.search_read(
        "alfinf.pallet.out.line",
        [["pallet_id", "=", p["id"]]],
        ["product_id", "family_id", "variety_ids", "farmer_id", "kilos",
         "box_quantity", "euro_unit", "ammount_euro", "pallet_in_id", "state"],
        limit=100,
    )

    lineas = []
    for l in lines:
        # Obtener variedades
        variety_names = []
        if l.get("variety_ids"):
            varieties = odoo.search_read(
                "alfinf.variety", [["id", "in", l["variety_ids"]]], ["name"], limit=10
            )
            variety_names = [v["name"] for v in varieties]

        lineas.append({
            "producto": l["product_id"][1] if l["product_id"] else "",
            "familia": l["family_id"][1] if l["family_id"] else "",
            "variedades": variety_names,
            "agricultor": l["farmer_id"][1] if l["farmer_id"] else "",
            "pallet_entrada": l["pallet_in_id"][1] if l["pallet_in_id"] else "",
            "kilos": l["kilos"],
            "cajas": l["box_quantity"],
            "euro_kg": l["euro_unit"],
            "importe": l["ammount_euro"],
            "estado": l["state"] or "",
        })

    return {
        "pallet": p["name"],
        "tipo": p["pallet_type_id"][1] if p["pallet_type_id"] else "",
        "cliente": p["partner_id"][1] if p["partner_id"] else "",
        "albaran": p["sale_order_name"] or "",
        "fecha_albaran": p["sale_order_date"] or "",
        "fecha_pallet": p["date"],
        "kilos_bruto": p["total_kilos"],
        "kilos_neto": p["kg_net"],
        "estado": p["state"] or "",
        "centro": p["operating_unit_id"][1] if p["operating_unit_id"] else "",
        "observaciones": p["observations"] or "",
        "lineas": lineas,
    }


def get_pallets_entradas_agricultor(date_from: str = "", date_to: str = "", limit: int = 30) -> list[dict]:
    if not date_from and not date_to:
        date_from = f"{date.today().year}-01-01"
    domain = _date_domain("date", date_from, date_to)
    records = odoo.read_group(
        "alfinf.pallet.in",
        domain,
        ["partner_id", "pallet_quantity:sum", "box_quantity:sum", "kg_gross:sum", "kg_net:sum"],
        ["partner_id"],
        orderby="kg_gross desc",
    )
    result = []
    for r in records[:limit]:
        if not r.get("partner_id"):
            continue
        result.append({
            "agricultor": r["partner_id"][1],
            "pallets": r["pallet_quantity"],
            "cajas": r["box_quantity"],
            "kg_bruto": r["kg_gross"],
            "kg_neto": r["kg_net"],
        })
    return result


def get_pallets_stock(agricultor_name: str = "") -> list[dict]:
    domain: list = [["in_stock", "=", True]]
    if agricultor_name:
        domain.append(["partner_id.name", "ilike", agricultor_name])
    records = odoo.search_read(
        "alfinf.pallet.in",
        domain,
        ["name", "partner_id", "product_id", "family_id", "pallet_stock",
         "kg_stock", "box_stock", "date", "operating_unit_id"],
        limit=100,
        order="date desc",
    )
    return [
        {
            "pallet_entrada": r["name"],
            "agricultor": r["partner_id"][1] if r["partner_id"] else "",
            "producto": r["product_id"][1] if r["product_id"] else "",
            "familia": r["family_id"][1] if r["family_id"] else "",
            "pallets_pendientes": r["pallet_stock"],
            "kg_pendientes": r["kg_stock"],
            "cajas_pendientes": r["box_stock"],
            "fecha_entrada": r["date"],
            "centro": r["operating_unit_id"][1] if r["operating_unit_id"] else "",
        }
        for r in records
    ]
