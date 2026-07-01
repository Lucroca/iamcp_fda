from odoo_client import odoo


def get_invoices(
    state: str = "posted",
    limit: int = 20,
    date_from: str = "",
    date_to: str = "",
    overdue_only: bool = False,
) -> list[dict]:
    """
    Obtiene facturas de clientes.

    Args:
        state: 'draft' (borrador), 'posted' (publicada), 'cancel' (cancelada), 'all'
        limit: Máximo de resultados (1-100)
        date_from: Fecha inicio YYYY-MM-DD
        date_to: Fecha fin YYYY-MM-DD
        overdue_only: Si True, solo facturas vencidas con saldo pendiente
    """
    domain: list = [("move_type", "=", "out_invoice")]
    if state != "all":
        domain.append(("state", "=", state))
    if date_from:
        domain.append(("invoice_date", ">=", date_from))
    if date_to:
        domain.append(("invoice_date", "<=", date_to))
    if overdue_only:
        from datetime import date
        today = date.today().isoformat()
        domain += [
            ("payment_state", "!=", "paid"),
            ("invoice_date_due", "<", today),
            ("state", "=", "posted"),
        ]

    limit = max(1, min(limit, 100))

    invoices = odoo.search_read(
        model="account.move",
        domain=domain,
        fields=[
            "name", "partner_id", "invoice_date", "invoice_date_due",
            "amount_total", "amount_residual", "payment_state", "state",
            "currency_id",
        ],
        limit=limit,
        order="invoice_date desc",
    )

    return [
        {
            "numero": inv["name"],
            "cliente": inv["partner_id"][1] if inv["partner_id"] else "",
            "fecha_factura": inv["invoice_date"] or "",
            "fecha_vencimiento": inv["invoice_date_due"] or "",
            "total": inv["amount_total"],
            "pendiente": inv["amount_residual"],
            "estado_pago": inv["payment_state"],
            "estado": inv["state"],
            "moneda": inv["currency_id"][1] if inv["currency_id"] else "",
        }
        for inv in invoices
    ]


def get_invoices_by_customer(
    customer_name: str,
    limit: int = 5,
    state: str = "posted",
) -> list[dict]:
    """
    Lista las últimas facturas de un cliente concreto.

    Args:
        customer_name: Nombre o parte del nombre del cliente
        limit: Número de facturas a devolver (1-50)
        state: 'posted', 'draft', 'cancel' o 'all'
    """
    partners = odoo.search_read(
        model="res.partner",
        domain=[("name", "ilike", customer_name)],
        fields=["id", "name"],
        limit=10,
    )
    if not partners:
        return [{"error": f"No se encontró ningún cliente con el nombre '{customer_name}'"}]

    partner_ids = [p["id"] for p in partners]

    domain: list = [
        ("move_type", "=", "out_invoice"),
        ("partner_id", "in", partner_ids),
    ]
    if state != "all":
        domain.append(("state", "=", state))

    limit = max(1, min(limit, 50))

    invoices = odoo.search_read(
        model="account.move",
        domain=domain,
        fields=[
            "name", "partner_id", "invoice_date", "invoice_date_due",
            "amount_total", "amount_residual", "payment_state", "state",
        ],
        limit=limit,
        order="invoice_date desc",
    )

    return [
        {
            "numero": inv["name"],
            "cliente": inv["partner_id"][1] if inv["partner_id"] else "",
            "fecha_factura": inv["invoice_date"] or "",
            "fecha_vencimiento": inv["invoice_date_due"] or "",
            "total": inv["amount_total"],
            "pendiente": inv["amount_residual"],
            "estado_pago": inv["payment_state"],
            "estado": inv["state"],
        }
        for inv in invoices
    ]


def get_revenue_summary(
    date_from: str = "",
    date_to: str = "",
    seller_id: int = 0,
) -> dict:
    """
    Resumen de ingresos: total facturado, cobrado y pendiente.

    Args:
        date_from: Fecha inicio YYYY-MM-DD
        date_to: Fecha fin YYYY-MM-DD
    """
    domain: list = [
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
    ]
    if date_from:
        domain.append(("invoice_date", ">=", date_from))
    if date_to:
        domain.append(("invoice_date", "<=", date_to))
    if seller_id:
        domain.append(("invoice_user_id", "=", seller_id))

    invoices = odoo.search_read(
        model="account.move",
        domain=domain,
        fields=["amount_total", "amount_residual", "payment_state"],
        limit=0,
    )

    total = sum(i["amount_total"] for i in invoices)
    pendiente = sum(i["amount_residual"] for i in invoices)
    cobrado = total - pendiente

    por_estado = {}
    for inv in invoices:
        estado = inv["payment_state"]
        por_estado[estado] = por_estado.get(estado, 0) + inv["amount_total"]

    return {
        "num_facturas": len(invoices),
        "total_facturado": round(total, 2),
        "total_cobrado": round(cobrado, 2),
        "total_pendiente": round(pendiente, 2),
        "por_estado_pago": {k: round(v, 2) for k, v in por_estado.items()},
    }


def get_overdue_summary() -> list[dict]:
    """
    Lista clientes con facturas vencidas, ordenados por mayor deuda pendiente.
    """
    from datetime import date
    today = date.today().isoformat()

    domain = [
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
        ("payment_state", "!=", "paid"),
        ("invoice_date_due", "<", today),
    ]

    invoices = odoo.search_read(
        model="account.move",
        domain=domain,
        fields=["partner_id", "amount_residual", "invoice_date_due"],
        limit=10000,
    )

    resumen: dict[str, dict] = {}
    for inv in invoices:
        nombre = inv["partner_id"][1] if inv["partner_id"] else "Sin cliente"
        if nombre not in resumen:
            resumen[nombre] = {"cliente": nombre, "num_facturas": 0, "deuda_total": 0.0}
        resumen[nombre]["num_facturas"] += 1
        resumen[nombre]["deuda_total"] += inv["amount_residual"]

    resultado = sorted(resumen.values(), key=lambda x: x["deuda_total"], reverse=True)
    for r in resultado:
        r["deuda_total"] = round(r["deuda_total"], 2)

    return resultado
