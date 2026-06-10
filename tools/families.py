from odoo_client import odoo


def get_familias_listar() -> list[dict]:
    families = odoo.search_read(
        "alfinf.family",
        [],
        ["name", "cod_intrastat", "ggn", "variety_ids", "max_tolerance", "min_tolerance"],
        limit=100,
        order="name asc",
    )
    result = []
    for f in families:
        variety_names = []
        if f.get("variety_ids"):
            varieties = odoo.search_read(
                "alfinf.variety", [["id", "in", f["variety_ids"]]], ["name"], limit=50
            )
            variety_names = sorted(v["name"] for v in varieties)
        result.append({
            "familia": f["name"],
            "cod_intrastat": f["cod_intrastat"] or "",
            "ggn": f["ggn"] or "",
            "tolerancia_min": f["min_tolerance"],
            "tolerancia_max": f["max_tolerance"],
            "variedades": variety_names,
        })
    return result
