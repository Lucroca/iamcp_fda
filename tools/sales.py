from odoo_client import odoo


def get_sellers() -> list[dict]:
    """Devuelve la lista de vendedores que tienen pedidos confirmados."""
    groups = odoo.read_group(
        model="sale.order",
        domain=[("state", "in", ["sale", "done"]), ("user_id", "!=", False)],
        fields=["user_id", "id:count"],
        groupby=["user_id"],
        orderby="user_id asc",
    )
    return [
        {"id": g["user_id"][0], "nombre": g["user_id"][1]}
        for g in groups if g["user_id"]
    ]


def get_sales_orders(
    state: str = "all",
    limit: int = 20,
    date_from: str = "",
    date_to: str = "",
    seller_id: int = 0,
    customer_name: str = "",
) -> list[dict]:
    """
    Obtiene pedidos de venta de Odoo.

    Args:
        state: Estado del pedido. Valores: 'draft', 'sent', 'sale', 'done', 'cancel', 'all'
        limit: Número máximo de resultados (1-100)
        date_from: Fecha inicio en formato YYYY-MM-DD
        date_to: Fecha fin en formato YYYY-MM-DD
        seller_id: ID del vendedor para filtrar (0 = todos)
        customer_name: Nombre o parte del nombre del cliente para filtrar
    """
    domain: list = []
    if state != "all":
        domain.append(("state", "=", state))
    if date_from:
        domain.append(("date_order", ">=", date_from))
    if date_to:
        domain.append(("date_order", "<=", date_to))
    if seller_id:
        domain.append(("user_id", "=", seller_id))
    if customer_name:
        domain.append(("partner_id.name", "ilike", customer_name))

    limit = max(1, min(limit, 100))

    orders = odoo.search_read(
        model="sale.order",
        domain=domain,
        fields=[
            "name", "partner_id", "date_order", "amount_total",
            "amount_untaxed", "state", "user_id", "currency_id",
        ],
        limit=limit,
        order="date_order desc",
    )

    return [
        {
            "referencia": o["name"],
            "cliente": o["partner_id"][1] if o["partner_id"] else "",
            "fecha": o["date_order"],
            "estado": o["state"],
            "vendedor": o["user_id"][1] if o["user_id"] else "",
            "total_sin_impuesto": o["amount_untaxed"],
            "total": o["amount_total"],
            "moneda": o["currency_id"][1] if o["currency_id"] else "",
        }
        for o in orders
    ]


def get_sales_summary_by_customer(
    date_from: str = "",
    date_to: str = "",
    limit: int = 20,
    seller_id: int = 0,
) -> list[dict]:
    """
    Resumen de ventas agrupado por cliente (solo pedidos confirmados).

    Args:
        date_from: Fecha inicio YYYY-MM-DD
        date_to: Fecha fin YYYY-MM-DD
        limit: Número máximo de clientes a devolver
        seller_id: ID del vendedor para filtrar (0 = todos)
    """
    domain: list = [("state", "in", ["sale", "done"])]
    if date_from:
        domain.append(("date_order", ">=", date_from))
    if date_to:
        domain.append(("date_order", "<=", date_to))
    if seller_id:
        domain.append(("user_id", "=", seller_id))

    groups = odoo.read_group(
        model="sale.order",
        domain=domain,
        fields=["partner_id", "amount_total:sum", "id:count"],
        groupby=["partner_id"],
        orderby="amount_total desc",
    )

    return [
        {
            "cliente": g["partner_id"][1] if g["partner_id"] else "Sin cliente",
            "num_pedidos": g["partner_id_count"],
            "total_vendido": round(g["amount_total"], 2),
        }
        for g in groups[:limit]
    ]


def get_top_products(limit: int = 15, seller_id: int = 0) -> list[dict]:
    """Top productos vendidos globalmente (pedidos confirmados), por importe."""
    domain = [("order_id.state", "in", ["sale", "done"])]
    if seller_id:
        domain.append(("order_id.user_id", "=", seller_id))
    groups = odoo.read_group(
        model="sale.order.line",
        domain=domain,
        fields=["product_id", "product_uom_qty:sum", "price_subtotal:sum"],
        groupby=["product_id"],
        orderby="price_subtotal desc",
    )
    return [
        {
            "posicion": i + 1,
            "producto": g["product_id"][1] if g["product_id"] else "Sin producto",
            "cantidad_total": round(g["product_uom_qty"], 2),
            "importe_total": round(g["price_subtotal"], 2),
        }
        for i, g in enumerate(groups[:limit])
    ]


def get_sales_by_month(year: int, seller_id: int = 0) -> list[dict]:
    """Ventas confirmadas agrupadas por mes para un año dado."""
    domain = [
        ("state", "in", ["sale", "done"]),
        ("date_order", ">=", f"{year}-01-01"),
        ("date_order", "<=", f"{year}-12-31"),
    ]
    if seller_id:
        domain.append(("user_id", "=", seller_id))
    groups = odoo.read_group(
        model="sale.order",
        domain=domain,
        fields=["amount_total:sum", "id:count"],
        groupby=["date_order:month"],
        orderby="date_order asc",
    )
    return [
        {
            "mes": g.get("date_order:month") or g.get("date_order", ""),
            "num_pedidos": g.get("__count", g.get("date_order_count", 0)),
            "total": round(g.get("amount_total", 0), 2),
        }
        for g in groups
    ]


def get_pending_orders(limit: int = 50, seller_id: int = 0) -> list[dict]:
    """Presupuestos pendientes (borrador o enviado)."""
    domain = [("state", "in", ["draft", "sent"])]
    if seller_id:
        domain.append(("user_id", "=", seller_id))
    orders = odoo.search_read(
        model="sale.order",
        domain=domain,
        fields=["name", "partner_id", "date_order", "amount_total", "state", "user_id"],
        limit=limit,
        order="date_order desc",
    )
    estados = {"draft": "Borrador", "sent": "Enviado"}
    return [
        {
            "referencia": o["name"],
            "cliente": o["partner_id"][1] if o["partner_id"] else "",
            "fecha": o["date_order"],
            "vendedor": o["user_id"][1] if o["user_id"] else "",
            "estado": estados.get(o["state"], o["state"]),
            "total": o["amount_total"],
        }
        for o in orders
    ]


def get_top_products_by_customer(
    customer_name: str,
    limit: int = 10,
) -> list[dict]:
    """
    Productos más vendidos a un cliente específico, ordenados por importe total.

    Args:
        customer_name: Nombre o parte del nombre del cliente
        limit: Número de productos a devolver
    """
    groups = odoo.read_group(
        model="sale.order.line",
        domain=[
            ("order_id.partner_id.name", "ilike", customer_name),
            ("order_id.state", "in", ["sale", "done"]),
        ],
        fields=["product_id", "product_uom_qty:sum", "price_subtotal:sum"],
        groupby=["product_id"],
        orderby="price_subtotal desc",
    )

    return [
        {
            "posicion": i + 1,
            "producto": g["product_id"][1] if g["product_id"] else "Sin producto",
            "cantidad_total": round(g["product_uom_qty"], 2),
            "importe_total": round(g["price_subtotal"], 2),
        }
        for i, g in enumerate(groups[:limit])
    ]


def get_ventas_kilos_por_producto(
    date_from: str = "",
    date_to: str = "",
    customer_name: str = "",
    limit: int = 20,
) -> list[dict]:
    domain: list = [("order_id.state", "in", ["sale", "done"])]
    if date_from:
        domain.append(("order_id.date_order", ">=", date_from))
    if date_to:
        domain.append(("order_id.date_order", "<=", date_to))
    if customer_name:
        domain.append(("order_id.partner_id.name", "ilike", customer_name))

    groups = odoo.read_group(
        model="sale.order.line",
        domain=domain,
        fields=["product_id", "product_uom_qty:sum", "price_subtotal:sum"],
        groupby=["product_id"],
        orderby="product_uom_qty desc",
    )

    result = []
    for g in groups[:limit]:
        if not g.get("product_id"):
            continue
        qty = g["product_uom_qty"] or 0
        revenue = g["price_subtotal"] or 0
        result.append({
            "producto": g["product_id"][1],
            "total_kg": round(qty, 2),
            "precio_medio_kg": round(revenue / qty, 4) if qty else 0,
            "importe_total": round(revenue, 2),
        })
    return result


def get_ventas_precio_por_cliente(
    product_name: str,
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    domain: list = [
        ("product_id.name", "ilike", product_name),
        ("order_id.state", "in", ["sale", "done"]),
    ]
    if date_from:
        domain.append(("order_id.date_order", ">=", date_from))
    if date_to:
        domain.append(("order_id.date_order", "<=", date_to))

    lines = odoo.search_read(
        model="sale.order.line",
        domain=domain,
        fields=["product_id", "order_id", "product_uom_qty", "price_unit", "price_subtotal"],
        limit=5000,
    )
    if not lines:
        return [{"error": f"No se encontraron ventas del producto '{product_name}'"}]

    order_ids = list({l["order_id"][0] for l in lines if l.get("order_id")})
    orders = odoo.search_read(
        model="sale.order",
        domain=[("id", "in", order_ids)],
        fields=["id", "partner_id"],
        limit=len(order_ids) + 1,
    )
    order_partner = {
        o["id"]: o["partner_id"][1] if o["partner_id"] else "Sin cliente"
        for o in orders
    }

    customers: dict = {}
    for line in lines:
        partner = order_partner.get(line["order_id"][0], "Sin cliente") if line.get("order_id") else "Sin cliente"
        if partner not in customers:
            customers[partner] = {"total_kg": 0.0, "total_revenue": 0.0, "precios": []}
        customers[partner]["total_kg"] += line["product_uom_qty"] or 0
        customers[partner]["total_revenue"] += line["price_subtotal"] or 0
        if line["price_unit"] > 0:
            customers[partner]["precios"].append(line["price_unit"])

    result = []
    for nombre, data in customers.items():
        qty = data["total_kg"]
        rev = data["total_revenue"]
        precios = data["precios"]
        if not qty:
            continue
        result.append({
            "cliente": nombre,
            "total_kg": round(qty, 2),
            "precio_medio_real": round(rev / qty, 4),
            "precio_min": round(min(precios), 4) if precios else 0,
            "precio_max": round(max(precios), 4) if precios else 0,
            "importe_total": round(rev, 2),
        })

    result.sort(key=lambda x: x["precio_medio_real"], reverse=True)
    return result


def get_sales_summary_by_seller(
    date_from: str = "",
    date_to: str = "",
    customer_name: str = "",
) -> list[dict]:
    """
    Resumen de ventas agrupado por vendedor (pedidos confirmados).

    Args:
        date_from: Fecha inicio YYYY-MM-DD
        date_to: Fecha fin YYYY-MM-DD
        customer_name: Nombre o parte del nombre del cliente para filtrar
    """
    domain: list = [("state", "in", ["sale", "done"])]
    if date_from:
        domain.append(("date_order", ">=", date_from))
    if date_to:
        domain.append(("date_order", "<=", date_to))
    if customer_name:
        domain.append(("partner_id.name", "ilike", customer_name))

    groups = odoo.read_group(
        model="sale.order",
        domain=domain,
        fields=["user_id", "amount_total:sum", "id:count"],
        groupby=["user_id"],
        orderby="amount_total desc",
    )

    return [
        {
            "vendedor": g["user_id"][1] if g["user_id"] else "Sin vendedor",
            "num_pedidos": g["user_id_count"],
            "total_vendido": round(g["amount_total"], 2),
        }
        for g in groups
    ]
