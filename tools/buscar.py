from odoo_client import odoo

_BIG = 10000


def get_buscar(referencia: str) -> dict:
    ref = referencia.strip()
    resultado: dict = {"referencia": ref, "encontrado_en": []}

    # 1. Pallet de salida
    pallets = odoo.search_read(
        "alfinf.pallet.out",
        [["name", "ilike", ref]],
        ["name", "partner_id", "sale_order_name", "date",
         "total_kilos", "kg_net", "state", "operating_unit_id"],
        limit=10,
    )
    if pallets:
        resultado["encontrado_en"].append("pallet")
        resultado["pallets"] = [
            {
                "pallet": p["name"],
                "cliente": p["partner_id"][1] if p["partner_id"] else "",
                "albaran": p["sale_order_name"] or "",
                "fecha": p["date"],
                "kg_bruto": p["total_kilos"],
                "kg_neto": p["kg_net"],
                "estado": p["state"] or "",
                "centro": p["operating_unit_id"][1] if p["operating_unit_id"] else "",
            }
            for p in pallets
        ]

    # 2. Trazabilidad (alfinf.trace)
    traces = odoo.search_read(
        "alfinf.trace",
        [["name", "ilike", ref]],
        ["name", "partner_id", "farm_id", "plot_id",
         "family_id", "variety_id", "hectares", "eco"],
        limit=10,
    )
    if traces:
        resultado["encontrado_en"].append("trazabilidad")
        resultado["trazabilidad"] = [
            {
                "codigo": t["name"],
                "agricultor": t["partner_id"][1] if t["partner_id"] else "",
                "finca": t["farm_id"][1] if t["farm_id"] else "",
                "parcela": t["plot_id"][1] if t["plot_id"] else "",
                "familia": t["family_id"][1] if t["family_id"] else "",
                "variedad": t["variety_id"][1] if t["variety_id"] else "",
                "hectareas": t["hectares"],
                "eco": t["eco"],
            }
            for t in traces
        ]

    # 3. Albarán (sale.order)
    orders = odoo.search_read(
        "sale.order",
        [["name", "ilike", ref]],
        ["name", "partner_id", "date_order", "amount_untaxed",
         "amount_total", "state", "user_id"],
        limit=10,
    )
    if orders:
        resultado["encontrado_en"].append("albaran")
        resultado["albaranes"] = [
            {
                "referencia": o["name"],
                "cliente": o["partner_id"][1] if o["partner_id"] else "",
                "fecha": o["date_order"],
                "base_imponible": o["amount_untaxed"],
                "total": o["amount_total"],
                "estado": o["state"],
                "centro": o["user_id"][1] if o["user_id"] else "",
            }
            for o in orders
        ]

    # 4. Factura (account.move)
    invoices = odoo.search_read(
        "account.move",
        [["name", "ilike", ref], ["move_type", "=", "out_invoice"]],
        ["name", "partner_id", "invoice_date", "invoice_date_due",
         "amount_untaxed", "amount_total", "amount_residual",
         "payment_state", "state"],
        limit=10,
    )
    if invoices:
        resultado["encontrado_en"].append("factura")
        resultado["facturas"] = [
            {
                "numero": i["name"],
                "cliente": i["partner_id"][1] if i["partner_id"] else "",
                "fecha": i["invoice_date"] or "",
                "vencimiento": i["invoice_date_due"] or "",
                "base_imponible": i["amount_untaxed"],
                "total": i["amount_total"],
                "pendiente": i["amount_residual"],
                "estado_pago": i["payment_state"],
                "estado": i["state"],
            }
            for i in invoices
        ]

    # 5. Líneas analíticas — busca por pallet_number o invoice_number
    alines = odoo.search_read(
        "account.analytic.line",
        ["|", ["pallet_number", "ilike", ref], ["invoice_number", "ilike", ref],
         ["category", "=", "invoice"]],
        ["pallet_number", "invoice_number", "date", "partner_id",
         "trace_id", "variety_id", "farm_id",
         "amount", "unit_amount", "price_unit", "sale_order_id"],
        limit=_BIG,
        order="date asc",
    )
    if alines:
        resultado["encontrado_en"].append("movimientos_analiticos")
        total_eur = sum(l["amount"] or 0 for l in alines)
        total_kg = sum(l["unit_amount"] or 0 for l in alines)
        resultado["movimientos_analiticos"] = {
            "total_eur": round(total_eur, 2),
            "total_kg": round(total_kg, 2),
            "precio_medio_kg": round(total_eur / total_kg, 4) if total_kg else 0,
            "num_lineas": len(alines),
            "lineas": [
                {
                    "fecha": l["date"],
                    "pallet": l["pallet_number"] or "",
                    "factura": l["invoice_number"] or "",
                    "albaran": l["sale_order_id"][1] if l["sale_order_id"] else "",
                    "cliente": l["partner_id"][1] if l["partner_id"] else "",
                    "trazabilidad": l["trace_id"][1] if l["trace_id"] else "",
                    "variedad": l["variety_id"][1] if l["variety_id"] else "",
                    "finca": l["farm_id"][1] if l["farm_id"] else "",
                    "kg": l["unit_amount"],
                    "precio_kg": l["price_unit"],
                    "importe_eur": round(l["amount"], 2),
                }
                for l in alines
            ],
        }

    if not resultado["encontrado_en"]:
        resultado["error"] = f"No se encontró ningún registro con referencia '{ref}'"

    return resultado
