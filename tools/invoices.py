from odoo_client import odoo

_TIPOS_FACTURA = ["out_invoice", "out_refund"]


def _signo(move_type: str) -> int:
    """Las rectificativas (out_refund) tienen importe positivo en BD pero son negativos económicamente."""
    return -1 if move_type == "out_refund" else 1


def get_factura_detalle(numero: str) -> dict:
    invoices = odoo.search_read(
        "account.move",
        [["name", "ilike", numero], ["move_type", "in", _TIPOS_FACTURA]],
        ["name", "move_type", "partner_id", "invoice_date", "invoice_date_due",
         "amount_untaxed", "amount_total", "amount_residual",
         "payment_state", "state", "ref"],
        limit=5,
        order="invoice_date desc",
    )
    if not invoices:
        return {"error": f"Factura '{numero}' no encontrada"}

    inv = invoices[0]
    signo = _signo(inv["move_type"])
    lines = odoo.search_read(
        "account.move.line",
        [["move_id", "=", inv["id"]], ["display_type", "=", "product"]],
        ["product_id", "name", "quantity", "price_unit", "discount",
         "price_subtotal", "product_uom_id", "family_id", "variety_ids"],
        limit=10000,
    )

    all_var_ids = list({vid for l in lines for vid in (l.get("variety_ids") or [])})
    var_names: dict = {}
    if all_var_ids:
        varieties = odoo.search_read(
            "alfinf.variety", [["id", "in", all_var_ids]], ["name"], limit=200
        )
        var_names = {v["id"]: v["name"] for v in varieties}

    return {
        "numero": inv["name"],
        "tipo": "Abono/Rectificativa" if inv["move_type"] == "out_refund" else "Factura",
        "cliente": inv["partner_id"][1] if inv["partner_id"] else "",
        "fecha": inv["invoice_date"] or "",
        "vencimiento": inv["invoice_date_due"] or "",
        "estado": inv["state"],
        "estado_pago": inv["payment_state"],
        "ref": inv["ref"] or "",
        "base_imponible": round(inv["amount_untaxed"] * signo, 2),
        "total": round(inv["amount_total"] * signo, 2),
        "pendiente": round(inv["amount_residual"] * signo, 2),
        "lineas": [
            {
                "descripcion": l["name"] or "",
                "producto": l["product_id"][1] if l["product_id"] else "",
                "familia": l["family_id"][1] if l["family_id"] else "",
                "variedades": [var_names[vid] for vid in (l.get("variety_ids") or []) if vid in var_names],
                "cantidad": l["quantity"],
                "unidad": l["product_uom_id"][1] if l["product_uom_id"] else "",
                "precio_unit": l["price_unit"],
                "descuento_pct": l["discount"],
                "subtotal": round(l["price_subtotal"] * signo, 2),
            }
            for l in lines
        ],
    }


def get_invoices(
    state: str = "posted",
    limit: int = 20,
    date_from: str = "",
    date_to: str = "",
    overdue_only: bool = False,
    tipo: str = "all",
) -> list[dict]:
    """
    Lista facturas y abonos de clientes.

    Args:
        state: 'draft', 'posted', 'cancel', 'all'
        tipo: 'all' (facturas + abonos), 'invoice' (solo facturas), 'refund' (solo abonos)
    """
    if tipo == "invoice":
        tipos = ["out_invoice"]
    elif tipo == "refund":
        tipos = ["out_refund"]
    else:
        tipos = _TIPOS_FACTURA

    domain: list = [("move_type", "in", tipos)]
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
            "name", "move_type", "partner_id", "invoice_date", "invoice_date_due",
            "amount_total", "amount_residual", "payment_state", "state", "currency_id",
        ],
        limit=limit,
        order="invoice_date desc",
    )

    return [
        {
            "numero": inv["name"],
            "tipo": "Abono" if inv["move_type"] == "out_refund" else "Factura",
            "cliente": inv["partner_id"][1] if inv["partner_id"] else "",
            "fecha_factura": inv["invoice_date"] or "",
            "fecha_vencimiento": inv["invoice_date_due"] or "",
            "total": round(inv["amount_total"] * _signo(inv["move_type"]), 2),
            "pendiente": round(inv["amount_residual"] * _signo(inv["move_type"]), 2),
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
        ("move_type", "in", _TIPOS_FACTURA),
        ("partner_id", "in", partner_ids),
    ]
    if state != "all":
        domain.append(("state", "=", state))

    limit = max(1, min(limit, 50))

    invoices = odoo.search_read(
        model="account.move",
        domain=domain,
        fields=[
            "name", "move_type", "partner_id", "invoice_date", "invoice_date_due",
            "amount_total", "amount_residual", "payment_state", "state",
        ],
        limit=limit,
        order="invoice_date desc",
    )

    return [
        {
            "numero": inv["name"],
            "tipo": "Abono" if inv["move_type"] == "out_refund" else "Factura",
            "cliente": inv["partner_id"][1] if inv["partner_id"] else "",
            "fecha_factura": inv["invoice_date"] or "",
            "fecha_vencimiento": inv["invoice_date_due"] or "",
            "total": round(inv["amount_total"] * _signo(inv["move_type"]), 2),
            "pendiente": round(inv["amount_residual"] * _signo(inv["move_type"]), 2),
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
    """Resumen de ingresos netos: facturas menos abonos/rectificativas."""
    domain: list = [
        ("move_type", "in", _TIPOS_FACTURA),
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
        fields=["move_type", "amount_total", "amount_residual", "payment_state"],
        limit=0,
    )

    total_facturas = 0.0
    total_abonos = 0.0
    pendiente = 0.0
    num_facturas = 0
    num_abonos = 0
    por_estado: dict = {}

    for inv in invoices:
        signo = _signo(inv["move_type"])
        importe = inv["amount_total"]
        if inv["move_type"] == "out_refund":
            total_abonos += importe
            num_abonos += 1
        else:
            total_facturas += importe
            num_facturas += 1
            estado = inv["payment_state"]
            por_estado[estado] = por_estado.get(estado, 0) + importe
        pendiente += inv["amount_residual"] * signo

    total_neto = total_facturas - total_abonos
    cobrado = total_neto - pendiente

    return {
        "num_facturas": num_facturas,
        "num_abonos": num_abonos,
        "total_facturas_bruto": round(total_facturas, 2),
        "total_abonos": round(total_abonos, 2),
        "total_neto": round(total_neto, 2),
        "total_cobrado": round(cobrado, 2),
        "total_pendiente": round(pendiente, 2),
        "por_estado_pago": {k: round(v, 2) for k, v in por_estado.items()},
    }


def get_overdue_summary() -> list[dict]:
    """Clientes con facturas vencidas ordenados por mayor deuda (solo facturas, no abonos)."""
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
