from pydantic import BaseModel, field_serializer
from typing import Optional, List, Literal
from decimal import Decimal
from datetime import datetime, date


class MovimientoResponse(BaseModel):
    id: int
    producto_id: int
    producto_nombre: Optional[str] = None
    producto_sku: Optional[str] = None
    tipo: str
    origen: str
    cantidad: Decimal
    stock_antes: Decimal
    stock_despues: Decimal
    costo_unitario: Optional[Decimal] = None
    compra_id: Optional[int] = None
    venta_id: Optional[int] = None
    motivo: Optional[str] = None
    usuario_id: Optional[int] = None
    fecha: datetime
    created_at: datetime | None = None

    model_config = {"from_attributes": True}

    @field_serializer("stock_antes", "stock_despues")
    def _serialize_stock(self, v: Decimal) -> float:
        """Snapshots de stock como número JSON (no string) para el frontend."""
        return float(v)


class AjusteInventarioInput(BaseModel):
    producto_id: int
    tipo: Literal["Entrada", "Salida"]
    cantidad: Decimal
    motivo: Optional[str] = None
    # Solo para ajuste de Entrada de un producto con controla_lote.
    codigo_lote: Optional[str] = None
    fecha_vencimiento: Optional[date] = None


class TopProductoValor(BaseModel):
    producto: str
    sku: str
    valor: float


class InventarioDashboard(BaseModel):
    valor_total_inventario: Decimal
    productos_stock_bajo: int
    movimientos_mes: int
    top_productos_por_valor: List[TopProductoValor]


class ErrorFilaImport(BaseModel):
    fila: int
    columna: str
    mensaje: str


class PreviewImport(BaseModel):
    total_filas: int
    validas: int
    errores: List[ErrorFilaImport]


class ResumenImport(BaseModel):
    importados: int
