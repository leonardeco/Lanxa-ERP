# Design Spec — Editar y eliminar cotizaciones en Borrador (#25)

- **Fecha:** 2026-07-06
- **Ruta:** feature (Hydraia Phases 0–6)
- **Pendiente:** #25 (PENDIENTES.md)

## Goal

Permitir **editar** y **eliminar** cotizaciones **únicamente en estado `Borrador`**. Hoy una
cotización solo avanza por transiciones (enviar/aprobar/rechazar/convertir); para corregir un
borrador con un error hay que rechazarlo y crear otro, dejando basura en la lista. Este cambio
da corrección real (editar) y limpieza (eliminar) sobre un documento que aún no tiene efectos.

## Chosen approach + rejected alternatives

**Elegido — dos endpoints nuevos + reutilizar el modal de creación (cambio quirúrgico).**
`PUT /cotizaciones/{id}` y `DELETE /cotizaciones/{id}`, ambos con guard `409` si el estado no es
`Borrador`. El front reutiliza `NuevaCotizacionModal` con una prop opcional `cotizacion` (POST vs
PUT) y añade botones ✏️/🗑️ visibles solo en `Borrador`. El cálculo de totales, hoy inline en
`create_cotizacion`, se extrae a un helper compartido para que crear y editar no divergan.

- **Rechazado — borrado lógico (nuevo estado `Anulada`).** Requeriría migración del enum
  `EstadoCotizacion`, filtros nuevos en la UI y en los listados, y un estado más que mantener —
  todo para un documento que **no tiene efectos** de inventario/contabilidad. Sobredimensionado.
  Un borrado real + rastro de auditoría cubre la necesidad sin deuda.
- **Rechazado — borrado real sin auditoría.** Más simple, pero pierde el rastro de quién borró
  qué. El sistema ya audita maestros/parámetros (#36); un borrado debe dejar traza por coherencia.
- **Rechazado — edición solo de ítems.** Limita corregir el cliente o la vigencia, que son errores
  igual de comunes en un borrador. El modal ya captura todos los campos; reusarlo cuesta lo mismo.

## Code-graph anchors (estructura real que el diseño respeta)

Sin codegraph (no instalado); anclas por lectura dirigida:

- **Modelo** `backend/app/modules/ventas/models.py`:
  - `EstadoCotizacion` (enum): `BORRADOR, ENVIADA, APROBADA, RECHAZADA, CONVERTIDA` (línea 43).
  - `Cotizacion` (línea 211): `numero, fecha, vigencia_dias, fecha_vencimiento, cliente_id,
    vendedor, subtotal, descuento_total, base_gravable, iva_total, total, estado, observaciones`;
    `detalles = relationship(..., cascade="all, delete-orphan")` (línea 243) → borrar la
    cotización borra sus líneas sin SQL manual.
  - `CotizacionDetalle` (línea 250): `producto_id, cantidad, precio_unitario,
    descuento_porcentaje, subtotal_linea, iva_porcentaje, iva_valor, total_linea, notas`.
- **Router** `backend/app/modules/ventas/router.py`:
  - `_calcular_detalle(det)` (→ línea 102): subtotal/iva/total por línea. Reutilizar tal cual.
  - `_build_cotizacion_response(cot)` (línea 439) y `_get_cotizacion_or_404(db, id)` (línea 489)
    con `_COTIZACION_EAGER` (línea 432). Reutilizar tal cual.
  - `create_cotizacion` (línea 525): el bloque de totales (líneas 549-581) es el patrón a extraer
    al helper `_aplicar_detalles_y_totales`.
  - Transiciones existentes (`enviar`/`aprobar`/`rechazar`/`convertir`, líneas 587-644) muestran el
    patrón de guard de estado con `HTTPException(status_code=400/409)`.
  - Endpoints de cotización usan `CurrentUser` (cualquier autenticado), **sin rol especial** →
    edit/delete lo replican.
- **Auditoría** `backend/app/modules/auditoria/service.py:45` —
  `registrar_auditoria(db, usuario, accion, entidad, entidad_id, descripcion, cambios=None)`,
  añade a la sesión sin commit, IP vía ContextVar. Convención: `accion` capitalizada
  (`"Crear"`, `"Actualizar"`), `entidad` PascalCase sin tildes (`"Producto"`, `"Cliente"`).
- **Schemas** `backend/app/modules/ventas/schemas.py`: `CotizacionCreate` (línea 244),
  `CotizacionResponse` (línea 258), `VentaDetalleResponse`.
- **Frontend**:
  - `frontend/src/services/ventasApi.ts` — cliente API (`getCotizaciones`, `enviarCotizacion`, …).
  - `frontend/src/views/VentasView.tsx` — `CotizacionesTab` (línea 764): estado, handlers
    (`handleEnviar/Aprobar/Rechazar/Convertir`), tabla con botones por estado (líneas 887-902),
    `NuevaCotizacionModal` (usado en línea 912).

## Global constraints

- **Estado editable/eliminable: SOLO `Borrador`.** Cualquier otro → `409`.
- **Reglas de la casa** (de create): validar cliente (`404` si no existe) y cada producto
  (`404` si no existe); `fecha_vencimiento = fecha + vigencia_dias`; totales redondeados a 2
  decimales con `round(x, 2)`; `Decimal` en todo el dinero.
- **Auditoría:** `entidad="Cotizacion"`; edit → `accion="Actualizar"`; delete → `accion="Eliminar"`.
- **Sin efectos colaterales:** no tocar ventas, inventario, cartera ni contabilidad.
- **Migraciones:** ninguna (no cambia el esquema).
- **Tests:** pytest (backend, patrón `tests/test_cotizaciones.py`) + Vitest (frontend). CI debe
  quedar verde; convención del repo: al cerrar, actualizar PENDIENTES/DOCUMENTACION/BITACORA.

## Threat model + mitigations

Superficie: input de un usuario **autenticado** (auth por `CurrentUser` ya existente) a dos
endpoints que mutan/borran un recurso propio del sistema. Sin datos enviados a terceros, sin
secretos, sin PII nueva.

| Riesgo (OWASP) | Mitigación (se vuelve tarea de plan) |
|---|---|
| A01 Broken Access Control — editar/borrar una cotización ya enviada/convertida | Guard `409` `estado != BORRADOR` **dentro** del handler, validado sobre el registro recién leído en la misma sesión/transacción. Test explícito de 409 por cada endpoint. |
| A01 — IDOR / recurso inexistente | `_get_cotizacion_or_404` (reutilizado) → `404`. Test de 404. |
| A04 Insecure Design — totales manipulados desde el cliente | Los totales se **recalculan en el backend** con `_calcular_detalle`; nunca se confía en montos del payload (igual que create). |
| Integridad referencial — `cliente_id`/`producto_id` inválidos | Validación explícita (`db.get` → `404`), idéntica a create. |
| Trazabilidad — borrado sin rastro | `registrar_auditoria(..., "Eliminar", ...)` **antes** del `db.delete`, en la misma transacción (commit atómico). |

## Design adversarial pass (una pasada, antes de congelar)

- *«¿Y si cambian el estado entre el GET de la UI y el PUT/DELETE?»* → el guard no se fía del
  estado que traiga el cliente; relee el registro y valida `estado == BORRADOR` en el servidor. Si
  otro proceso lo envió/convirtió justo antes, el segundo request recibe `409`. Aceptable (LAN,
  uvicorn single-worker; sin carrera real de multi-worker, ver #12).
- *«¿El PUT permite colar un `estado` o `numero` nuevo?»* → `CotizacionUpdate` **no** incluye
  `estado`, `numero`, `venta_id` ni `motivo_rechazo`; solo los campos editables de cabecera +
  `detalles`. El `numero` y el `estado` se preservan del registro existente.
- *«Reemplazar detalles: ¿fugas de huérfanos?»* → `cascade="all, delete-orphan"`: vaciar
  `cot.detalles` (o borrar los viejos) y añadir los nuevos deja la tabla consistente; un test de
  totales tras editar lo confirma.
- *«¿La auditoría del borrado se pierde si el delete revienta?»* → ambos van en la misma
  transacción; si el `delete` falla, el rollback también descarta el registro de auditoría. Correcto:
  no queremos “Eliminado” en el log si no se eliminó.
- *«¿Editar deja `updated_at` viejo?»* → el modelo tiene `onupdate=utcnow`; al mutar la fila se
  refresca solo.

## Acceptance criteria

1. `PUT /cotizaciones/{id}` sobre un `Borrador` actualiza cabecera + detalles y **recalcula
   totales**; responde `200` con el `CotizacionResponse` actualizado.
2. `PUT`/`DELETE` sobre una cotización en cualquier estado ≠ `Borrador` → `409` y **no** modifica nada.
3. `DELETE /cotizaciones/{id}` sobre un `Borrador` → `204`, borra la cotización y sus detalles, y
   deja **un registro de auditoría** `Eliminar/Cotizacion`.
4. `PUT`/`DELETE` sobre un id inexistente → `404`.
5. Front: en la fila de una cotización **en Borrador** aparecen ✏️ (editar) y 🗑️ (eliminar, con
   confirmación); en cualquier otro estado **no** aparecen.
6. El modal de edición precarga los datos actuales y guarda con `PUT`; el de creación sigue igual.
7. CI verde: pytest + Vitest + lint/tsc.
