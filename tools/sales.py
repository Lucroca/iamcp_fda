from odoo_client import odoo


def get_sellers() -> list[dict]:
    """Devuelve la lista de vendedores que tienen pedidos confirmados."""
    groups = odoo.read_group(
        model="sale.order",
        domain=[("state", "in", ["draft", "sent", "sale", "done"]), ("user_id", "!=", False)],
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
    domain: list = [("state", "in", ["draft", "sent", "sale", "done"])]
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


def get_top_products(limit: int = 15, seller_id: int = 0, date_from: str = "", date_to: str = "", familia_nombre: str = "") -> list[dict]:
    """Top productos vendidos globalmente (pedidos confirmados), por importe."""
    from datetime import date
    domain = [
        ("order_id.state", "in", ["draft", "sent", "sale", "done"]),
        ("order_id.date_order", ">=", date_from or f"{date.today().year}-01-01"),
    ]
    if date_to:
        domain.append(("order_id.date_order", "<=", date_to))
    if seller_id:
        domain.append(("order_id.user_id", "=", seller_id))
    if familia_nombre:
        domain.append(("family_id.name", "ilike", familia_nombre))
    groups = odoo.read_group(
        model="sale.order.line",
        domain=domain,
        fields=["product_id", "family_id", "product_uom_qty:sum", "price_subtotal:sum"],
        groupby=["product_id", "family_id"],
        orderby="price_subtotal desc",
    )
    seen: dict = {}
    for g in groups:
        if not g.get("product_id"):
            continue
        prod = g["product_id"][1]
        if prod not in seen:
            seen[prod] = {
                "familia": g["family_id"][1] if g.get("family_id") else "",
                "qty": 0.0, "revenue": 0.0,
            }
        seen[prod]["qty"] += g["product_uom_qty"] or 0
        seen[prod]["revenue"] += g["price_subtotal"] or 0
    return [
        {
            "posicion": i + 1,
            "producto": prod,
            "familia": data["familia"],
            "cantidad_total": round(data["qty"], 2),
            "importe_total": round(data["revenue"], 2),
        }
        for i, (prod, data) in enumerate(
            sorted(seen.items(), key=lambda x: x[1]["revenue"], reverse=True)[:limit]
        )
    ]


def get_sales_by_month(year: int, seller_id: int = 0) -> list[dict]:
    """Ventas confirmadas agrupadas por mes para un año dado."""
    domain = [
        ("state", "in", ["draft", "sent", "sale", "done"]),
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


def get_albaran_detalle(referencia: str) -> dict:
    orders = odoo.search_read(
        model="sale.order",
        domain=[("name", "ilike", referencia)],
        fields=[
            "name", "partner_id", "date_order", "state", "amount_untaxed",
            "amount_total", "user_id", "invoice_status", "client_order_ref",
            "destination_id", "carrier_id", "transport_company", "incoterm",
            "payment_term_id", "observation",
        ],
        limit=5,
        order="date_order desc",
    )
    if not orders:
        return {"error": f"No se encontró ningún albarán con referencia '{referencia}'"}

    order = orders[0]
    order_id = order["id"]

    lines = odoo.search_read(
        model="sale.order.line",
        domain=[("order_id", "=", order_id)],
        fields=[
            "product_id", "family_id", "variety", "product_uom_qty",
            "product_uom", "price_unit", "discount", "price_subtotal",
        ],
        limit=200,
    )

    return {
        "referencia": order["name"],
        "ref_cliente": order["client_order_ref"] or "",
        "cliente": order["partner_id"][1] if order["partner_id"] else "",
        "fecha": order["date_order"],
        "estado": order["state"],
        "estado_factura": order["invoice_status"],
        "centro_manipulacion": order["user_id"][1] if order["user_id"] else "",
        "destino": order["destination_id"][1] if order["destination_id"] else "",
        "transportista": order["carrier_id"][1] if order["carrier_id"] else "",
        "empresa_transporte": order["transport_company"] or "",
        "incoterm": order["incoterm"][1] if order["incoterm"] else "",
        "forma_pago": order["payment_term_id"][1] if order["payment_term_id"] else "",
        "observacion": order["observation"] or "",
        "base_imponible": order["amount_untaxed"],
        "total": order["amount_total"],
        "lineas": [
            {
                "producto": l["product_id"][1] if l["product_id"] else "",
                "familia": l["family_id"][1] if l["family_id"] else "",
                "variedad": l["variety"] or "",
                "cantidad": l["product_uom_qty"],
                "unidad": l["product_uom"][1] if l["product_uom"] else "",
                "precio_unit": round(l["price_unit"], 4),
                "descuento": l["discount"],
                "subtotal": round(l["price_subtotal"], 2),
            }
            for l in lines
        ],
    }


def get_top_products_by_customer(
    customer_name: str,
    limit: int = 10,
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    """
    Productos más vendidos a un cliente específico, ordenados por importe total.

    Args:
        customer_name: Nombre o parte del nombre del cliente
        limit: Número de productos a devolver
        date_from: Fecha inicio YYYY-MM-DD (por defecto enero del año actual)
        date_to: Fecha fin YYYY-MM-DD
    """
    from datetime import date
    domain = [
        ("order_id.partner_id.name", "ilike", customer_name),
        ("order_id.state", "in", ["draft", "sent", "sale", "done"]),
        ("order_id.date_order", ">=", date_from or f"{date.today().year}-01-01"),
    ]
    if date_to:
        domain.append(("order_id.date_order", "<=", date_to))
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


def get_ventas_kilos_por_producto(
    date_from: str = "",
    date_to: str = "",
    customer_name: str = "",
    familia_nombre: str = "",
    limit: int = 20,
) -> list[dict]:
    from datetime import date as _date
    domain: list = [
        ("state", "in", ["draft", "sent", "sale", "done"]),
        ("order_id.date_order", ">=", date_from or f"{_date.today().year}-01-01"),
    ]
    if date_to:
        domain.append(("order_id.date_order", "<=", date_to))
    if customer_name:
        domain.append(("order_partner_id.name", "ilike", customer_name))
    if familia_nombre:
        domain.append(("family_id.name", "ilike", familia_nombre))

    groups = odoo.read_group(
        model="sale.order.line",
        domain=domain,
        fields=["product_id", "family_id", "product_uom_qty:sum", "price_subtotal:sum"],
        groupby=["product_id", "family_id"],
        orderby="product_uom_qty desc",
    )

    result = []
    seen_products: dict = {}
    for g in groups:
        if not g.get("product_id"):
            continue
        prod = g["product_id"][1]
        familia = g["family_id"][1] if g.get("family_id") else ""
        qty = g["product_uom_qty"] or 0
        revenue = g["price_subtotal"] or 0
        if prod not in seen_products:
            seen_products[prod] = {"familia": familia, "total_kg": 0.0, "total_revenue": 0.0}
        seen_products[prod]["total_kg"] += qty
        seen_products[prod]["total_revenue"] += revenue

    for prod, data in sorted(seen_products.items(), key=lambda x: x[1]["total_kg"], reverse=True)[:limit]:
        qty = data["total_kg"]
        rev = data["total_revenue"]
        result.append({
            "producto": prod,
            "familia": data["familia"],
            "total_kg": round(qty, 2),
            "precio_medio_kg": round(rev / qty, 4) if qty else 0,
            "importe_total": round(rev, 2),
        })
    return result


def get_ventas_precio_por_cliente(
    product_name: str,
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    from datetime import date as _date
    domain: list = [
        ("product_id.name", "ilike", product_name),
        ("state", "in", ["draft", "sent", "sale", "done"]),
        ("order_id.date_order", ">=", date_from or f"{_date.today().year}-01-01"),
    ]
    if date_to:
        domain.append(("order_id.date_order", "<=", date_to))

    lines = odoo.search_read(
        model="sale.order.line",
        domain=domain,
        fields=["order_partner_id", "product_uom_qty", "price_unit", "price_subtotal"],
        limit=5000,
    )
    if not lines:
        return [{"error": f"No se encontraron ventas del producto '{product_name}'"}]

    customers: dict = {}
    for line in lines:
        partner = line["order_partner_id"][1] if line.get("order_partner_id") else "Sin cliente"
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
    domain: list = [("state", "in", ["draft", "sent", "sale", "done"])]
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
