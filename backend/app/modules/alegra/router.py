"""
Super Ozono Global -- Modulo Alegra (Facturacion Electronica)
Endpoints para sincronizar clientes, productos y enviar facturas a Alegra
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import SessionDep, CurrentUser, AdminDep
from app.core.config import get_settings
from app.modules.alegra.client import alegra_get, alegra_post
from app.modules.alegra.mappers import cliente_to_alegra, producto_to_alegra, venta_to_alegra, detalle_to_alegra_item
from app.modules.ventas.models import Cliente, Producto, VentaDocumento, VentaDetalle, EstadoVenta
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/api/v1/alegra", tags=["Alegra - Facturacion Electronica"])
settings = get_settings()
SuperuserDep = AdminDep


def _check_credentials():
    if not settings.ALEGRA_EMAIL or not settings.ALEGRA_TOKEN:
        raise HTTPException(
            400,
            "Credenciales de Alegra no configuradas. Agrega ALEGRA_EMAIL y ALEGRA_TOKEN al archivo .env"
        )


# -- Estado de conexion ----------------------------------------

@router.get("/status")
async def alegra_status(_: CurrentUser):
    """Verifica la conexion con Alegra y devuelve info de la cuenta."""
    _check_credentials()
    try:
        data = await alegra_get("/company")
        return {
            "conectado": True,
            "empresa": data.get("name", ""),
            "nit": data.get("identification", ""),
            "plan": data.get("plan", {}).get("name", ""),
            "email": settings.ALEGRA_EMAIL,
        }
    except Exception as e:
        return {"conectado": False, "error": str(e)}


# -- Impuestos disponibles en Alegra ---------------------------

@router.get("/taxes")
async def get_alegra_taxes(_: CurrentUser):
    """Lista los impuestos configurados en la cuenta de Alegra."""
    _check_credentials()
    try:
        return await alegra_get("/taxes")
    except Exception as e:
        raise HTTPException(502, f"Error al consultar impuestos en Alegra: {e}")


# -- Sincronizar cliente a Alegra ------------------------------

@router.post("/sync/cliente/{cliente_id}")
async def sync_cliente(cliente_id: int, session: SessionDep, _: CurrentUser):
    """Crea o actualiza un cliente en Alegra y guarda su alegra_id en el ERP."""
    _check_credentials()
    cliente = await session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")

    payload = cliente_to_alegra(cliente)

    try:
        if cliente.alegra_id:
            result = await alegra_post(f"/contacts/{cliente.alegra_id}", payload)
        else:
            result = await alegra_post("/contacts", payload)
            cliente.alegra_id = result["id"]
            await session.commit()

        return {"ok": True, "alegra_id": result["id"], "nombre": result.get("name")}
    except Exception as e:
        raise HTTPException(502, f"Error al sincronizar cliente con Alegra: {e}")


# -- Sincronizar producto a Alegra -----------------------------

@router.post("/sync/producto/{producto_id}")
async def sync_producto(producto_id: int, session: SessionDep, _: CurrentUser, iva_tax_id: int = 3):
    """
    Crea o actualiza un producto en Alegra.
    iva_tax_id: ID del impuesto IVA en tu cuenta de Alegra (consulta /alegra/taxes para encontrarlo).
    """
    _check_credentials()
    producto = await session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(404, "Producto no encontrado")

    tax_ids = [iva_tax_id] if float(producto.tarifa_iva) > 0 else []
    payload = producto_to_alegra(producto, tax_ids)

    try:
        if producto.alegra_id:
            result = await alegra_post(f"/items/{producto.alegra_id}", payload)
        else:
            result = await alegra_post("/items", payload)
            producto.alegra_id = result["id"]
            await session.commit()

        return {"ok": True, "alegra_id": result["id"], "nombre": result.get("name")}
    except Exception as e:
        raise HTTPException(502, f"Error al sincronizar producto con Alegra: {e}")


# -- Enviar factura a Alegra -----------------------------------

@router.post("/facturas/{venta_id}")
async def enviar_factura(venta_id: int, session: SessionDep, _: CurrentUser, iva_tax_id: int = 3):
    """
    Envia una venta confirmada a Alegra como factura electronica.
    Requiere que el cliente y todos los productos ya esten sincronizados con Alegra.
    """
    _check_credentials()

    result = await session.execute(
        select(VentaDocumento)
        .options(selectinload(VentaDocumento.detalles).selectinload(VentaDetalle.producto))
        .where(VentaDocumento.id == venta_id)
    )
    venta = result.scalar_one_or_none()

    if not venta:
        raise HTTPException(404, "Venta no encontrada")
    if venta.estado == EstadoVenta.ANULADA:
        raise HTTPException(400, "No se puede facturar una venta anulada")
    if venta.alegra_id:
        raise HTTPException(400, f"Esta venta ya fue enviada a Alegra (ID: {venta.alegra_id})")

    cliente = await session.get(Cliente, venta.cliente_id)
    if not cliente or not cliente.alegra_id:
        raise HTTPException(
            400,
            "El cliente no esta sincronizado con Alegra. Sincronizalo primero desde /alegra/sync/cliente/{id}",
        )

    # Verificar que todos los productos esten sincronizados
    items = []
    for det in venta.detalles:
        if not det.producto or not det.producto.alegra_id:
            raise HTTPException(
                400,
                f"El producto '{det.producto.nombre if det.producto else det.producto_id}'"
                " no esta sincronizado con Alegra"
            )
        tax_ids = [iva_tax_id] if float(det.iva_porcentaje) > 0 else []
        items.append(detalle_to_alegra_item(det, det.producto.alegra_id, tax_ids))

    payload = venta_to_alegra(venta, cliente.alegra_id, items)

    try:
        data = await alegra_post("/invoices", payload)
        venta.alegra_id = data["id"]
        venta.alegra_numero = str(data.get("numberTemplate", {}).get("fullNumber", data["id"]))
        venta.cufe = data.get("stamp", {}).get("cufe", "")
        venta.estado = EstadoVenta.FACTURADA
        await session.commit()

        return {
            "ok": True,
            "alegra_id": data["id"],
            "numero_factura": venta.alegra_numero,
            "cufe": venta.cufe,
            "estado": "Facturada",
        }
    except Exception as e:
        raise HTTPException(502, f"Error al enviar factura a Alegra: {e}")


# -- Ver facturas en Alegra ------------------------------------

@router.get("/facturas")
async def list_facturas_alegra(_: CurrentUser, limit: int = 20, start: int = 0):
    """Lista las facturas registradas directamente en Alegra."""
    _check_credentials()
    try:
        return await alegra_get("/invoices", params={"limit": limit, "start": start})
    except Exception as e:
        raise HTTPException(502, f"Error al consultar facturas en Alegra: {e}")
