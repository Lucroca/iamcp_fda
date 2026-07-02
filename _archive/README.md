# Archivo histórico — código no activo

Estos ficheros formaron parte del proyecto en algún momento pero ya no se usan
en el servidor MCP actual. Se conservan aquí por si alguno fuera útil como punto
de partida para un desarrollo futuro.

---

## server.py — Servidor MCP local (stdio)

**Qué era:** Primera versión del servidor MCP. Usaba transporte `stdio` en lugar
de SSE, lo que significa que Claude Desktop lo lanzaba como un proceso local en
el propio ordenador del usuario.

**Por qué se dejó de usar:** El modelo actual usa `server_remote.py` con transporte
SSE, desplegado en el VPS. Así varios usuarios se conectan al mismo servidor sin
instalar nada localmente.

**Cómo reutilizarlo:** Si algún día quieres un modo offline/local (sin VPS),
puedes volver a este servidor. En `claude_desktop_config.json` se configuraría así:
```json
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": ["c:/ruta/al/proyecto/server.py"]
    }
  }
}
```
Necesita `requirements.txt` (también archivado aquí).

---

## dashboard.py — Dashboard visual con Streamlit

**Qué era:** Interfaz web con gráficas (Plotly) y tablas para visualizar datos
de Odoo sin necesidad de IA. Tenía vistas de ventas, clientes y facturas.

**Por qué se dejó de usar:** El enfoque MCP + Claude resultó más flexible y
potente. El dashboard requería Streamlit, Plotly y openpyxl, que son dependencias
pesadas que no necesita el servidor MCP.

**Cómo reutilizarlo:**
```bash
pip install streamlit plotly pandas openpyxl
streamlit run dashboard.py
```
Útil si quieres una vista visual fija sin IA, o como base para una app web propia.
Usa `favicon.ico` y `logo.png` (también archivados) para el branding.

---

## export_excel.py — Exportación a Excel

**Qué era:** Script puntual para exportar resúmenes de ventas por vendedor a
un fichero `.xlsx` con formato profesional (colores, bordes, totales).

**Por qué se dejó de usar:** Era una solución ad-hoc para peticiones puntuales.
Con el MCP, Claude puede describir los datos directamente en el chat.

**Cómo reutilizarlo:**
```bash
pip install openpyxl
python export_excel.py [nombre_vendedor]
```
Sirve como base si en el futuro quieres añadir exportación a Excel desde
la app o desde el propio MCP.

---

## clients.json.example — Configuración multi-cliente

**Qué era:** Ejemplo de configuración para un servidor MCP capaz de servir a
varios clientes Odoo distintos desde la misma instancia. Cada cliente tenía su
token de acceso y sus propias credenciales de Odoo.

**Por qué se dejó de usar:** Se optó por desplegar una instancia separada por
cliente (una para Frescitrus, otra para FDA). Más simple de mantener.

**Cómo reutilizarlo:** Si en el futuro quieres un servidor único multi-tenant,
este fichero muestra la estructura del mapa `token → credenciales`. El servidor
leería el token del header HTTP y cargaría las credenciales correspondientes.

---

## Dockerfile.mcp — (referencia, el activo está en la raíz del proyecto)

**Nota:** `Dockerfile.mcp` fue restaurado a la raíz del proyecto porque el VPS
lo referencia en el `docker-compose.yml`. La copia aquí es solo histórica.

---

## Dockerfile.dashboard — Dockerfile para el dashboard Streamlit

**Qué era:** Dockerfile para desplegar el dashboard Streamlit en el VPS como
contenedor independiente.

**Cómo reutilizarlo:** Si vuelves a activar el dashboard, úsalo junto con
`dashboard.py`. Añade el servicio al `docker-compose.yml` del VPS.

---

## requirements.txt — Dependencias del servidor local (stdio)

**Qué era:** Dependencias mínimas para el servidor stdio (`server.py`).
Sin `uvicorn` ni `starlette` porque no necesitaba SSE.

**Diferencia con `requirements_remote.txt`:**
```
requirements.txt         requirements_remote.txt
────────────────         ───────────────────────
mcp>=1.0.0               mcp>=1.0.0
python-dotenv            python-dotenv
certifi                  certifi
                         uvicorn>=0.30.0   ← para SSE
                         starlette>=0.40.0 ← para SSE
```

---

## favicon.ico / logo.png

Activos visuales usados por `dashboard.py`. Sin uso fuera del dashboard.

---

## *.xlsx — Ficheros de datos exportados

Exportaciones puntuales generadas con `export_excel.py` en mayo 2026.
No son código, son datos históricos de prueba.
