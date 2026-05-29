from mcp.server.fastmcp import FastMCP
from tools.sales import get_sales_orders, get_sales_summary_by_customer, get_sales_summary_by_seller, get_top_products_by_customer
from tools.customers import search_customers, get_customer_stats, get_top_customers
from tools.invoices import get_invoices, get_revenue_summary, get_overdue_summary

mcp = FastMCP("Odoo 18 MCP")

# ── Ventas ────────────────────────────────────────────────────────────────────

@mcp.tool()
def ventas_listar(
    state: str = "all",
    limit: int = 20,
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    """
    Lista pedidos de venta de Odoo 18.

    Args:
        state: Estado del pedido: 'draft', 'sent', 'sale', 'done', 'cancel' o 'all'
        limit: Número máximo de resultados (máx. 100)
        date_from: Filtro fecha inicio (YYYY-MM-DD)
        date_to: Filtro fecha fin (YYYY-MM-DD)
    """
    return get_sales_orders(state=state, limit=limit, date_from=date_from, date_to=date_to)


@mcp.tool()
def ventas_resumen_por_cliente(
    date_from: str = "",
    date_to: str = "",
    limit: int = 20,
) -> list[dict]:
    """
    Resumen de ventas confirmadas agrupado por cliente, ordenado por volumen total.

    Args:
        date_from: Filtro fecha inicio (YYYY-MM-DD)
        date_to: Filtro fecha fin (YYYY-MM-DD)
        limit: Número máximo de clientes a devolver
    """
    return get_sales_summary_by_customer(date_from=date_from, date_to=date_to, limit=limit)


@mcp.tool()
def ventas_top_productos_cliente(
    customer_name: str,
    limit: int = 10,
) -> list[dict]:
    """
    Productos más vendidos a un cliente concreto, ordenados por importe total.

    Args:
        customer_name: Nombre o parte del nombre del cliente
        limit: Número de productos a devolver
    """
    return get_top_products_by_customer(customer_name=customer_name, limit=limit)


@mcp.tool()
def ventas_resumen_por_vendedor(
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    """
    Resumen de ventas confirmadas agrupado por vendedor, ordenado por volumen total.

    Args:
        date_from: Filtro fecha inicio (YYYY-MM-DD)
        date_to: Filtro fecha fin (YYYY-MM-DD)
    """
    return get_sales_summary_by_seller(date_from=date_from, date_to=date_to)


# ── Clientes ──────────────────────────────────────────────────────────────────

@mcp.tool()
def clientes_buscar(
    query: str = "",
    is_company: bool | None = None,
    limit: int = 20,
) -> list[dict]:
    """
    Busca clientes en Odoo por nombre, email o teléfono.

    Args:
        query: Texto libre de búsqueda
        is_company: True para empresas, False para personas físicas, omitir para ambos
        limit: Máximo de resultados
    """
    return search_customers(query=query, is_company=is_company, limit=limit)


@mcp.tool()
def clientes_estadisticas(customer_name: str) -> dict:
    """
    Estadísticas completas de un cliente: pedidos, facturas y deuda pendiente.

    Args:
        customer_name: Nombre o parte del nombre del cliente
    """
    return get_customer_stats(customer_name=customer_name)


@mcp.tool()
def clientes_top(
    date_from: str = "",
    date_to: str = "",
    limit: int = 10,
) -> list[dict]:
    """
    Ranking de clientes por mayor volumen de compra en pedidos confirmados.

    Args:
        date_from: Filtro fecha inicio (YYYY-MM-DD)
        date_to: Filtro fecha fin (YYYY-MM-DD)
        limit: Cuántos clientes mostrar en el ranking
    """
    return get_top_customers(date_from=date_from, date_to=date_to, limit=limit)


# ── Facturación ───────────────────────────────────────────────────────────────

@mcp.tool()
def facturas_listar(
    state: str = "posted",
    limit: int = 20,
    date_from: str = "",
    date_to: str = "",
    overdue_only: bool = False,
) -> list[dict]:
    """
    Lista facturas de clientes de Odoo 18.

    Args:
        state: 'draft', 'posted', 'cancel' o 'all'
        limit: Máximo de resultados
        date_from: Filtro fecha inicio (YYYY-MM-DD)
        date_to: Filtro fecha fin (YYYY-MM-DD)
        overdue_only: Si True, muestra solo facturas vencidas con saldo pendiente
    """
    return get_invoices(
        state=state, limit=limit,
        date_from=date_from, date_to=date_to,
        overdue_only=overdue_only,
    )


@mcp.tool()
def facturas_resumen_ingresos(
    date_from: str = "",
    date_to: str = "",
) -> dict:
    """
    Resumen financiero: total facturado, cobrado y pendiente de cobro.

    Args:
        date_from: Filtro fecha inicio (YYYY-MM-DD)
        date_to: Filtro fecha fin (YYYY-MM-DD)
    """
    return get_revenue_summary(date_from=date_from, date_to=date_to)


@mcp.tool()
def facturas_vencidas_por_cliente() -> list[dict]:
    """
    Lista de clientes con facturas vencidas, ordenados por mayor deuda pendiente.
    No requiere parámetros — siempre usa la fecha de hoy como referencia.
    """
    return get_overdue_summary()


if __name__ == "__main__":
    mcp.run()
