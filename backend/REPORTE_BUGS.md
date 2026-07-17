# Reporte de Bugs — Super Ozono Global ERP
**Fecha:** 2026-06-26
**Versión analizada:** 0.2.0
**Alcance:** Backend FastAPI (`superozono-erp/backend`)
**Método:** Análisis estático + pruebas automatizadas (104/104 tests pasan)
**Auditor:** Claude Sonnet 4.6

---

> **Actualización 2026-07-17:** BUG-004/005 cerrados con `#12a` (`document_sequences` + `FOR UPDATE`). BUG-006 cerrado con servicios de dominio ventas (#13). Ver `PENDIENTES.md` / `DOCUMENTACION.md` §13.

## Resumen

| ID | Severidad | Estado | Descripción corta |
|---|---|---|---|
| BUG-001 | MEDIO | ✅ Corregido 2026-07-01 | `reteica` nunca se calcula en ventas (motor de retenciones híbrido) |
| BUG-002 | ALTO | ✅ Corregido 2026-07-01 | N+1 queries en `list_ventas()` (`selectinload` + `_build_venta_response`) |
| BUG-003 | MEDIO | ✅ Corregido 2026-07-02 | `datetime.utcnow()` deprecado (helper `utcnow()` en `core/time.py`) |
| BUG-004 | MEDIO | ✅ Corregido 2026-07-15 | Race numeración ventas → `document_sequences` + locks (#12a) |
| BUG-005 | MEDIO | ✅ Corregido 2026-07-15 | Race numeración compras → mismo mecanismo (#12a) |
| BUG-006 | BAJO | ✅ Corregido 2026-07-10 | Servicios de dominio ventas (#13) |
| BUG-007 | BAJO | ✅ Corregido 2026-07-02 | POST→PUT en updates de Alegra (`alegra_put`, con tests) |
| BUG-C01 | ALTO | ✅ Corregido | `conftest.py` no hacía commit entre requests |
| BUG-C02 | ALTO | ✅ Corregido | `conftest.py` sin `expire_on_commit=False` |

---

## ALTO

### BUG-002 — N+1 queries en `list_ventas()`
**Archivo:** `app/modules/ventas/router.py` líneas 318–372
**Severidad:** ALTO — degradación de performance proporcional al volumen de datos

**Descripción:**
El endpoint `GET /api/v1/ventas/` ejecuta consultas adicionales a la BD por cada venta en el resultado:
- 1 query inicial para listar todas las ventas
- +1 query por venta para obtener el cliente (`db.get(Cliente, venta.cliente_id)`)
- +N queries por venta para obtener cada producto de cada línea de detalle

Con 100 ventas de 5 líneas cada una → **601 queries** por request.

**Código problemático:**
```python
for venta in ventas:
    cliente = await db.get(Cliente, venta.cliente_id)          # ← N queries
    detalles_result = await db.execute(select(VentaDetalle)...) # ← N queries
    for d in detalles_raw:
        prod = await db.get(Producto, d.producto_id)            # ← N×M queries
```

El mismo problema existe en `get_venta()` (líneas 377–432), aunque en menor escala (solo 1 venta).

**Fix recomendado — usar `selectinload`:**
```python
from sqlalchemy.orm import selectinload

@router.get("/", response_model=List[VentaResponse])
async def list_ventas(_: CurrentUser, estado: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = (
        select(VentaDocumento)
        .options(
            selectinload(VentaDocumento.cliente),
            selectinload(VentaDocumento.detalles).selectinload(VentaDetalle.producto),
        )
        .order_by(desc(VentaDocumento.fecha), desc(VentaDocumento.id))
    )
    if estado:
        query = query.where(VentaDocumento.estado == estado)
    result = await db.execute(query)
    return result.scalars().all()
```

Esto reduce el número de queries a **3 fijos**, independientemente del volumen.

**Nota:** Requiere agregar `relationship` a `VentaDocumento` para `cliente` si no existe.

---

### BUG-C01 — `conftest.py` no hacía commit entre requests (CORREGIDO)
**Archivo:** `tests/conftest.py`
**Severidad:** ALTO — hacía fallar ~30 tests
**Estado:** ✅ Corregido el 2026-06-26

**Descripción:**
La función `override_get_db()` del conftest de tests no incluía `await session.commit()` al cerrar la sesión. Los endpoints de ventas usan `db.flush()` sin commit explícito, confiando en que `get_db` de producción haga el commit. Al no hacerlo en tests, los datos creados en un request no eran visibles en el siguiente.

```python
# ANTES (roto):
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session  # ← nunca commitea

# DESPUÉS (corregido):
async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()  # ← igual que producción
        except Exception:
            await session.rollback()
            raise
```

---

### BUG-C02 — `conftest.py` sin `expire_on_commit=False` (CORREGIDO)
**Archivo:** `tests/conftest.py`
**Severidad:** ALTO — causaba `MissingGreenlet` en tests de compras
**Estado:** ✅ Corregido el 2026-06-26

**Descripción:**
`TestingSessionLocal` no tenía `expire_on_commit=False`. Después de hacer commit, SQLAlchemy expiraba los atributos de los objetos ORM. Al acceder a `compra.id` en `compras/router.py` línea 286 (tras el commit), SQLAlchemy intentaba un lazy-load sincrónico que falla en contexto async.

```python
# ANTES (roto):
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

# DESPUÉS (corregido):
TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine,
    expire_on_commit=False  # igual que la sesión de producción
)
```

---

## MEDIO

### BUG-001 — `reteica` nunca se calcula en ventas
**Archivo:** `app/modules/ventas/router.py` línea ~519
**Severidad:** MEDIO — funcionalidad incompleta (retención de ICA)

**Descripción:**
El modelo `VentaDocumento` tiene el campo `reteica` y el schema `VentaResponse` lo incluye. Sin embargo, en `create_venta()` el campo nunca se calcula y permanece en `Decimal("0.00")`. Además, la fórmula del total no lo resta:

```python
# ventas/router.py ~519 — reteica no aparece en la fórmula
retefuente = round(base_gravable * Decimal("0.025"), 2) if base_gravable >= Decimal("1092000") else Decimal("0.00")
reteiva = round(iva_total * Decimal("0.15"), 2) if iva_total > 0 else Decimal("0.00")
total = base_gravable + iva_total - retefuente - reteiva   # ← falta - reteica
```

En compras sí se resta: `total = base_grav + iva_total - rete - reteiva - reteica`

**Impacto actual:** Nulo (reteica siempre es 0, el total es matemáticamente correcto). Pero si se implementa el cálculo de reteica sin corregir la fórmula, el total quedaría incorrecto.

**Fix:**
```python
# Calcular reteica (tasa municipal, varía por municipio — ejemplo Armenia Quindío 0.414%)
reteica = round(base_gravable * Decimal("0.00414"), 2) if base_gravable > 0 else Decimal("0.00")

# Actualizar fórmula:
total = base_gravable + iva_total - retefuente - reteiva - reteica

# Y asignar el campo:
venta.reteica = reteica
```

---

### BUG-003 — `datetime.utcnow()` deprecado en Python 3.12+
**Archivos:**
- `app/core/security.py` líneas 24, 25, 44, 45
- `app/modules/ventas/models.py` líneas 77, 78
- `app/modules/usuarios/models.py` línea 36

**Descripción:**
`datetime.utcnow()` fue marcado como deprecado en Python 3.12 y puede ser removido en versiones futuras. Genera `DeprecationWarning` en logs. El proyecto usa Python 3.13.

**Ocurrencias en el código:**
```python
# security.py
expire = datetime.utcnow() + timedelta(hours=...)
expire = datetime.utcnow() + timedelta(days=...)
return datetime.utcnow() + timedelta(days=...)

# models.py (Column defaults)
created_at = Column(DateTime, default=datetime.utcnow)
updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Fix:**
```python
from datetime import datetime, timezone

# Reemplazar todas las ocurrencias:
datetime.utcnow()        →  datetime.now(timezone.utc)
default=datetime.utcnow  →  default=lambda: datetime.now(timezone.utc)
```

**Nota:** Al cambiar los defaults de columnas, verificar que las comparaciones en `refresh_token_expiry()` también usen `datetime.now(timezone.utc)` para evitar comparar naive vs aware datetimes.

---

### BUG-004 — Race condition en numeración de ventas
**Archivo:** `app/modules/ventas/router.py` líneas 36–41
**Severidad:** MEDIO — ocurre bajo carga concurrente

**Descripción:**
```python
async def _next_venta_numero(db: AsyncSession) -> str:
    result = await db.scalar(select(func.count(VentaDocumento.id)))
    next_num = (result or 0) + 1
    return f"SOG-V-{next_num:04d}"
```

Si dos ventas se crean simultáneamente, ambas obtienen el mismo `COUNT` y generan el mismo número. Dado que `numero` tiene constraint `UNIQUE`, una de las dos peticiones fallará con error 500.

**Fix — usar MAX + FOR UPDATE o secuencia:**
```python
async def _next_venta_numero(db: AsyncSession) -> str:
    result = await db.scalar(
        select(func.max(
            func.cast(func.substr(VentaDocumento.numero, 7), Integer)
        )).with_for_update()  # bloquea hasta commitear
    )
    next_num = (result or 0) + 1
    return f"SOG-V-{next_num:04d}"
```

O mejor aún, usar una tabla de contadores o una secuencia de BD.

---

### BUG-005 — Race condition en numeración de compras
**Archivo:** `app/modules/compras/router.py` líneas 246–249
**Severidad:** MEDIO — ocurre bajo carga concurrente

**Descripción:**
```python
nums_result = await session.execute(select(CompraDocumento.numero))
nums = nums_result.scalars().all()
max_num = max((int(n.split("-")[-1]) for n in nums), default=0)
numero = f"SOG-CP-{max_num + 1:04d}"
```

Mismo problema que BUG-004: carga todos los números, calcula el máximo en Python. Bajo concurrencia, dos requests pueden obtener el mismo máximo.

Adicionalmente, `n.split("-")[-1]` asume que el número siempre tiene exactamente 3 segmentos separados por `-`. Si el formato cambia, lanzará `ValueError` en `int()`.

**Fix:**
```python
result = await session.scalar(
    select(func.max(
        func.cast(func.substr(CompraDocumento.numero, 8), Integer)
    )).with_for_update()
)
max_num = result or 0
numero = f"SOG-CP-{max_num + 1:04d}"
```

---

## BAJO

### BUG-006 — Inconsistencia de commit entre módulos (ventas vs compras)
**Archivos:** `app/modules/ventas/router.py` vs `app/modules/compras/router.py`
**Severidad:** BAJO — no es un bug funcional, es inconsistencia de estilo

**Descripción:**
- `ventas/router.py`: todos los endpoints usan `db.flush()` sin `db.commit()` explícito. Funcionan porque `get_db()` hace commit al final.
- `compras/router.py`: los endpoints llaman `await session.commit()` explícitamente Y `get_db()` también commitea → doble commit (inofensivo para SQLAlchemy, pero confuso).

**Impacto:** Ninguno en producción. Sin embargo, confunde a quien lee el código y puede causar bugs en contextos donde `get_db` no se usa (scripts, seeds, tests con sesiones manuales).

**Recomendación:** Estandarizar a un solo patrón. La opción más clara es que cada router haga su propio `commit()` explícito (como compras), sin depender del comportamiento de `get_db`.

---

### BUG-007 — Alegra sync usa POST para actualizar contactos/productos
**Archivo:** `app/modules/alegra/router.py` líneas 75–76 y 104–106
**Severidad:** BAJO — depende del comportamiento de la API de Alegra

**Descripción:**
```python
# Contactos:
if cliente.alegra_id:
    result = await alegra_post(f"/contacts/{cliente.alegra_id}", payload)  # ¿debería ser PUT?

# Productos:
if producto.alegra_id:
    result = await alegra_post(f"/items/{producto.alegra_id}", payload)    # ¿debería ser PUT?
```

La convención REST estándar para actualizar un recurso existente con ID conocido es `PUT /recurso/{id}`, no `POST /recurso/{id}`. Si la API de Alegra sigue REST estrictamente, este código puede crear duplicados o lanzar errores 4xx silenciosos.

**Fix — revisar docs de Alegra y crear función `alegra_put()`:**
```python
# app/modules/alegra/client.py
async def alegra_put(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{ALEGRA_BASE_URL}{path}",
            json=payload,
            auth=(settings.ALEGRA_EMAIL, settings.ALEGRA_TOKEN),
        )
        resp.raise_for_status()
        return resp.json()

# alegra/router.py
if cliente.alegra_id:
    result = await alegra_put(f"/contacts/{cliente.alegra_id}", payload)
else:
    result = await alegra_post("/contacts", payload)
```

---

## Prioridad de corrección

| Prioridad | Bug | Esfuerzo estimado |
|---|---|---|
| 1 | BUG-002 — N+1 queries (performance) | 2-3 horas |
| 2 | BUG-003 — datetime.utcnow() deprecated | 30 min (search & replace) |
| 3 | BUG-001 — reteica en ventas | 1 hora (incluye lógica de negocio) |
| 4 | BUG-004 / BUG-005 — Race conditions | 1 hora (ambos juntos) |
| 5 | BUG-006 — Inconsistencia commit | 30 min (refactor estilo) |
| 6 | BUG-007 — Alegra PUT vs POST | 1 hora (incluye testing manual) |

---

## Tests de regresión

Todos los bugs están cubiertos por pruebas en `tests/test_bugs.py`. Ejecutar después de cada fix:

```bash
cd C:\Users\LEONARDO GUZMAN\proyectos\PROYECTOS\superozono-erp\backend
venv\Scripts\activate
pytest tests/test_bugs.py -v --tb=short
```
