from odoo_client import odoo


def search_customers(
    query: str = "",
    is_company: bool | None = None,
    limit: int = 20,
) -> list[dict]:
    """
    Busca clientes/contactos en Odoo.

    Args:
        query: Texto libre para buscar por nombre, email o teléfono
        is_company: True para empresas, False para personas, None para todos
        limit: Máximo de resultados (1-100)
    """
    domain: list = [("customer_rank", ">", 0)]

    if query:
        domain += [
            "|", "|",
            ("name", "ilike", query),
            ("email", "ilike", query),
            ("phone", "ilike", query),
        ]
    if is_company is not None:
        domain.append(("is_company", "=", is_company))

    limit = max(1, min(limit, 100))

    partners = odoo.search_read(
        model="res.partner",
        domain=domain,
        fields=[
            "name", "email", "phone", "mobile", "is_company",
            "street", "city", "country_id", "customer_rank", "supplier_rank",
        ],
        limit=limit,
        order="name asc",
    )

    return [
        {
            "nombre": p["name"],
            "tipo": "Empresa" if p["is_company"] else "Persona",
            "email": p["email"] or "",
            "telefono": p["phone"] or p["mobile"] or "",
            "ciudad": p["city"] or "",
            "pais": p["country_id"][1] if p["country_id"] else "",
            "ranking_cliente": p["customer_rank"],
        }
        for p in partners
    ]


def get_customer_stats(customer_name: str) -> dict:
    """
    Obtiene estadísticas de un cliente específico: pedidos, facturas y deuda.

    Args:
        customer_name: Nombre exacto o parcial del cliente
    """
    partners = odoo.search_read(
        model="res.partner",
        domain=[("name", "ilike", customer_name), ("customer_rank", ">", 0)],
        fields=["id", "name", "email", "credit", "debit"],
        limit=1,
    )

    if not partners:
        return {"error": f"No se encontró cliente con nombre '{customer_name}'"}

    partner = partners[0]
    partner_id = partner["id"]

    num_orders = odoo.search_count(
        "sale.order", [("partner_id", "=", partner_id), ("state", "in", ["draft", "sent", "sale", "done"])]
    )

    invoices = odoo.search_read(
        model="account.move",
        domain=[
            ("partner_id", "=", partner_id),
            ("move_type", "=", "out_invoice"),
            ("state", "!=", "cancel"),
        ],
        fields=["amount_total", "amount_residual", "state"],
        limit=200,
    )

    total_facturado = sum(i["amount_total"] for i in invoices)
    total_pendiente = sum(i["amount_residual"] for i in invoices)

    return {
        "cliente": partner["name"],
        "email": partner["email"] or "",
        "pedidos_confirmados": num_orders,
        "facturas_emitidas": len(invoices),
        "total_facturado": round(total_facturado, 2),
        "deuda_pendiente": round(total_pendiente, 2),
    }


def get_sales_by_country(date_from: str = "", date_to: str = "", seller_id: int = 0) -> list[dict]:
    """Ventas confirmadas agrupadas por país del cliente."""
    from collections import defaultdict

    domain: list = [("state", "in", ["draft", "sent", "sale", "done"])]
    if date_from:
        domain.append(("date_order", ">=", date_from))
    if date_to:
        domain.append(("date_order", "<=", date_to))
    if seller_id:
        domain.append(("user_id", "=", seller_id))

    orders = odoo.search_read(
        model="sale.order",
        domain=domain,
        fields=["partner_id", "amount_total"],
        limit=0,
    )

    partner_ids = list({o["partner_id"][0] for o in orders if o["partner_id"]})
    if not partner_ids:
        return []

    partners = odoo.search_read(
        model="res.partner",
        domain=[("id", "in", partner_ids)],
        fields=["id", "country_id"],
        limit=len(partner_ids),
    )
    country_map = {
        p["id"]: p["country_id"][1] if p["country_id"] else None
        for p in partners
    }

    by_country: dict = defaultdict(lambda: {"total": 0.0, "num_pedidos": 0})
    for o in orders:
        if not o["partner_id"]:
            continue
        pais = country_map.get(o["partner_id"][0])
        if not pais:
            continue
        by_country[pais]["total"]      += o["amount_total"]
        by_country[pais]["num_pedidos"] += 1

    return sorted(
        [{"pais": k, "total_ventas": round(v["total"], 2), "num_pedidos": v["num_pedidos"]}
         for k, v in by_country.items()],
        key=lambda x: x["total_ventas"], reverse=True,
    )


def get_customers_from_country(country_name: str) -> list[dict]:
    """Clientes de un país concreto con su volumen de compra."""
    groups = odoo.read_group(
        model="sale.order",
        domain=[
            ("state", "in", ["draft", "sent", "sale", "done"]),
            ("partner_id.country_id.name", "=", country_name),
        ],
        fields=["partner_id", "amount_total:sum", "id:count"],
        groupby=["partner_id"],
        orderby="amount_total desc",
    )
    return [
        {
            "cliente": g["partner_id"][1] if g["partner_id"] else "",
            "num_pedidos": g["partner_id_count"],
            "total_comprado": round(g["amount_total"], 2),
        }
        for g in groups
    ]


def get_customers_by_country() -> list[dict]:
    """Número de clientes agrupado por país."""
    groups = odoo.read_group(
        model="res.partner",
        domain=[("customer_rank", ">", 0), ("is_company", "=", True)],
        fields=["country_id", "id:count"],
        groupby=["country_id"],
        orderby="id desc",
    )
    return [
        {
            "pais": g["country_id"][1] if g["country_id"] else "Sin país",
            "num_clientes": g["country_id_count"],
        }
        for g in groups
        if g["country_id"]
    ]


def get_top_customers(
    date_from: str = "",
    date_to: str = "",
    limit: int = 10,
    seller_id: int = 0,
) -> list[dict]:
    """
    Devuelve los clientes con mayor volumen de ventas confirmadas.

    Args:
        date_from: Fecha inicio YYYY-MM-DD
        date_to: Fecha fin YYYY-MM-DD
        limit: Número de clientes a devolver
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
            "posicion": i + 1,
            "cliente": g["partner_id"][1] if g["partner_id"] else "Sin cliente",
            "num_pedidos": g["partner_id_count"],
            "total_comprado": round(g["amount_total"], 2),
        }
        for i, g in enumerate(groups[:limit])
    ]
