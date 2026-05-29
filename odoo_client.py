import ssl
import xmlrpc.client
from functools import cached_property
from config import ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_API_KEY


def _make_transport() -> xmlrpc.client.SafeTransport:
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except ImportError:
        # certifi no disponible — usar CAs del sistema si existen
        pass
    return xmlrpc.client.SafeTransport(context=ctx)


class OdooClient:
    def __init__(self):
        self.url = ODOO_URL.rstrip("/")
        self.db = ODOO_DB
        self.username = ODOO_USERNAME
        self.api_key = ODOO_API_KEY
        self._uid: int | None = None
        self._transport = _make_transport()

    @cached_property
    def _common(self):
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", transport=self._transport)

    @cached_property
    def _models(self):
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", transport=self._transport)

    @property
    def uid(self) -> int:
        if self._uid is None:
            self._uid = self._common.authenticate(
                self.db, self.username, self.api_key, {}
            )
            if not self._uid:
                raise ConnectionError(
                    "Autenticación fallida. Verifica URL, DB, usuario y API key."
                )
        return self._uid

    def search_read(
        self,
        model: str,
        domain: list,
        fields: list[str],
        limit: int = 80,
        order: str = "",
    ) -> list[dict]:
        kwargs = {"fields": fields, "limit": limit}
        if order:
            kwargs["order"] = order
        return self._models.execute_kw(
            self.db, self.uid, self.api_key,
            model, "search_read",
            [domain], kwargs,
        )

    def read_group(
        self,
        model: str,
        domain: list,
        fields: list[str],
        groupby: list[str],
        orderby: str = "",
    ) -> list[dict]:
        kwargs: dict = {}
        if orderby:
            kwargs["orderby"] = orderby
        return self._models.execute_kw(
            self.db, self.uid, self.api_key,
            model, "read_group",
            [domain, fields, groupby], kwargs,
        )

    def search_count(self, model: str, domain: list) -> int:
        return self._models.execute_kw(
            self.db, self.uid, self.api_key,
            model, "search_count",
            [domain],
        )


odoo = OdooClient()
