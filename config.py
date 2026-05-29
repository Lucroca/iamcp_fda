import os
from dotenv import load_dotenv

load_dotenv()

ODOO_URL = os.getenv("ODOO_URL", "")
ODOO_DB = os.getenv("ODOO_DB", "")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "")
ODOO_API_KEY = os.getenv("ODOO_API_KEY", "")

if not all([ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_API_KEY]):
    raise EnvironmentError(
        "Faltan variables de entorno. Copia .env.example a .env y complétalo."
    )
