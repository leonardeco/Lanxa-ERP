# Pendientes — Super Ozono ERP

Backlog vivo del proyecto. Actualizado: **9 de julio de 2026** (22ª revisión — 🚧 en progreso módulo lote+vencimiento (capas 1-2 de 4 listas: modelo + servicio FEFO); resueltos ✅ #2-parcial importador de inventario y ✅ #28 purga de auditoría). **Este archivo es la fuente única de pendientes.**
Estado general: 247 tests API (95% cobertura) + 35 componentes + 5 E2E (local y CI), CI verde, 0 CVEs. Versión: **v0.3.0**.

---

## 🔴 Bloqueados por el negocio (no son de código)

| # | Pendiente | Quién | Notas (verificado 2026-07-05) |
|---|---|---|---|
| 1 | **Validar el mapeo PUC** del motor contable | Contadora | ✔ Documento listo: [`MAPEO-PUC-PARA-CONTADOR.md`](./MAPEO-PUC-PARA-CONTADOR.md) — tiene las preguntas concretas (4135 vs 4120, Caja vs Bancos, compras de gasto) |
| 2 | **Datos maestros reales**: PUC definitivo, inventario inicial, saldos de apertura | Contadora + empresa | ✔ Las tablas ya existen (`SaldoInicial`, seeds). **Importador de inventario LISTO (2026-07-09)**: plantilla `.xlsx` + validación fila-por-fila + carga atómica con entrada en el kardex (Inventario → Importar). Solo falta cargar la información real. El **asiento de apertura** contable sigue pendiente (depende de #3) |
| 3 | Definir **método de costeo** (promedio ponderado recomendado con el kardex actual) | Contadora | ✔ Prerequisito del ítem 8 (asiento de costo de venta) |
| 4 | Confirmar **`UVT_VALOR` 2026** y activar flags `retiene_*` en clientes retenedores | Contadora | ✔ Verificado: sigue el placeholder 49799 en `config.py`; afecta el umbral de retefuente en ventas |

## 🟠 Operativo (administrador del PC servidor)

| # | Pendiente | Notas (verificado 2026-07-05) |
|---|---|---|
| 5 | **Copiar backups fuera del PC servidor** (NAS/nube/otro PC) + guardar `BACKUP_ENCRYPTION_KEY` en un gestor de contraseñas | Riesgo #1: hoy BD, backups y clave viven en el mismo disco. El restore ya está verificado con simulacro (2026-07-02) |
| 6 | Desplegar **v0.3.0** al servidor siguiendo [`DESPLIEGUE.md`](./DESPLIEGUE.md) | ⚠ **Desde v0.3.0 `alembic upgrade head` es obligatorio en cada actualización** (producción ya no hace `create_all`). Incluye además: `pip install`, rename `ACCESS_TOKEN_EXPIRE_*`, `alembic stamp` (una sola vez), CA en PCs cliente nuevos |
| 7 | Entregar [`MANUAL-DE-USUARIO.md`](./MANUAL-DE-USUARIO.md) a los 4 usuarios y que cambien su contraseña inicial | ✔ Manual existe y está vigente |
| 7a | **Drill de restore trimestral** (calendarizarlo) | El procedimiento se verificó una vez (2026-07-02); un backup solo es confiable si se prueba periódicamente |
| 7b | Documentar la vigencia del certificado TLS local y cuándo regenerarlo | `scripts/generate_tls_cert.py` — nadie sabe hoy la fecha de expiración |
| 27 | **Revisar el job E2E del CI al hacer release** | Nuevo 2026-07-05: el job "E2E — smoke Playwright" es informativo (`continue-on-error`) — sus fallos NO bloquean el merge, hay que mirarlos a mano en Actions |
| 33op | **🔐 (OPERATIVO) Definir `SEED_ADMIN_PASSWORD` en el `.env` del servidor y rotar la clave del admin** | ✅ **Código resuelto 2026-07-05**: con `DEBUG=false` la app ya NO arranca con la clave por defecto (validator en `config.py`), y `.env.servidor` trae el campo con nota. **Queda la acción operativa**: el admin del servidor debe poner su clave propia en `.env` (parte del #6 despliegue) y cambiarla desde la UI tras el primer login (parte del #7) |

## 🟡 Técnico — deuda puntual (dev)

| # | Pendiente | Notas (verificado 2026-07-05) |
|---|---|---|
| 8 | **Asiento de costo de venta** (DB 6135 / CR 1435 al confirmar venta) | Depende del ítem 3. Sin esto el P&L muestra ingresos, no margen |
| 10 | Migración Alembic de **nulabilidad legacy** (BD creadas pre-tipado vs modelos 2.0) | ✔ Drift sigue documentado en `alembic/versions/72f7b9fae762`. Requiere backfill revisado contra la BD real del servidor |
| 12 | Locks de concurrencia (`with_for_update`) en abonos y stock | ✔ Verificado: no hay ningún `with_for_update` en el código. **Solo si** el despliegue pasa a multi-worker; con uvicorn single-worker en LAN no aplica |
| 12a | Race en numeración de documentos (`MAX+1` sin lock en SOG-V/SOG-CP/RC/CE/COT/NC/ND) | ✔ Verificado en `core/numbering.py` (la nota en el docstring sigue vigente y ahora cubre también COT/NC/ND). Mismo escenario que #12: solo multi-worker |
| 13 | Extraer servicios de dominio (`confirmar_venta` orquesta stock+CxC+asiento inline en el router) | ✔ Verificado: sigue inline en `ventas/router.py` (y `convertir_cotizacion` ahora también llama `create_venta` directo). Incluye unificar commit/flush (BUG-006) y `estado` Enum vs String |
| 14a | Unificar Cliente/Proveedor/Tercero a nivel de modelo | ✔ Verificado: `CuentaPorCobrar.cliente_nit` sigue siendo `String(20)` sin FK; la materialización por NIT es el puente |

## 🟢 Funcional — siguientes features (por prioridad de negocio)

| # | Feature | Alcance (verificado 2026-07-05) |
|---|---|---|
| 🚧 Lotes | **Trazabilidad por lote + vencimiento** (EN PROGRESO 2026-07-09, 2/4 capas) | Módulo por capas — ✅ **Capa 1** (modelo `Lote`, flag `controla_lote`, `kardex.lote_id`, migración `a1b2c3d4e5f6`) · ✅ **Capa 2** (servicio `entrada_lote` + `consumir_fefo` con FEFO, invariante `stock_actual == Σ lotes`, 5 tests) · ⏳ **Capa 3** (enganche compras/ventas/ajuste/importador — SIGUIENTE) · Capa 4 (alertas de vencimiento + existencias por lote + UI). Opt-in por producto, **FEFO**, sin producción (MVP). Rama `feat/lotes-vencimiento` (en GitHub, sin PR aún) |
| 18 | **RRHH y nómina** (Fase 2) | Empleados, contratos, liquidación — requiere definiciones de negocio propias |
| 20 | Activación Alegra con facturación electrónica DIAN | ✔ La integración está construida y testeada con mocks; falta cuenta/token real y rotación documentada (SEC-002) |
| 21 | Empaquetado Electron (Fase 4) | App de escritorio .exe |
| 21a | Entorno de staging (aunque sea una carpeta paralela con BD copia en el mismo servidor) | Hoy todo cambio va directo a producción — riesgo de proceso, no de código |
| 21b | ¿Multi-bodega? — **pregunta de negocio** | El inventario es global; si Super Ozono maneja planta + punto de venta separados, el kardex actual no lo distingue. Confirmar con la empresa antes de diseñar |

## ⚖️ Cumplimiento Colombia (activar junto con la facturación electrónica)

| # | Pendiente | Notas |
|---|---|---|
| 22 | Requisitos DIAN en la factura impresa | Verificar razón social, régimen, y **resolución de numeración autorizada** (el consecutivo SOG-V-#### es interno) |
| 23 | Habeas Data (Ley 1581 de 2012) | Clientes persona natural: aviso de privacidad y política de tratamiento de datos |
| 24 | Política de redondeo de retenciones validada con la contadora | Hoy `round()` half-even de Python; confirmar contra la práctica DIAN |

## 🔵 Nice-to-have

- Seeder de datos demo (50 clientes, 200 ventas) para probar rendimiento de UI
- Tests de los utilitarios de impresión (`printFactura.ts`, `printCotizacion.ts`, etc.)
- **30 — Access token de `localStorage` a memoria** (revisión de seguridad 2026-07-05): un XSS podría leerlo; ya está mitigado (vida 15 min + refresh en cookie HttpOnly, ver REPORTE_SEGURIDAD) — reevaluar si el ERP sale de la LAN
- `APP_VERSION` se mantiene manual en `config.py` — recordar alinearla con el tag en cada release (v0.3.0 ✔)
- Política de contraseñas (complejidad/expiración) — hoy solo mínimo 8 caracteres; aceptable en LAN
- Blacklist de JTI en Redis para revocación inmediata de access tokens — innecesario con vida de 15 min; además desde v0.3.0 el Admin puede revocar los refresh tokens (14c)
- **ecdsa / PYSEC-2026-1325** (2026-07-09): la CVE se **ignora en CI** con justificación (inalcanzable — los JWT usan HS256 + backend `cryptography`; `ecdsa` es dep transitiva de `python-jose` que solo se importa para algoritmos ES*, y no hay versión con fix). Evaluar migrar `python-jose` → `PyJWT` para eliminar la dependencia `ecdsa` por completo.

---

**Regla de mantenimiento:** al completar un ítem, moverlo a la tabla de completados de
`DOCUMENTACION.md` (sección 13) con fecha, y registrar la sesión en `BITACORA.md`.
