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

Crear `docker-compose.yml` en `/home/ubuntu/nuevo_cliente/` basándote en `docker-compose.example.yml` del repo:

```yaml
services:
  mcp:
    build:
      context: ./app
      dockerfile: Dockerfile.mcp
    image: nuevo_cliente_mcp:latest
    container_name: nuevo_cliente_mcp
    working_dir: /app
    volumes:
      - ./app:/app          # código en vivo, git pull es suficiente
    environment:
      - MCP_PORT=8082       # cambiar si el puerto está ocupado
    ports:
      - "8082:8082"
    restart: unless-stopped
```

```bash
# Primera vez: construir imagen y arrancar
docker compose up -d --build
```

> **Nota sobre el `.env`:** Las credenciales de Odoo van en `./app/.env`.
> El contenedor monta `./app` como volumen, así que `python-dotenv` las lee
> directamente al arrancar. No van en el `docker-compose.yml`.

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
>
> Si cambia `requirements_remote.txt` hay que añadir `--build` para reconstruir la imagen:
> ```bash
> docker compose up -d --build --force-recreate
> ```

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
├── server_remote.py           # Servidor MCP (SSE) — registra todas las tools
├── config.py                  # Lee variables de entorno
├── odoo_client.py             # Cliente XML-RPC para Odoo (SSL desactivado)
├── Dockerfile                 # Imagen Docker (alternativa, copia código)
├── Dockerfile.mcp             # Imagen Docker usada por el VPS (solo paquetes, código via volumen)
├── docker-compose.example.yml # Plantilla docker-compose para desplegar en VPS
├── requirements_remote.txt    # Dependencias Python
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

## Tools disponibles (42)

> **Parámetros comunes:**
> - `date_from` / `date_to`: formato `YYYY-MM-DD`. Si se omiten, la mayoría de tools usa el año en curso por defecto.
> - `limit`: número de resultados. `0` = todos los datos (sin límite).
> - `familia_nombre`: filtra por nombre de familia de producto (búsqueda parcial, sin distinción may/min).
> - `empresa_nombre`: filtra por empresa contable, p.ej. `"FRESCITRUS"` o `"DOÑANA BUS"` (solo tools de analítica).

---

### Ventas / Albaranes
> Modelo base: `sale.order`. En Frescitrus los importes de `sale.order` son 0 — usar tools de **Analítica** para importes reales.

| Tool | Parámetros | Qué devuelve |
|---|---|---|
| `ventas_listar` | `state` (all/sale/done/draft), `limit`, `date_from`, `date_to` | Lista de albaranes con cliente, fecha, importe y estado |
| `ventas_resumen_por_cliente` | `date_from`, `date_to`, `limit` | Total de ventas agrupado por cliente |
| `ventas_resumen_por_vendedor` | `date_from`, `date_to` | Total de ventas por centro de manipulación |
| `ventas_top_productos` | `limit`, `date_from`, `date_to`, `familia_nombre` | Productos ordenados por importe con familia |
| `ventas_top_productos_cliente` | `customer_name` *, `limit`, `date_from`, `date_to` | Productos vendidos a un cliente concreto |
| `ventas_pedidos_pendientes` | `limit` | Albaranes en estado borrador/pendiente |
| `ventas_kilos_por_producto` | `date_from`, `date_to`, `customer_name`, `familia_nombre`, `limit` | Kg vendidos por producto con precio medio |
| `ventas_precio_por_cliente` | `product_name` *, `date_from`, `date_to` | Precio medio/mín/máx que paga cada cliente por ese producto |
| `albaran_detalle` | `referencia` * | Cabecera + todas las líneas del albarán (productos, variedades, cantidades) |

---

### Clientes
> Modelo base: `res.partner` + `sale.order`.

| Tool | Parámetros | Qué devuelve |
|---|---|---|
| `clientes_top` | `date_from`, `date_to`, `limit` | Clientes ordenados por volumen de compra con país |
| `clientes_estadisticas` | `customer_name` * | Pedidos, facturas emitidas, total facturado y deuda pendiente de un cliente |
| `clientes_por_pais` | — | Número de clientes empresa agrupado por país |
| `clientes_de_pais` | `pais` * | Lista de clientes de un país concreto con su volumen |
| `ventas_por_pais` | `date_from`, `date_to` | Ventas agrupadas por país (basado en sale.order) |

---

### Facturas
> Modelo base: `account.move`. Incluye facturas (`out_invoice`, prefijo DÑ/INV) y abonos/rectificativas (`out_refund`, prefijo RDÑ). Los abonos se devuelven con importe negativo.

| Tool | Parámetros | Qué devuelve |
|---|---|---|
| `facturas_listar` | `state` (posted/draft/cancel/all), `limit`, `date_from`, `date_to`, `tipo` (all/invoice/refund), `overdue_only` | Lista de facturas y abonos con estado de pago |
| `facturas_por_cliente` | `customer_name` *, `limit` | Últimas facturas de un cliente concreto |
| `facturas_resumen_ingresos` | `date_from`, `date_to` | Total bruto, total abonos, **neto real**, cobrado y pendiente |
| `facturas_vencidas_por_cliente` | — | Clientes con deuda vencida ordenados por mayor importe |
| `factura_detalle` | `numero` * | Cabecera + todas las líneas (producto, variedad, cantidad, precio, descuento, subtotal). Funciona con DÑ/... y RDÑ/... |

---

### Compras
> Modelo base: `purchase.order.line`.

| Tool | Parámetros | Qué devuelve |
|---|---|---|
| `compras_precio_por_proveedor` | `product_name` *, `date_from`, `date_to` | Precio de un producto por proveedor (precio medio, mín, máx), ordenado de menor a mayor |

---

### Familias y variedades
> Modelo base: `alfinf.family`.

| Tool | Parámetros | Qué devuelve |
|---|---|---|
| `familias_listar` | — | Todas las familias con sus variedades, código intrastat y tolerancias |

---

### Trazabilidad
> Modelo base: `alfinf.trace` + `alfinf.pallet.out`. Nota: los precios en estas tools son 0 en Frescitrus — usar `analitica_detalle_parcela` para precios reales.

| Tool | Parámetros | Qué devuelve |
|---|---|---|
| `trazabilidad_parcelas` | `agricultor_nombre`, `finca_nombre`, `familia_nombre` | Lista de parcelas con agricultor, finca, variedad, hectáreas y campaña |
| `trazabilidad_kilos_por_parcela` | `date_from`, `date_to`, `agricultor_nombre`, `familia_nombre`, `limit` | Kg e importe vendidos por parcela |
| `trazabilidad_detalle_parcela` | `trazabilidad` * | Detalle completo: agricultor, finca, variedad + todos los pallets y albaranes |

---

### Pallets
> Modelo base: `alfinf.pallet.out` (salida) y `alfinf.pallet.in` (entrada).

| Tool | Parámetros | Qué devuelve |
|---|---|---|
| `pallets_listar` | `limit`, `date_from`, `date_to`, `solo_sin_albaran`, `familia_nombre` | Lista de pallets de salida con columna albaran (vacía si sin asignar) |
| `pallets_sin_albaran` | `limit`, `date_from`, `date_to` | Pallets de salida sin albarán asignado |
| `pallets_con_albaran` | `limit`, `date_from`, `date_to` | Pallets de salida con albarán, mostrando cliente y pedido |
| `pallet_trazabilidad` | `referencia` * | Trazabilidad completa de un pallet: albarán, cliente, agricultor, variedad |
| `pallets_entradas_agricultor` | `date_from`, `date_to`, `limit` | Entradas de pallets agrupadas por agricultor |
| `pallets_stock` | `agricultor_name` | Stock actual de pallets de entrada pendientes de procesar |

---

### Analítica — solo Frescitrus
> Modelo base: `account.analytic.line` (category=invoice). Fuente de verdad para importes y precios reales en Frescitrus. Campos clave: `amount` (€), `unit_amount` (kg), `price_unit` (€/kg).

| Tool | Parámetros | Qué devuelve |
|---|---|---|
| `analitica_por_cliente` | `date_from`, `date_to`, `familia_nombre`, `empresa_nombre`, `limit` | Clientes con importe €, kg y precio medio. Incluye país |
| `analitica_por_finca` | `date_from`, `date_to`, `familia_nombre`, `empresa_nombre`, `limit` | Fincas con importe € y kg |
| `analitica_por_variedad` | `date_from`, `date_to`, `familia_nombre`, `empresa_nombre`, `limit` | Variedades con importe €, kg y precio medio |
| `analitica_por_parcela` | `date_from`, `date_to`, `agricultor_nombre`, `familia_nombre`, `empresa_nombre`, `limit` | Parcelas (trazabilidad) con importe € y kg |
| `analitica_por_agricultor` | `date_from`, `date_to`, `familia_nombre`, `empresa_nombre`, `limit` | Agricultores con importe € y kg vendidos desde sus parcelas |
| `analitica_por_transportista` | `date_from`, `date_to`, `familia_nombre`, `empresa_nombre`, `limit` | Transportistas con importe € y kg transportados |
| `analitica_por_pais` | `date_from`, `date_to`, `familia_nombre`, `empresa_nombre` | País de destino real (campo `destination_country`) con importe €, kg y nº clientes |
| `analitica_detalle_parcela` | `trazabilidad` * | **Detalle completo** de una parcela: todos los movimientos con cliente, albarán, factura, pallet, agricultor, transportista, kg, cajas, precio real, importe, merma, gastos transporte y fechas |
| `analitica_evolucion_mensual` | `date_from`, `date_to`, `familia_nombre`, `empresa_nombre` | Importe €, kg y precio medio agrupados por mes |
| `analitica_variedad_por_cliente` | `variedad_nombre` *, `date_from`, `date_to`, `empresa_nombre` | Para una variedad: qué clientes la compran, kg y precio medio por cliente |
| `rentabilidad_global` | `date_from`, `date_to`, `empresa_nombre` | Ingresos vs costes (liquidación agricultor), margen bruto € y % por familia y global |

---

### Búsqueda universal

| Tool | Parámetros | Qué devuelve |
|---|---|---|
| `buscar` | `referencia` * | Busca en 5 modelos simultáneamente (pallets, trazabilidad, albaranes, facturas, analítica) cualquier código y devuelve todo lo encontrado |

---

> `*` = parámetro obligatorio

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
