from odoo_client import odoo


def get_compras_precio_por_proveedor(
    product_name: str,
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    domain: list = [
        ("product_id.name", "ilike", product_name),
        ("order_id.state", "in", ["purchase", "done"]),
    ]
    if date_from:
        domain.append(("order_id.date_order", ">=", date_from))
    if date_to:
        domain.append(("order_id.date_order", "<=", date_to))

    lines = odoo.search_read(
        model="purchase.order.line",
        domain=domain,
        fields=["product_id", "order_id", "product_qty", "price_unit"],
        limit=5000,
    )
    if not lines:
        return [{"error": f"No se encontraron compras del producto '{product_name}'"}]

    order_ids = list({l["order_id"][0] for l in lines if l.get("order_id")})
    orders = odoo.search_read(
        model="purchase.order",
        domain=[("id", "in", order_ids)],
        fields=["id", "partner_id", "date_order"],
        limit=len(order_ids) + 1,
    )
    order_info = {o["id"]: o for o in orders}

    suppliers: dict = {}
    for line in lines:
        if not line.get("order_id"):
            continue
        order = order_info.get(line["order_id"][0], {})
        partner = order.get("partner_id") or [None, "Sin proveedor"]
        partner_name = partner[1] if partner else "Sin proveedor"

        if partner_name not in suppliers:
            suppliers[partner_name] = {"total_kg": 0.0, "precios": [], "ultima_fecha": ""}
        suppliers[partner_name]["total_kg"] += line["product_qty"] or 0
        if line["price_unit"] > 0:
            suppliers[partner_name]["precios"].append(line["price_unit"])
        fecha = (order.get("date_order") or "")[:10]
        if fecha > suppliers[partner_name]["ultima_fecha"]:
            suppliers[partner_name]["ultima_fecha"] = fecha

    result = []
    for nombre, data in suppliers.items():
        precios = data["precios"]
        if not precios:
            continue
        result.append({
            "proveedor": nombre,
            "total_kg": round(data["total_kg"], 2),
            "precio_medio": round(sum(precios) / len(precios), 4),
            "precio_min": round(min(precios), 4),
            "precio_max": round(max(precios), 4),
            "ultima_compra": data["ultima_fecha"],
            "num_compras": len(precios),
        })

    result.sort(key=lambda x: x["precio_medio"])
    return result
