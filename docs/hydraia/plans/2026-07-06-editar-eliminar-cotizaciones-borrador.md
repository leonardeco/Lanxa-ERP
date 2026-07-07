# Plan — Editar y eliminar cotizaciones en Borrador (#25)

- **Goal:** permitir editar y eliminar cotizaciones **solo en estado `Borrador`**.
- **Architecture:** dos endpoints REST nuevos (`PUT`/`DELETE`) en el módulo `ventas`, con guard
  `409` de estado y auditoría; el front reutiliza el modal de creación en modo edición y añade
  botones ✏️/🗑️ visibles solo en Borrador. Sin migraciones ni efectos en ventas/inventario/contab.
- **Tech Stack:** FastAPI + SQLAlchemy 2.0 async (backend, Python 3.13), React 19 + TS + Vite
  (frontend), pytest + Vitest.
- **Spec:** `docs/hydraia/specs/2026-07-06-editar-eliminar-cotizaciones-borrador-design.md`

## Global Constraints (copiados del spec)

- Estado editable/eliminable: **SOLO `Borrador`**; cualquier otro → `409`.
- Validar cliente (`404`) y cada producto (`404`), como en `create_cotizacion`.
- `fecha_vencimiento = fecha + vigencia_dias`; totales `round(x, 2)`; dinero en `Decimal`.
- Auditoría: `entidad="Cotizacion"`; editar → `"Actualizar"`; eliminar → `"Eliminar"`.
- No tocar ventas, inventario, cartera ni contabilidad. Sin migraciones.
- CI verde: pytest + Vitest + ruff/flake8 + tsc + eslint.

## File Structure map

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `backend/app/modules/ventas/router.py` | Modify | Extraer helper de detalles+totales; añadir `PUT` y `DELETE` de cotización |
| `backend/tests/test_cotizaciones.py` | Modify | Tests de editar/eliminar (200/204/409/404 + auditoría) |
| `frontend/src/services/ventasApi.ts` | Modify | `updateCotizacion`, `deleteCotizacion` |
| `frontend/src/views/VentasView.tsx` | Modify | Modal en modo edición + botones ✏️/🗑️ + handler eliminar |
| `frontend/src/views/CotizacionesEdit.test.tsx` | Create | Test del modal en modo edición (prefill + PUT) |
| `PENDIENTES.md`, `DOCUMENTACION.md`, `BITACORA.md` | Modify | Cierre según convención del repo |

---

## Task 1 — Backend: helper compartido + endpoints PUT y DELETE

**Files:**
- Modify: `backend/app/modules/ventas/router.py`

**Interfaces:**
- Consumes: `_calcular_detalle(det)`, `_get_cotizacion_or_404(db, id)`, `_build_cotizacion_response(cot)`,
  `registrar_auditoria(db, usuario, accion, entidad, entidad_id, descripcion, cambios=None)`,
  models `Cotizacion`, `CotizacionDetalle`, `EstadoCotizacion`, `Cliente`, `Producto`.
- Produces: `_aplicar_detalles_y_totales(db, cot, data)`, endpoints
  `PUT /cotizaciones/{id}` y `DELETE /cotizaciones/{id}`.

**Precondiciones de entorno:** working dir `backend/`; venv activo; comando de test
`python -m pytest tests/test_cotizaciones.py -q` (desde `backend/`).

### Paso 1.1 — Extraer el helper `_aplicar_detalles_y_totales`

En `create_cotizacion`, el bloque de cálculo hoy es (anclar por este texto exacto y **reemplazarlo**):

`old_string`:
```python
    db.add(cot)
    await db.flush()

    subtotal_total = Decimal("0.00")
    descuento_total = Decimal("0.00")
    iva_total = Decimal("0.00")
    for det_data in data.detalles:
        producto = await db.get(Producto, det_data.producto_id)
        if not producto:
            raise HTTPException(
                status_code=404, detail=f"Producto ID {det_data.producto_id} no encontrado")

        calc = _calcular_detalle(det_data)
        db.add(CotizacionDetalle(
            cotizacion_id=cot.id,
            producto_id=det_data.producto_id,
            cantidad=det_data.cantidad,
            precio_unitario=det_data.precio_unitario,
            descuento_porcentaje=det_data.descuento_porcentaje,
            subtotal_linea=calc["subtotal_linea"],
            iva_porcentaje=det_data.iva_porcentaje,
            iva_valor=calc["iva_valor"],
            total_linea=calc["total_linea"],
            notas=det_data.notas,
        ))
        linea_bruta = det_data.cantidad * det_data.precio_unitario
        subtotal_total += linea_bruta
        descuento_total += linea_bruta * (det_data.descuento_porcentaje / Decimal("100"))
        iva_total += calc["iva_valor"]

    base_gravable = subtotal_total - descuento_total
    cot.subtotal = round(subtotal_total, 2)
    cot.descuento_total = round(descuento_total, 2)
    cot.base_gravable = round(base_gravable, 2)
    cot.iva_total = round(iva_total, 2)
    cot.total = round(base_gravable + iva_total, 2)

    await db.flush()
    return _build_cotizacion_response(await _get_cotizacion_or_404(db, cot.id))
```

`new_string`:
```python
    db.add(cot)
    await db.flush()

    await _aplicar_detalles_y_totales(db, cot, data)

    await db.flush()
    return _build_cotizacion_response(await _get_cotizacion_or_404(db, cot.id))
```

### Paso 1.2 — Añadir el helper y los dos endpoints

Anclar en la línea final del `enviar/aprobar/rechazar/convertir` bloque: insertar el helper
**justo antes** de `def _build_cotizacion_response(` (línea ~439). Es decir, `old_string` es el
inicio de esa función y el `new_string` antepone el helper. Anclar por texto único:

`old_string`:
```python
def _build_cotizacion_response(cot: Cotizacion) -> CotizacionResponse:
    """Requiere cliente, venta y detalles (con .producto) precargados."""
```

`new_string`:
```python
async def _aplicar_detalles_y_totales(db: AsyncSession, cot: Cotizacion, data) -> None:
    """Crea los detalles de la cotización (validando cada producto) y recalcula
    sus totales. `cot` ya debe estar en la sesión con su id (flush hecho). Al
    editar, los detalles previos deben haberse borrado antes de llamar aquí."""
    subtotal_total = Decimal("0.00")
    descuento_total = Decimal("0.00")
    iva_total = Decimal("0.00")
    for det_data in data.detalles:
        producto = await db.get(Producto, det_data.producto_id)
        if not producto:
            raise HTTPException(
                status_code=404, detail=f"Producto ID {det_data.producto_id} no encontrado")

        calc = _calcular_detalle(det_data)
        db.add(CotizacionDetalle(
            cotizacion_id=cot.id,
            producto_id=det_data.producto_id,
            cantidad=det_data.cantidad,
            precio_unitario=det_data.precio_unitario,
            descuento_porcentaje=det_data.descuento_porcentaje,
            subtotal_linea=calc["subtotal_linea"],
            iva_porcentaje=det_data.iva_porcentaje,
            iva_valor=calc["iva_valor"],
            total_linea=calc["total_linea"],
            notas=det_data.notas,
        ))
        linea_bruta = det_data.cantidad * det_data.precio_unitario
        subtotal_total += linea_bruta
        descuento_total += linea_bruta * (det_data.descuento_porcentaje / Decimal("100"))
        iva_total += calc["iva_valor"]

    base_gravable = subtotal_total - descuento_total
    cot.subtotal = round(subtotal_total, 2)
    cot.descuento_total = round(descuento_total, 2)
    cot.base_gravable = round(base_gravable, 2)
    cot.iva_total = round(iva_total, 2)
    cot.total = round(base_gravable + iva_total, 2)


def _build_cotizacion_response(cot: Cotizacion) -> CotizacionResponse:
    """Requiere cliente, venta y detalles (con .producto) precargados."""
```

Luego, insertar los dos endpoints **después** del final de `create_cotizacion` (anclar por el
inicio de `enviar_cotizacion`, que va justo después):

`old_string`:
```python
@router.post("/cotizaciones/{cotizacion_id}/enviar", response_model=CotizacionResponse)
async def enviar_cotizacion(cotizacion_id: int, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Marcar la cotización como Enviada al cliente."""
```

`new_string`:
```python
@router.put("/cotizaciones/{cotizacion_id}", response_model=CotizacionResponse)
async def update_cotizacion(
    cotizacion_id: int, data: CotizacionCreate, current: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Editar una cotización en Borrador: reemplaza cabecera y detalles y
    recalcula totales. Solo Borrador (409 en cualquier otro estado)."""
    cot = await _get_cotizacion_or_404(db, cotizacion_id)
    if cot.estado != EstadoCotizacion.BORRADOR:
        raise HTTPException(
            status_code=409, detail="Solo se pueden editar cotizaciones en Borrador")

    cliente = await db.get(Cliente, data.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    cot.fecha = data.fecha
    cot.vigencia_dias = data.vigencia_dias
    cot.fecha_vencimiento = data.fecha + timedelta(days=data.vigencia_dias)
    cot.cliente_id = data.cliente_id
    cot.vendedor = data.vendedor
    cot.observaciones = data.observaciones

    # Reemplazar los detalles: borrar los viejos explícitamente, luego recrear.
    for det in list(cot.detalles):
        await db.delete(det)
    await db.flush()

    await _aplicar_detalles_y_totales(db, cot, data)

    registrar_auditoria(
        db, current, "Actualizar", "Cotizacion", cot.id,
        f"Editó la cotización {cot.numero} (total {cot.total})",
    )
    await db.flush()
    db.expire(cot, ["detalles"])
    return _build_cotizacion_response(await _get_cotizacion_or_404(db, cot.id))


@router.delete("/cotizaciones/{cotizacion_id}", status_code=204)
async def delete_cotizacion(
    cotizacion_id: int, current: CurrentUser, db: AsyncSession = Depends(get_db),
):
    """Eliminar una cotización en Borrador (borrado real; cascade borra los
    detalles). Deja rastro en auditoría. Solo Borrador (409 en otro estado)."""
    cot = await _get_cotizacion_or_404(db, cotizacion_id)
    if cot.estado != EstadoCotizacion.BORRADOR:
        raise HTTPException(
            status_code=409, detail="Solo se pueden eliminar cotizaciones en Borrador")

    registrar_auditoria(
        db, current, "Eliminar", "Cotizacion", cot.id,
        f"Eliminó la cotización {cot.numero} "
        f"(cliente {cot.cliente_id}, total {cot.total})",
    )
    await db.delete(cot)
    await db.flush()


@router.post("/cotizaciones/{cotizacion_id}/enviar", response_model=CotizacionResponse)
async def enviar_cotizacion(cotizacion_id: int, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Marcar la cotización como Enviada al cliente."""
```

**Nota de imports (verificar, NO re-importar si ya están):** `registrar_auditoria`, `timedelta`,
`HTTPException`, `Cliente`, `Producto`, `CotizacionDetalle`, `EstadoCotizacion`, `AsyncSession`,
`Depends`, `get_db`, `CurrentUser`, `CotizacionCreate` ya se usan en este archivo (el `create`
los usa). Confirmar con:
`grep -n "registrar_auditoria\|from datetime import\|CotizacionCreate" backend/app/modules/ventas/router.py`
→ deben aparecer. Si `registrar_auditoria` NO estuviera importado, añadir
`from app.modules.auditoria.service import registrar_auditoria`.

**Verificación del Task 1 (sin tests aún — estructural):**
```
cd backend && python -c "import ast; ast.parse(open('app/modules/ventas/router.py').read()); print('OK sintaxis')"
grep -c "async def update_cotizacion\|async def delete_cotizacion\|async def _aplicar_detalles_y_totales" app/modules/ventas/router.py
```
→ `OK sintaxis` y el `grep -c` = `3`.

---

## Task 2 — Backend: tests de editar/eliminar

**Files:**
- Modify: `backend/tests/test_cotizaciones.py`

**Interfaces:** consume los helpers ya existentes en ese archivo (`_cliente_y_producto`,
`_crear_cotizacion`) y los fixtures `client: AsyncClient`, `auth_headers: dict` (el usuario es
Admin, así que puede consultar `/api/v1/auditoria`).

**Entorno:** working dir `backend/`; comando `python -m pytest tests/test_cotizaciones.py -q`.

Insertar estos tests **al final** del archivo `backend/tests/test_cotizaciones.py` (anclar por el
final del archivo; añadir tras la última línea). Contenido literal:

```python


@pytest.mark.asyncio
async def test_editar_cotizacion_borrador_recalcula_totales(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    cot = await _crear_cotizacion(client, auth_headers, cli, prod)  # 5 uds, 10% desc

    # Editar: subir a 10 unidades, sin descuento, y cambiar el vendedor.
    resp = await client.put(
        f"/api/v1/ventas/cotizaciones/{cot['id']}",
        json={"fecha": date.today().isoformat(), "vigencia_dias": 30,
              "cliente_id": cli["id"], "vendedor": "Editado",
              "detalles": [{"producto_id": prod["id"], "cantidad": "10",
                            "precio_unitario": "20000.00", "descuento_porcentaje": "0"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    editada = resp.json()
    assert editada["numero"] == cot["numero"]         # el número se conserva
    assert editada["estado"] == "Borrador"
    assert editada["vendedor"] == "Editado"
    # 10 × 20.000 = 200.000; sin desc; IVA 19% = 38.000; total 238.000
    assert float(editada["subtotal"]) == 200000.0
    assert float(editada["descuento_total"]) == 0.0
    assert float(editada["iva_total"]) == 38000.0
    assert float(editada["total"]) == 238000.0
    assert len(editada["detalles"]) == 1
    assert float(editada["detalles"][0]["cantidad"]) == 10.0
    # Vigencia recalculada a 30 días
    assert editada["fecha_vencimiento"] == (date.today() + timedelta(days=30)).isoformat()


@pytest.mark.asyncio
async def test_editar_cotizacion_no_borrador_da_409(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    cot = await _crear_cotizacion(client, auth_headers, cli, prod)
    # Enviar → ya no es Borrador
    await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/enviar", headers=auth_headers)

    resp = await client.put(
        f"/api/v1/ventas/cotizaciones/{cot['id']}",
        json={"fecha": date.today().isoformat(), "vigencia_dias": 15,
              "cliente_id": cli["id"],
              "detalles": [{"producto_id": prod["id"], "cantidad": "1",
                            "precio_unitario": "20000.00", "descuento_porcentaje": "0"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_editar_cotizacion_inexistente_da_404(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    resp = await client.put(
        "/api/v1/ventas/cotizaciones/999999",
        json={"fecha": date.today().isoformat(), "vigencia_dias": 15,
              "cliente_id": cli["id"],
              "detalles": [{"producto_id": prod["id"], "cantidad": "1",
                            "precio_unitario": "20000.00", "descuento_porcentaje": "0"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_eliminar_cotizacion_borrador_deja_auditoria(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    cot = await _crear_cotizacion(client, auth_headers, cli, prod)

    resp = await client.delete(f"/api/v1/ventas/cotizaciones/{cot['id']}", headers=auth_headers)
    assert resp.status_code == 204, resp.text

    # Ya no existe
    resp = await client.get(f"/api/v1/ventas/cotizaciones/{cot['id']}", headers=auth_headers)
    assert resp.status_code == 404

    # Quedó registro de auditoría "Eliminar/Cotizacion"
    resp = await client.get(
        "/api/v1/auditoria", params={"entidad": "Cotizacion", "accion": "Eliminar"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    registros = resp.json()
    assert any(r["entidad_id"] == cot["id"] for r in registros)


@pytest.mark.asyncio
async def test_eliminar_cotizacion_no_borrador_da_409(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    cot = await _crear_cotizacion(client, auth_headers, cli, prod)
    await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/enviar", headers=auth_headers)

    resp = await client.delete(f"/api/v1/ventas/cotizaciones/{cot['id']}", headers=auth_headers)
    assert resp.status_code == 409, resp.text
    # Sigue existiendo
    resp = await client.get(f"/api/v1/ventas/cotizaciones/{cot['id']}", headers=auth_headers)
    assert resp.status_code == 200
```

**Verificación del Task 2:**
```
cd backend && python -m pytest tests/test_cotizaciones.py -q
```
→ todos verdes (los ~4 previos + 5 nuevos). Esperado: `9 passed` (o más si ya había otros).

---

## Task 3 — Frontend: cliente API (updateCotizacion, deleteCotizacion)

**Files:**
- Modify: `frontend/src/services/ventasApi.ts`

**Interfaces:** Produces `ventasApi.updateCotizacion(id, data)`, `ventasApi.deleteCotizacion(id)`.
Consume `CotizacionInput`, `Cotizacion` (ya definidos en el archivo), `api` (axios), `BASE`.

Anclar por la línea de `convertirCotizacion` y añadir las dos funciones antes del cierre del
objeto. `old_string`:
```typescript
  convertirCotizacion: (id: number) => api.post<Cotizacion>(`${BASE}/cotizaciones/${id}/convertir`),
};
```
`new_string`:
```typescript
  convertirCotizacion: (id: number) => api.post<Cotizacion>(`${BASE}/cotizaciones/${id}/convertir`),
  updateCotizacion: (id: number, data: CotizacionInput) =>
    api.put<Cotizacion>(`${BASE}/cotizaciones/${id}`, data),
  deleteCotizacion: (id: number) => api.delete<void>(`${BASE}/cotizaciones/${id}`),
};
```

**Verificación del Task 3:**
```
cd frontend && grep -c "updateCotizacion\|deleteCotizacion" src/services/ventasApi.ts
```
→ `2` (una definición de cada una).

---

## Task 4 — Frontend: modal en modo edición + botones en la fila

**Files:**
- Modify: `frontend/src/views/VentasView.tsx`

**Interfaces:** consume `ventasApi.updateCotizacion/deleteCotizacion` (Task 3), tipos `Cotizacion`,
`VentaDetalleInput` (ya importados), componentes `Modal`, `NuevaCotizacionModal`.

**Entorno:** working dir `frontend/`; `npx tsc --noEmit` y `npx eslint src/views/VentasView.tsx`.

### Paso 4.1 — Firma del modal + precarga desde `cotizacion`

`old_string`:
```typescript
function NuevaCotizacionModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [clienteId, setClienteId] = useState('');
  const [fecha, setFecha] = useState(new Date().toISOString().split('T')[0]);
  const [vigenciaDias, setVigenciaDias] = useState('15');
  const [vendedor, setVendedor] = useState('');
  const [observaciones, setObservaciones] = useState('');
  const [lineas, setLineas] = useState<VentaDetalleInput[]>([]);
```
`new_string`:
```typescript
function NuevaCotizacionModal(
  { onClose, onCreated, cotizacion }:
  { onClose: () => void; onCreated: () => void; cotizacion?: Cotizacion },
) {
  const editMode = !!cotizacion;
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [clienteId, setClienteId] = useState(cotizacion ? String(cotizacion.cliente_id) : '');
  const [fecha, setFecha] = useState(cotizacion ? cotizacion.fecha : new Date().toISOString().split('T')[0]);
  const [vigenciaDias, setVigenciaDias] = useState(cotizacion ? String(cotizacion.vigencia_dias) : '15');
  const [vendedor, setVendedor] = useState(cotizacion?.vendedor ?? '');
  const [observaciones, setObservaciones] = useState(cotizacion?.observaciones ?? '');
  const [lineas, setLineas] = useState<VentaDetalleInput[]>(
    cotizacion
      ? cotizacion.detalles.map(d => ({
          producto_id: d.producto_id,
          cantidad: Number(d.cantidad),
          precio_unitario: Number(d.precio_unitario),
          descuento_porcentaje: Number(d.descuento_porcentaje),
          iva_porcentaje: Number(d.iva_porcentaje),
          notas: d.notas,
        }))
      : [],
  );
```

### Paso 4.2 — Rama create/update en el submit + mensaje de error

`old_string`:
```typescript
    setSaving(true);
    setError('');
    try {
      await ventasApi.createCotizacion({
        fecha,
        vigencia_dias: parseInt(vigenciaDias) || 15,
        cliente_id: parseInt(clienteId),
        vendedor: vendedor || undefined,
        observaciones: observaciones || undefined,
        detalles: lineas,
      });
      onCreated();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al crear la cotización');
    } finally {
      setSaving(false);
    }
```
`new_string`:
```typescript
    setSaving(true);
    setError('');
    const payload = {
      fecha,
      vigencia_dias: parseInt(vigenciaDias) || 15,
      cliente_id: parseInt(clienteId),
      vendedor: vendedor || undefined,
      observaciones: observaciones || undefined,
      detalles: lineas,
    };
    try {
      if (editMode) {
        await ventasApi.updateCotizacion(cotizacion!.id, payload);
      } else {
        await ventasApi.createCotizacion(payload);
      }
      onCreated();
    } catch (err: any) {
      setError(err.response?.data?.detail
        || (editMode ? 'Error al actualizar la cotización' : 'Error al crear la cotización'));
    } finally {
      setSaving(false);
    }
```

### Paso 4.3 — Título del modal según el modo

`old_string`:
```typescript
    <Modal title="📋 Nueva Cotización" onClose={onClose} wide confirmDiscard={dirty}>
```
`new_string`:
```typescript
    <Modal title={editMode ? '✏️ Editar Cotización' : '📋 Nueva Cotización'} onClose={onClose} wide confirmDiscard={dirty}>
```

### Paso 4.4 — Estado de edición + handler eliminar en `CotizacionesTab`

Anclar por la declaración de estado del tab (línea ~767). `old_string`:
```typescript
  const [showNueva, setShowNueva] = useState(false);
```
⚠️ **Este texto aparece 2 veces** (CotizacionesTab y VentasTab). Usar un anclaje único: reemplazar
la línea que está **inmediatamente seguida** por la de cotizaciones. Anclar así — `old_string`:
```typescript
function CotizacionesTab() {
  const [cotizaciones, setCotizaciones] = useState<Cotizacion[]>([]);
```
`new_string`:
```typescript
function CotizacionesTab() {
  const [cotizaciones, setCotizaciones] = useState<Cotizacion[]>([]);
  const [editando, setEditando] = useState<Cotizacion | null>(null);
```

Añadir el handler eliminar junto a los otros handlers. `old_string`:
```typescript
  const handleConvertir = async (c: Cotizacion) => {
```
`new_string`:
```typescript
  const handleEliminar = (c: Cotizacion) => {
    if (!confirm(`¿Eliminar la cotización ${c.numero}? Esta acción no se puede deshacer.`)) return;
    accion(() => ventasApi.deleteCotizacion(c.id), `Cotización ${c.numero} eliminada`);
  };

  const handleConvertir = async (c: Cotizacion) => {
```

### Paso 4.5 — Botones ✏️/🗑️ en la fila (solo Borrador)

`old_string`:
```typescript
                        {c.estado === 'Borrador' && (
                          <button className="btn-icon" title="Marcar como enviada" onClick={() => handleEnviar(c)}>📤</button>
                        )}
```
`new_string`:
```typescript
                        {c.estado === 'Borrador' && (
                          <>
                            <button className="btn-icon" title="Editar" onClick={() => setEditando(c)}>✏️</button>
                            <button className="btn-icon" title="Marcar como enviada" onClick={() => handleEnviar(c)}>📤</button>
                            <button className="btn-icon" title="Eliminar" onClick={() => handleEliminar(c)}>🗑️</button>
                          </>
                        )}
```

### Paso 4.6 — Render del modal en modo edición

Anclar por el bloque del modal de creación. `old_string`:
```typescript
      {showNueva && (
        <NuevaCotizacionModal
          onClose={() => setShowNueva(false)}
          onCreated={() => { setShowNueva(false); fetchCotizaciones(); setToast({ msg: 'Cotización creada exitosamente', type: 'success' }); }}
        />
      )}
```
`new_string`:
```typescript
      {showNueva && (
        <NuevaCotizacionModal
          onClose={() => setShowNueva(false)}
          onCreated={() => { setShowNueva(false); fetchCotizaciones(); setToast({ msg: 'Cotización creada exitosamente', type: 'success' }); }}
        />
      )}

      {editando && (
        <NuevaCotizacionModal
          cotizacion={editando}
          onClose={() => setEditando(null)}
          onCreated={() => { setEditando(null); fetchCotizaciones(); setToast({ msg: 'Cotización actualizada', type: 'success' }); }}
        />
      )}
```

**Verificación del Task 4:**
```
cd frontend && npx tsc --noEmit && npx eslint src/views/VentasView.tsx
grep -c "editando\|handleEliminar" src/views/VentasView.tsx
```
→ tsc y eslint exit 0; `grep -c` ≥ `4`.

---

## Task 5 — Frontend: test del modal en modo edición

**Files:**
- Create: `frontend/src/views/CotizacionesEdit.test.tsx`

**Interfaces:** mockea `ventasApi` (getClientes, getProductos, updateCotizacion). Renderiza
`NuevaCotizacionModal` — pero es una función NO exportada. **Por eso el test valida el flujo a
través de la tab NO es viable sin exportar; en su lugar exportamos el modal.** Requiere un cambio
mínimo adicional en `VentasView.tsx`: exportar el modal.

### Paso 5.1 — Exportar el modal para poder testearlo

En `frontend/src/views/VentasView.tsx`, `old_string`:
```typescript
function NuevaCotizacionModal(
  { onClose, onCreated, cotizacion }:
```
`new_string`:
```typescript
export function NuevaCotizacionModal(
  { onClose, onCreated, cotizacion }:
```

### Paso 5.2 — El test (contenido literal completo del archivo nuevo)

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const { updateSpy, createSpy } = vi.hoisted(() => ({
  updateSpy: vi.fn(() => Promise.resolve({ data: {} })),
  createSpy: vi.fn(() => Promise.resolve({ data: {} })),
}));

vi.mock('../services/ventasApi', () => ({
  ventasApi: {
    getClientes: () => Promise.resolve({ data: [
      { id: 7, nit_cc: '900', razon_social: 'Cliente 7', activo: true },
    ] }),
    getProductos: () => Promise.resolve({ data: [
      { id: 3, sku: 'P3', nombre: 'Producto 3', precio_venta: 20000, tarifa_iva: 19, activo: true },
    ] }),
    updateCotizacion: updateSpy,
    createCotizacion: createSpy,
  },
}));

import { NuevaCotizacionModal } from './VentasView';

const cotizacion = {
  id: 42,
  numero: 'COT-0042',
  fecha: '2026-07-06',
  vigencia_dias: 20,
  fecha_vencimiento: '2026-07-26',
  cliente_id: 7,
  vendedor: 'Ana',
  subtotal: 20000, descuento_total: 0, base_gravable: 20000,
  iva_total: 3800, total: 23800,
  estado: 'Borrador',
  vencida: false,
  observaciones: 'nota',
  created_at: '2026-07-06',
  detalles: [{
    id: 1, producto_id: 3, cantidad: 1, precio_unitario: 20000,
    descuento_porcentaje: 0, subtotal_linea: 20000, iva_porcentaje: 19,
    iva_valor: 3800, total_linea: 23800, created_at: '2026-07-06',
  }],
} as any;

describe('NuevaCotizacionModal — modo edición (#25)', () => {
  beforeEach(() => { updateSpy.mockClear(); createSpy.mockClear(); });

  it('en modo edición precarga el vendedor y guarda con updateCotizacion (PUT)', async () => {
    const onCreated = vi.fn();
    const user = userEvent.setup();
    render(<NuevaCotizacionModal cotizacion={cotizacion} onClose={() => {}} onCreated={onCreated} />);

    // Título de edición y datos precargados
    expect(await screen.findByText(/Editar Cotización/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByDisplayValue('Ana')).toBeInTheDocument());

    // Guardar → llama updateCotizacion con el id, NO createCotizacion
    await user.click(screen.getByRole('button', { name: /Guardar|Actualizar/ }));
    await waitFor(() => expect(updateSpy).toHaveBeenCalledTimes(1));
    expect(updateSpy.mock.calls[0][0]).toBe(42);
    expect(createSpy).not.toHaveBeenCalled();
    expect(onCreated).toHaveBeenCalled();
  });
});
```

**Nota para el ejecutor:** el nombre exacto del botón de guardar puede ser "Guardar" o
"Crear/Actualizar" — la regex `/Guardar|Actualizar/` cubre ambos; si el texto real fuera otro,
ajústalo leyendo el JSX del footer del `Modal` en `VentasView.tsx` (NO inventes: léelo). Verifica
también que las props mínimas de `Cliente`/`Producto` que el modal usa estén en los mocks (si el
render se queja de un campo faltante, añádelo al mock con un valor plausible leído del type).

**Verificación del Task 5:**
```
cd frontend && npx vitest run src/views/CotizacionesEdit.test.tsx
```
→ 1 passed.

---

## Task 6 — Cierre: build/tests reales + docs del repo

**Files:**
- Modify: `PENDIENTES.md`, `DOCUMENTACION.md`, `BITACORA.md`

**Pasos:**
1. Correr la verificación real completa (Phase 6 lo re-ejecuta, pero el ejecutor confirma):
   ```
   cd backend && python -m pytest -q
   cd ../frontend && npx vitest run && npx tsc --noEmit
   ```
   Todo verde antes de tocar docs.
2. `DOCUMENTACION.md` sección 13: añadir fila `| 48 | #25: editar y eliminar cotizaciones en
   Borrador (PUT/DELETE con guard 409 + auditoría del borrado) + tests | ✅ Completado 2026-07-06 |`
   tras la fila 47.
3. `PENDIENTES.md`: quitar la fila `| 25 | **Editar/eliminar cotizaciones en Borrador** | ... |`;
   actualizar la cabecera a **19ª revisión** citando el cierre de #25; actualizar el conteo de tests
   API y de componentes en la línea "Estado general" con los números reales del paso 1.
4. `BITACORA.md`: añadir al final una entrada de sesión "Editar/eliminar cotizaciones en Borrador
   (#25)" con Resumen / Lo que se hizo / Verificación (con los números reales de tests) / Nota de
   proceso (hecho por el pipeline Hydraia), siguiendo el formato de las entradas previas.

**Verificación del Task 6:**
```
grep -c "| 25 |" PENDIENTES.md   # → 0 (ya no está el pendiente #25)
grep -c "#25" DOCUMENTACION.md   # → ≥ 1
```

---

## Notas de ejecución (para las fases 4–6)

- **Orden:** Task 1 → 2 (backend, con tests verdes) → 3 → 4 → 5 (frontend) → 6 (cierre). Task 5
  depende del `export` del Paso 5.1 y de las funciones API del Task 3.
- **Anclas:** todos los `Modify` usan texto único citado, no números de línea sueltos.
- **Sin migraciones** — si algún test se queja del esquema, es un error de setup, no del cambio.
- **Reviewers previstos (Phase 5):** `python-reviewer` (router + tests), `react-reviewer` +
  `typescript-reviewer` (VentasView/ventasApi), más el suelo de seguridad
  (`security-reviewer`, `silent-failure-hunter`, `code-reviewer`, `hydraia-reviewer`).
