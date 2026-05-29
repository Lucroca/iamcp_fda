import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP
from tools.sales import (
    get_sales_orders, get_sales_summary_by_customer,
    get_sales_summary_by_seller, get_top_products,
    get_pending_orders, get_top_products_by_customer,
    get_ventas_kilos_por_producto, get_ventas_precio_por_cliente,
)
from tools.customers import get_top_customers, get_customer_stats
from tools.invoices import (
    get_invoices, get_revenue_summary,
    get_overdue_summary, get_invoices_by_customer,
)
from tools.purchases import get_compras_precio_por_proveedor

mcp = FastMCP("Odoo 18 — Fruta de Andalucía",
              host="0.0.0.0",
              port=int(os.getenv("MCP_PORT", 8080)))


@mcp.tool()
def ventas_listar(state: str = "all", limit: int = 20, date_from: str = "", date_to: str = "") -> list[dict]:
    """Lista albaranes (pedidos de venta) de Odoo. Un albarán es un sale.order."""
    return get_sales_orders(state=state, limit=limit, date_from=date_from, date_to=date_to)


@mcp.tool()
def ventas_resumen_por_cliente(date_from: str = "", date_to: str = "", limit: int = 20) -> list[dict]:
    """Resumen de albaranes (ventas) agrupado por cliente."""
    return get_sales_summary_by_customer(date_from=date_from, date_to=date_to, limit=limit)


@mcp.tool()
def ventas_resumen_por_vendedor(date_from: str = "", date_to: str = "") -> list[dict]:
    """Resumen de albaranes (ventas) agrupado por vendedor/centro de producción."""
    return get_sales_summary_by_seller(date_from=date_from, date_to=date_to)


@mcp.tool()
def ventas_top_productos(limit: int = 15, date_from: str = "", date_to: str = "") -> list[dict]:
    """Top productos vendidos globalmente. Por defecto muestra el año en curso."""
    return get_top_products(limit=limit, date_from=date_from, date_to=date_to)


@mcp.tool()
def ventas_top_productos_cliente(customer_name: str, limit: int = 10, date_from: str = "", date_to: str = "") -> list[dict]:
    """Productos más vendidos a un cliente concreto. Por defecto muestra el año en curso."""
    return get_top_products_by_customer(customer_name=customer_name, limit=limit, date_from=date_from, date_to=date_to)


@mcp.tool()
def ventas_pedidos_pendientes(limit: int = 50) -> list[dict]:
    """Albaranes (pedidos de venta) pendientes de confirmar."""
    return get_pending_orders(limit=limit)


@mcp.tool()
def clientes_estadisticas(customer_name: str) -> dict:
    """Estadísticas completas de un cliente."""
    return get_customer_stats(customer_name=customer_name)


@mcp.tool()
def clientes_top(date_from: str = "", date_to: str = "", limit: int = 10) -> list[dict]:
    """Ranking de clientes por volumen de compra."""
    return get_top_customers(date_from=date_from, date_to=date_to, limit=limit)


@mcp.tool()
def facturas_listar(state: str = "posted", limit: int = 20, date_from: str = "", date_to: str = "", overdue_only: bool = False) -> list[dict]:
    """Lista facturas de clientes."""
    return get_invoices(state=state, limit=limit, date_from=date_from, date_to=date_to, overdue_only=overdue_only)


@mcp.tool()
def facturas_por_cliente(customer_name: str, limit: int = 5) -> list[dict]:
    """Lista las últimas facturas de un cliente concreto."""
    return get_invoices_by_customer(customer_name=customer_name, limit=limit)


@mcp.tool()
def facturas_resumen_ingresos(date_from: str = "", date_to: str = "") -> dict:
    """Resumen de ingresos: facturado, cobrado y pendiente."""
    return get_revenue_summary(date_from=date_from, date_to=date_to)


@mcp.tool()
def facturas_vencidas_por_cliente() -> list[dict]:
    """Clientes con facturas vencidas ordenados por mayor deuda."""
    return get_overdue_summary()


@mcp.tool()
def ventas_kilos_por_producto(date_from: str = "", date_to: str = "", customer_name: str = "", limit: int = 20) -> list[dict]:
    """Top productos por kg vendidos con precio medio real (importe/kg)."""
    return get_ventas_kilos_por_producto(date_from=date_from, date_to=date_to, customer_name=customer_name, limit=limit)


@mcp.tool()
def ventas_precio_por_cliente(product_name: str, date_from: str = "", date_to: str = "") -> list[dict]:
    """Para un producto concreto, muestra el precio medio, mín y máx que paga cada cliente."""
    return get_ventas_precio_por_cliente(product_name=product_name, date_from=date_from, date_to=date_to)


@mcp.tool()
def compras_precio_por_proveedor(product_name: str, date_from: str = "", date_to: str = "") -> list[dict]:
    """Para un producto concreto, compara el precio de cada proveedor (ordenado de menor a mayor)."""
    return get_compras_precio_por_proveedor(product_name=product_name, date_from=date_from, date_to=date_to)


if __name__ == "__main__":
    mcp.run(transport="sse")
