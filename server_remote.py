"""
Servidor MCP remoto — modo HTTP/SSE.
Cada cliente tiene su propio token de acceso y credenciales de Odoo.
Arrancar con: python server_remote.py
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Carga configuración de clientes ───────────────────────────────────────────
CLIENTS_FILE = Path(__file__).parent / "clients.json"

def load_clients() -> dict:
    if CLIENTS_FILE.exists():
        return json.loads(CLIENTS_FILE.read_text())
    return {}

CLIENTS = load_clients()

# ── Servidor MCP con autenticación por token ──────────────────────────────────
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount
import uvicorn

# Middleware de autenticación por Bearer token
class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()

        if token not in CLIENTS:
            return JSONResponse({"error": "Token inválido"}, status_code=401)

        # Inyecta las credenciales del cliente en el contexto de la request
        request.state.client_config = CLIENTS[token]
        return await call_next(request)


def create_mcp_for_client(config: dict) -> FastMCP:
    """Crea una instancia MCP con las credenciales del cliente."""
    import importlib, sys

    # Sobreescribe variables de entorno para este cliente
    os.environ["ODOO_URL"]      = config["odoo_url"]
    os.environ["ODOO_DB"]       = config["odoo_db"]
    os.environ["ODOO_USERNAME"] = config["odoo_username"]
    os.environ["ODOO_API_KEY"]  = config["odoo_api_key"]

    # Recarga los módulos para que lean las nuevas variables
    for mod in ["config", "odoo_client",
                "tools.sales", "tools.customers", "tools.invoices"]:
        if mod in sys.modules:
            importlib.reload(sys.modules[mod])

    from tools.sales import (
        get_sales_orders, get_sales_summary_by_customer,
        get_sales_summary_by_seller, get_top_products,
        get_sales_by_month, get_pending_orders,
        get_top_products_by_customer,
    )
    from tools.customers import (
        get_top_customers, get_customers_by_country,
        get_customer_stats, search_customers,
    )
    from tools.invoices import get_revenue_summary, get_overdue_summary

    mcp = FastMCP(f"Odoo MCP — {config.get('nombre', 'Cliente')}")

    @mcp.tool()
    def ventas_listar(state: str = "all", limit: int = 20,
                      date_from: str = "", date_to: str = "") -> list[dict]:
        """Lista pedidos de venta."""
        return get_sales_orders(state=state, limit=limit,
                                date_from=date_from, date_to=date_to)

    @mcp.tool()
    def ventas_resumen_por_cliente(date_from: str = "",
                                   date_to: str = "", limit: int = 20) -> list[dict]:
        """Resumen de ventas agrupado por cliente."""
        return get_sales_summary_by_customer(date_from=date_from,
                                             date_to=date_to, limit=limit)

    @mcp.tool()
    def ventas_resumen_por_vendedor(date_from: str = "",
                                    date_to: str = "") -> list[dict]:
        """Resumen de ventas agrupado por vendedor."""
        return get_sales_summary_by_seller(date_from=date_from, date_to=date_to)

    @mcp.tool()
    def ventas_top_productos_cliente(customer_name: str,
                                     limit: int = 10) -> list[dict]:
        """Productos más vendidos a un cliente."""
        return get_top_products_by_customer(customer_name=customer_name, limit=limit)

    @mcp.tool()
    def ventas_top_productos(limit: int = 15) -> list[dict]:
        """Top productos vendidos globalmente."""
        return get_top_products(limit=limit)

    @mcp.tool()
    def ventas_pedidos_pendientes(limit: int = 50) -> list[dict]:
        """Presupuestos pendientes de confirmar."""
        return get_pending_orders(limit=limit)

    @mcp.tool()
    def clientes_buscar(query: str = "", limit: int = 20) -> list[dict]:
        """Busca clientes por nombre, email o teléfono."""
        return search_customers(query=query, limit=limit)

    @mcp.tool()
    def clientes_estadisticas(customer_name: str) -> dict:
        """Estadísticas completas de un cliente."""
        return get_customer_stats(customer_name=customer_name)

    @mcp.tool()
    def clientes_top(date_from: str = "", date_to: str = "",
                     limit: int = 10) -> list[dict]:
        """Ranking de clientes por volumen de compra."""
        return get_top_customers(date_from=date_from, date_to=date_to, limit=limit)

    @mcp.tool()
    def facturas_listar(state: str = "posted", limit: int = 20,
                        date_from: str = "", date_to: str = "",
                        overdue_only: bool = False) -> list[dict]:
        """Lista facturas de clientes."""
        from tools.invoices import get_invoices
        return get_invoices(state=state, limit=limit,
                            date_from=date_from, date_to=date_to,
                            overdue_only=overdue_only)

    @mcp.tool()
    def facturas_resumen_ingresos(date_from: str = "",
                                  date_to: str = "") -> dict:
        """Resumen de ingresos: facturado, cobrado y pendiente."""
        return get_revenue_summary(date_from=date_from, date_to=date_to)

    @mcp.tool()
    def facturas_vencidas_por_cliente() -> list[dict]:
        """Clientes con facturas vencidas ordenados por mayor deuda."""
        return get_overdue_summary()

    return mcp


# ── App principal ─────────────────────────────────────────────────────────────
# Crea una app SSE por cliente registrado
routes = []
for token, config in CLIENTS.items():
    nombre = config.get("nombre", token[:8])
    mcp_instance = create_mcp_for_client(config)
    sse_app = mcp_instance.get_sse_server_app()
    routes.append(Mount(f"/{nombre}", app=sse_app))

app = Starlette(routes=routes)
app.add_middleware(TokenAuthMiddleware)

if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", 8080))
    print(f"MCP remoto arrancando en http://0.0.0.0:{port}")
    for token, config in CLIENTS.items():
        nombre = config.get("nombre", token[:8])
        print(f"  Cliente '{nombre}': /{nombre}/sse  (token: {token[:12]}...)")
    uvicorn.run(app, host="0.0.0.0", port=port)
