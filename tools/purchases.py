from odoo_client import odoo


def get_compras_precio_por_proveedor(
    product_name: str,
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    domain: list = [
        ("product_id.name", "ilike", product_name),
        ("state", "in", ["purchase", "done"]),
    ]
    if date_from:
        domain.append(("order_id.date_order", ">=", date_from))
    if date_to:
        domain.append(("order_id.date_order", "<=", date_to))

    lines = odoo.search_read(
        model="purchase.order.line",
        domain=domain,
        fields=["partner_id", "product_qty", "price_unit"],
        limit=5000,
    )
    if not lines:
        return [{"error": f"No se encontraron compras del producto '{product_name}'"}]

    suppliers: dict = {}
    for line in lines:
        partner = line["partner_id"][1] if line.get("partner_id") else "Sin proveedor"
        if partner not in suppliers:
            suppliers[partner] = {"total_kg": 0.0, "precios": []}
        suppliers[partner]["total_kg"] += line["product_qty"] or 0
        if line["price_unit"] > 0:
            suppliers[partner]["precios"].append(line["price_unit"])

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
            "num_compras": len(precios),
        })

    result.sort(key=lambda x: x["precio_medio"])
    return result
