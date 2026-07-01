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
    get_albaran_detalle,
)
from tools.customers import get_top_customers, get_customer_stats
from tools.invoices import (
    get_invoices, get_revenue_summary,
    get_overdue_summary, get_invoices_by_customer,
)
from tools.purchases import get_compras_precio_por_proveedor
from tools.families import get_familias_listar
from tools.trazabilidad import (
    get_trazabilidad_parcelas, get_trazabilidad_kilos_por_parcela,
    get_trazabilidad_detalle_parcela,
)
from tools.pallets import (
    get_pallets_listar, get_pallets_sin_albaran, get_pallets_con_albaran,
    get_pallet_trazabilidad, get_pallets_entradas_agricultor,
    get_pallets_stock,
)
from tools.analitica import (
    get_analitica_resumen_por_cliente, get_analitica_resumen_por_finca,
    get_analitica_resumen_por_variedad, get_analitica_resumen_por_parcela,
)

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
    """Resumen de albaranes (ventas) agrupado por centro de manipulación (user_id)."""
    return get_sales_summary_by_seller(date_from=date_from, date_to=date_to)


@mcp.tool()
def ventas_top_productos(limit: int = 15, date_from: str = "", date_to: str = "", familia_nombre: str = "") -> list[dict]:
    """Top productos vendidos globalmente con columna familia. Filtra por familia con familia_nombre. Por defecto año en curso."""
    return get_top_products(limit=limit, date_from=date_from, date_to=date_to, familia_nombre=familia_nombre)


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
def albaran_detalle(referencia: str) -> dict:
    """Devuelve todos los detalles de un albarán (cabecera + líneas): cliente, fecha, centro de manipulación, destino, transportista, productos con variedad y precio."""
    return get_albaran_detalle(referencia=referencia)


@mcp.tool()
def ventas_kilos_por_producto(date_from: str = "", date_to: str = "", customer_name: str = "", familia_nombre: str = "", limit: int = 20) -> list[dict]:
    """Top productos por kg vendidos con precio medio real y columna familia. Filtra por familia con familia_nombre."""
    return get_ventas_kilos_por_producto(date_from=date_from, date_to=date_to, customer_name=customer_name, familia_nombre=familia_nombre, limit=limit)


@mcp.tool()
def ventas_precio_por_cliente(product_name: str, date_from: str = "", date_to: str = "") -> list[dict]:
    """Para un producto concreto, muestra el precio medio, mín y máx que paga cada cliente."""
    return get_ventas_precio_por_cliente(product_name=product_name, date_from=date_from, date_to=date_to)


@mcp.tool()
def compras_precio_por_proveedor(product_name: str, date_from: str = "", date_to: str = "") -> list[dict]:
    """Para un producto concreto, compara el precio de cada proveedor (ordenado de menor a mayor)."""
    return get_compras_precio_por_proveedor(product_name=product_name, date_from=date_from, date_to=date_to)


@mcp.tool()
def trazabilidad_parcelas(agricultor_nombre: str = "", finca_nombre: str = "", familia_nombre: str = "") -> list[dict]:
    """Lista parcelas de trazabilidad con agricultor, finca, variedad, hectáreas y campaña. Filtra por agricultor, finca o familia."""
    return get_trazabilidad_parcelas(agricultor_nombre=agricultor_nombre, finca_nombre=finca_nombre, familia_nombre=familia_nombre)


@mcp.tool()
def trazabilidad_kilos_por_parcela(date_from: str = "", date_to: str = "", agricultor_nombre: str = "", familia_nombre: str = "", limit: int = 30) -> list[dict]:
    """Kilos e importe vendidos agrupados por parcela (trazabilidad). Por defecto año en curso."""
    return get_trazabilidad_kilos_por_parcela(date_from=date_from, date_to=date_to, agricultor_nombre=agricultor_nombre, familia_nombre=familia_nombre, limit=limit)


@mcp.tool()
def trazabilidad_detalle_parcela(trazabilidad: str) -> dict:
    """Detalle completo de una parcela: agricultor, finca, variedad, todos los pallets y albaranes que han salido de ella."""
    return get_trazabilidad_detalle_parcela(trazabilidad=trazabilidad)


@mcp.tool()
def familias_listar() -> list[dict]:
    """Lista todas las familias de producto con sus variedades, código intrastat y tolerancias."""
    return get_familias_listar()


@mcp.tool()
def pallets_listar(limit: int = 50, date_from: str = "", date_to: str = "", solo_sin_albaran: bool = False, familia_nombre: str = "") -> list[dict]:
    """Lista pallets de salida con columna 'albaran' (vacía si no tiene albarán asignado). Por defecto año en curso. Filtra por familia con familia_nombre."""
    return get_pallets_listar(limit=limit, date_from=date_from, date_to=date_to, solo_sin_albaran=solo_sin_albaran, familia_nombre=familia_nombre)


@mcp.tool()
def pallets_sin_albaran(limit: int = 50, date_from: str = "", date_to: str = "") -> list[dict]:
    """Pallets de salida que no están asignados a ningún albarán (pedido de venta)."""
    return get_pallets_sin_albaran(limit=limit, date_from=date_from, date_to=date_to)


@mcp.tool()
def pallets_con_albaran(limit: int = 50, date_from: str = "", date_to: str = "") -> list[dict]:
    """Pallets de salida asignados a un albarán, mostrando a qué cliente y pedido van. Por defecto año en curso."""
    return get_pallets_con_albaran(limit=limit, date_from=date_from, date_to=date_to)


@mcp.tool()
def pallet_trazabilidad(referencia: str) -> dict:
    """Trazabilidad completa de un pallet de salida: cabecera, albarán, cliente y líneas con agricultor, variedad y pallet de entrada."""
    return get_pallet_trazabilidad(referencia=referencia)


@mcp.tool()
def pallets_entradas_agricultor(date_from: str = "", date_to: str = "", limit: int = 30) -> list[dict]:
    """Resumen de entradas de pallets agrupado por agricultor (kg bruto, neto, cajas). Por defecto año en curso."""
    return get_pallets_entradas_agricultor(date_from=date_from, date_to=date_to, limit=limit)


@mcp.tool()
def pallets_stock(agricultor_name: str = "") -> list[dict]:
    """Stock actual de pallets de entrada pendientes de procesar. Filtra opcionalmente por nombre de agricultor."""
    return get_pallets_stock(agricultor_name=agricultor_name)


@mcp.tool()
def analitica_por_cliente(date_from: str = "", date_to: str = "", familia_nombre: str = "", limit: int = 20) -> list[dict]:
    """Ranking de clientes por importe y kg vendidos (cuenta analítica). Por defecto año en curso."""
    return get_analitica_resumen_por_cliente(date_from=date_from, date_to=date_to, familia_nombre=familia_nombre, limit=limit)


@mcp.tool()
def analitica_por_finca(date_from: str = "", date_to: str = "", familia_nombre: str = "", limit: int = 20) -> list[dict]:
    """Ranking de fincas por importe y kg procesados (cuenta analítica). Por defecto año en curso."""
    return get_analitica_resumen_por_finca(date_from=date_from, date_to=date_to, familia_nombre=familia_nombre, limit=limit)


@mcp.tool()
def analitica_por_variedad(date_from: str = "", date_to: str = "", familia_nombre: str = "", limit: int = 20) -> list[dict]:
    """Ranking de variedades por importe y kg con precio medio. Por defecto año en curso."""
    return get_analitica_resumen_por_variedad(date_from=date_from, date_to=date_to, familia_nombre=familia_nombre, limit=limit)


@mcp.tool()
def analitica_por_parcela(date_from: str = "", date_to: str = "", agricultor_nombre: str = "", familia_nombre: str = "", limit: int = 30) -> list[dict]:
    """Importe y kg agrupados por parcela de trazabilidad con agricultor, finca y variedad. Por defecto año en curso."""
    return get_analitica_resumen_por_parcela(date_from=date_from, date_to=date_to, agricultor_nombre=agricultor_nombre, familia_nombre=familia_nombre, limit=limit)


if __name__ == "__main__":
    mcp.run(transport="sse")
