"""
Super Ozono Global — Mapeo de modelos ERP → formato Alegra API
"""

from typing import Any

from app.modules.ventas.models import Cliente, Producto, VentaDocumento


def cliente_to_alegra(c: Cliente) -> dict:
    payload: dict[str, Any] = {
        "name": c.razon_social,
        "identification": c.nit_cc,
        "type": ["client"],
    }
    if c.email:
        payload["email"] = c.email
    if c.telefono or c.celular:
        payload["phonePrimary"] = c.telefono or c.celular
    if c.direccion or c.ciudad:
        payload["address"] = {
            "address": c.direccion or "",
            "city": c.ciudad or "",
            "department": c.departamento or "",
            "country": "CO",
        }
    if c.tipo_persona == "Natural":
        payload["nameObject"] = {"firstName": c.razon_social}
    else:
        payload["nameObject"] = {"tradeName": c.nombre_comercial or c.razon_social}
    return payload


def producto_to_alegra(p: Producto, tax_ids: list[int]) -> dict:
    payload: dict[str, Any] = {
        "name": p.nombre,
        "description": p.descripcion or p.nombre,
        "reference": p.sku,
        "price": [{"idPriceList": 1, "price": float(p.precio_venta)}],
        "type": "product",
        "unit": _unidad_medida(p.unidad_medida),
    }
    if tax_ids:
        payload["tax"] = [{"id": tid} for tid in tax_ids]
    return payload


def venta_to_alegra(v: VentaDocumento, alegra_client_id: int, items: list[dict]) -> dict:
    payload: dict[str, Any] = {
        "date": v.fecha.isoformat(),
        "client": {"id": alegra_client_id},
        "items": items,
    }
    if v.fecha_vencimiento:
        payload["dueDate"] = v.fecha_vencimiento.isoformat()
    if v.observaciones:
        payload["observations"] = v.observaciones
    if v.vendedor:
        payload["seller"] = v.vendedor
    return payload


def detalle_to_alegra_item(detalle, alegra_item_id: int, tax_ids: list[int]) -> dict:
    item = {
        "id": alegra_item_id,
        "description": detalle.producto.nombre if detalle.producto else "",
        "quantity": float(detalle.cantidad),
        "price": float(detalle.precio_unitario),
        "discount": float(detalle.descuento_porcentaje),
    }
    if tax_ids:
        item["tax"] = [{"id": tid} for tid in tax_ids]
    return item


def _unidad_medida(um: str) -> str:
    mapping = {
        "Litro": "unit",
        "Galón": "unit",
        "Kilo": "unit",
        "Unidad": "unit",
        "Caja": "box",
        "Caneca": "unit",
    }
    return mapping.get(um, "unit")
