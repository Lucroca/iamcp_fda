# Odoo MCP Server

Servidor MCP (Model Context Protocol) que conecta Claude con Odoo 18 via XML-RPC.
Permite consultar datos de Odoo en lenguaje natural directamente desde Claude Desktop
o cualquier cliente MCP compatible.

## Arquitectura

```
Claude Desktop / Claude.ai
        ↓  SSE (HTTPS)
   Nginx Proxy Manager (VPS)
        ↓
   Docker: server_remote.py  ←→  Odoo 18 (XML-RPC)
```

Cada cliente tiene su propia instancia Docker en el VPS con su propio `.env`.

---

## Requisitos

- Python 3.11+
- Docker + Docker Compose
- VPS con Nginx Proxy Manager (NPM) para SSL
- Acceso a Odoo 18 con API key

---

## Variables de entorno

Crear un fichero `.env` en la raíz del proyecto (nunca subir al repo):

```env
ODOO_URL=https://tu-cliente.alfinfdoo.com
ODOO_DB=nombre_base_datos
ODOO_USERNAME=admin
ODOO_API_KEY=tu_api_key_aqui
MCP_PORT=8080
```

Para obtener la API key en Odoo: **Ajustes → Usuarios → tu usuario → pestaña API Keys**.

---

## Deploy en VPS (nuevo cliente)

### 1. Primera vez

```bash
# Conectar al VPS
ssh ubuntu@164.132.97.91

# Crear carpeta del cliente
mkdir /home/ubuntu/nuevo_cliente
cd /home/ubuntu/nuevo_cliente

# Clonar el repo
git clone https://github.com/Lucroca/iamcp_fda app
cd app

# Crear el .env con los datos del cliente
nano .env
```

Crear `docker-compose.yml` en `/home/ubuntu/nuevo_cliente/`:

```yaml
services:
  mcp:
    build: ./app
    restart: unless-stopped
    env_file: ./app/.env
    ports:
      - "8082:8080"   # cambiar puerto si ya está ocupado
```

```bash
# Arrancar
docker compose up -d
```

### 2. En Nginx Proxy Manager

- Añadir Proxy Host nuevo
- Domain: `inuevocliente.alfinf.com`
- Forward: `localhost:8082`
- Activar SSL con Let's Encrypt

### 3. En Claude Desktop del cliente

Añadir en `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "odoo": {
      "url": "https://inuevocliente.alfinf.com/sse"
    }
  }
}
```

---

## Actualizar un cliente existente (deploy)

```bash
ssh ubuntu@164.132.97.91
cd /home/ubuntu/nombre_cliente/app && git pull
cd ..
docker compose up -d --force-recreate
```

> **Importante:** usar siempre `--force-recreate`, no `restart`. El restart no recarga el `.env`.

---

## Clientes activos

| Cliente | Carpeta VPS | Puerto | URL MCP |
|---|---|---|---|
| Frescitrus | `/home/ubuntu/frescitrus/` | 8081 | `https://ifrescitrus.alfinf.com/sse` |
| Fruta de Andalucía | `/home/ubuntu/iafda/` | 8080 | `https://iafda.alfinf.com/sse` |

---

## Estructura del proyecto

```
mcp_ia/
├── server_remote.py        # Servidor MCP (SSE) — registra todas las tools
├── config.py               # Lee variables de entorno
├── odoo_client.py          # Cliente XML-RPC para Odoo (SSL desactivado)
├── Dockerfile              # Imagen Docker
├── requirements_remote.txt # Dependencias Python
├── tools/
│   ├── analitica.py        # account.analytic.line (Frescitrus)
│   ├── buscar.py           # Búsqueda universal por referencia
│   ├── customers.py        # Clientes y país
│   ├── families.py         # Familias y variedades
│   ├── invoices.py         # Facturas y abonos
│   ├── pallets.py          # Pallets de entrada/salida
│   ├── purchases.py        # Compras por proveedor
│   ├── sales.py            # Albaranes y ventas
│   └── trazabilidad.py     # Parcelas y trazabilidad
└── _archive/               # Código antiguo documentado (no activo)
```

---

## Tools disponibles (~42)

### Ventas / Albaranes
`ventas_listar` · `ventas_resumen_por_cliente` · `ventas_resumen_por_vendedor` · `ventas_top_productos` · `ventas_top_productos_cliente` · `ventas_pedidos_pendientes` · `ventas_kilos_por_producto` · `ventas_precio_por_cliente` · `albaran_detalle`

### Clientes
`clientes_top` · `clientes_estadisticas` · `clientes_por_pais` · `clientes_de_pais`

### Facturas
`facturas_listar` · `facturas_por_cliente` · `facturas_resumen_ingresos` · `facturas_vencidas_por_cliente` · `factura_detalle`

### Compras
`compras_precio_por_proveedor`

### Familias
`familias_listar`

### Trazabilidad
`trazabilidad_parcelas` · `trazabilidad_kilos_por_parcela` · `trazabilidad_detalle_parcela`

### Pallets
`pallets_listar` · `pallets_sin_albaran` · `pallets_con_albaran` · `pallet_trazabilidad` · `pallets_entradas_agricultor` · `pallets_stock`

### Analítica (Frescitrus — account.analytic.line)
`analitica_por_cliente` · `analitica_por_finca` · `analitica_por_variedad` · `analitica_por_parcela` · `analitica_detalle_parcela` · `analitica_evolucion_mensual` · `analitica_variedad_por_cliente` · `analitica_por_pais` · `analitica_por_agricultor` · `analitica_por_transportista` · `rentabilidad_global`

### País
`ventas_por_pais`

### Búsqueda
`buscar`

---

## Añadir una nueva tool

1. Crear la función en el fichero `tools/` correspondiente
2. Registrarla en `server_remote.py` con el decorador `@mcp.tool()`
3. Commit + push
4. Deploy en VPS: `git pull && docker compose up -d --force-recreate`

---

## Notas técnicas

- **SSL:** El cliente XML-RPC tiene `CERT_NONE` para evitar problemas con certificados autofirmados de Odoo
- **`read_group` con fechas:** En este Odoo 18 el módulo `alfinf_base` sobreescribe `read_group` y no soporta `date:month`. La evolución mensual se agrupa en Python via `date[:7]`
- **Precios en albaranes:** En Frescitrus, `sale.order.line` y `pallet.out.line` tienen precios a 0. Los precios reales están en `account.analytic.line` y `account.move.line`
- **Límites:** Las tools de agrupación usan `limit=0` (todos los datos). Las de detalle usan `limit=10000`. Nunca truncar datos parciales
