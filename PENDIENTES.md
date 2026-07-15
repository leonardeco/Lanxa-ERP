# Pendientes — Super Ozono ERP

Backlog vivo del proyecto. Actualizado: **15 de julio de 2026** (32ª revisión — ✅ **codeable sin contadora**: política de contraseñas (min 8 + letra + dígito, bloquea fábrica `Admin2026!`); **#14a puente** Cliente/Proveedor → `terceros` al crear/editar; **#21a staging LAN** `ops/STAGING.md` + `ops/setup-staging.ps1`. Previo: Runs 2–5 multi-tenant, #12/#12a locks, Docker/Terraform/ECR/CloudFront como código (sin apply cloud en este PC). **Sigue bloqueado por contadora: #1–4 y #8.** Operativo en servidor: #5–7b, #33op. **Este archivo es la fuente única de pendientes.**
Estado general: suite API + Vitest + E2E (local y CI), versión LAN **v0.3.0**.
**Run 2–5 (2026-07-15):** tenancy + RLS + filtros + **uniques `(tenant_id, clave)`** + **`POST /api/v1/tenants/onboard`**. Login por email sigue global (preferir emails únicos entre empresas).

---

## 🔴 Bloqueados por el negocio (no son de código)

| # | Pendiente | Quién | Notas (verificado 2026-07-05) |
|---|---|---|---|
| 1 | **Validar el mapeo PUC** del motor contable | Contador | ✔ Documento + paquete reunión listos: [`MAPEO-PUC-PARA-CONTADOR.md`](./MAPEO-PUC-PARA-CONTADOR.md), `ops/INSTRUCCIONES-REUNION-CONTADOR.md`, carpeta Escritorio `Entrega-Contador-PUC\`. **Queda humano:** reunión y respuestas por escrito |
| 2 | **Datos maestros reales**: PUC definitivo, inventario inicial, saldos de apertura | Contadora + empresa | ✔ Las tablas ya existen (`SaldoInicial`, seeds). **Importador de inventario LISTO (2026-07-09)**: plantilla `.xlsx` + validación fila-por-fila + carga atómica con entrada en el kardex (Inventario → Importar). Solo falta cargar la información real. El **asiento de apertura** contable sigue pendiente (depende de #3) |
| 3 | Definir **método de costeo** (promedio ponderado recomendado con el kardex actual) | Contadora | ✔ Prerequisito del ítem 8 (asiento de costo de venta) |
| 4 | Confirmar **`UVT_VALOR` 2026** y activar flags `retiene_*` en clientes retenedores | Contadora | ✔ Verificado: sigue el placeholder 49799 en `config.py`; afecta el umbral de retefuente en ventas |

## 🟠 Operativo (administrador del PC servidor)

| # | Pendiente | Notas (verificado 2026-07-05) |
|---|---|---|
| 5 | **Copiar backups fuera del PC servidor** (NAS/nube/otro PC) + guardar `BACKUP_ENCRYPTION_KEY` en un gestor de contraseñas | ✅ Offsite OneDrive OK (último backup 2026-07-15 15:55). Recordatorio: `C:\SuperOzono-Backups\RECORDATORIO-CLAVE-BACKUP.txt` — **cópiala al gestor y borra ese archivo** (paso en `ops/HOY-GO-LIVE.md`) |
| 6 | Desplegar **v0.3.0** al servidor siguiendo [`DESPLIEGUE.md`](./DESPLIEGUE.md) | ✅ **Hecho en este PC:** health `v0.3.0`, Alembic head, CORS/IP `192.168.1.48`, CA confiable, `start.bat` + acceso escritorio. Ver `ops/ESTADO-OPERATIVO-PC.md` |
| 7 | Entregar [`MANUAL-DE-USUARIO.md`](./MANUAL-DE-USUARIO.md) a los usuarios y que cambien su contraseña inicial | ✅ **Paquete 7 roles listo:** Escritorio `Entrega-SuperOzono-v030` (`01`–`07` + checklist) y guía `ops/HOY-GO-LIVE.md` / Escritorio `HOY-GO-LIVE-SuperOzono.md`. **Queda humano:** entregar tarjetas y marcar cambio de clave |
| 7a | **Drill de restore trimestral** (calendarizarlo) | ✅ Tarea `SuperOzonoERP-RestoreDrillReminder` + próximo **2026-10-15** en `ops/ENTREGA-OPERATIVA-v030.md`. Ejecutar el drill en esa fecha |
| 7b | Documentar la vigencia del certificado TLS local y cuándo regenerarlo | ✅ Documentado: expira **2028-10-17**, SAN `192.168.1.48` (+ localhost). Ver ENTREGA y ESTADO-OPERATIVO |
| 27 | **Revisar el job E2E del CI al hacer release** | Nuevo 2026-07-05: el job "E2E — smoke Playwright" es informativo (`continue-on-error`) — sus fallos NO bloquean el merge, hay que mirarlos a mano en Actions |
| 33op | **🔐 (OPERATIVO) Definir `SEED_ADMIN_PASSWORD` en el `.env` del servidor y rotar la clave del admin** | ✅ **Código resuelto 2026-07-05**: con `DEBUG=false` la app ya NO arranca con la clave por defecto (validator en `config.py`), y `.env.servidor` trae el campo con nota. **Queda la acción operativa**: el admin del servidor debe poner su clave propia en `.env` (parte del #6 despliegue) y cambiarla desde la UI tras el primer login (parte del #7) |

## 🟡 Técnico — deuda puntual (dev)

| # | Pendiente | Notas (verificado 2026-07-05) |
|---|---|---|
| 8 | **Asiento de costo de venta** (DB 6135 / CR 1435 al confirmar venta) | Depende del ítem 3. Sin esto el P&L muestra ingresos, no margen |
| 10 | Migración Alembic de **nulabilidad legacy** + **drift de versión** (BD creadas por `create_all` vs cadena Alembic) | ✔ Drift de nulabilidad documentado en `alembic/versions/72f7b9fae762`. **BD local reconciliada 2026-07-10**: estaba marcada en `c3e9a17f5d02` pero con esquema `create_all` sin las columnas de lotes (`productos.controla_lote`, `movimientos_inventario.lote_id`, `compras_detalles.codigo_lote/fecha_vencimiento`) — se agregaron por `ALTER TABLE` + `alembic stamp b2c3d4e5f6a7` + `upgrade head`. ⚠ **La BD del PC servidor casi seguro tiene el mismo drift** — aplicar el mismo procedimiento al desplegar (ver #6). ✅ **Blindado en CI desde Run 1 (2026-07-14, PR #26):** el CI corre `alembic upgrade head` + **`alembic check`** contra Postgres en cada PR (falla si hay drift). Además se detectó y corrigió que `env.py` no importaba el modelo `auditoria` (un `--autogenerate` habría propuesto `DROP TABLE auditoria`) |
| 12 | Locks de concurrencia (`with_for_update`) en abonos y stock | ✅ **Hecho 2026-07-15**: `registrar_movimiento` bloquea `Producto` + rechaza stock negativo en salidas (`StockError`); FEFO/entrada de lotes con `FOR UPDATE`; `confirmar_venta` bloquea productos por id; abonos/anulación de pagos bloquean CxC/CxP/Pago. Tests `test_locks_stock.py`. Útil ya en LAN y obligatorio en multi-worker |
| 12a | Race en numeración de documentos (`MAX+1` sin lock en SOG-V/SOG-CP/RC/CE/COT/NC/ND) | ✅ **Hecho 2026-07-15**: tabla `document_sequences` + `SELECT … FOR UPDATE` + savepoint/retry en `core/numbering.py`; siembra desde MAX legacy; migración `d5e6f7a8b9c0`; tests `test_numbering.py`. Prefijos SOG-V/SOG-CP/RC/CE/COT/NC/ND. (#12 stock/abonos sigue pendiente si multi-worker) |
| 13 | Extraer servicios de dominio (`confirmar_venta` orquesta stock+CxC+asiento inline en el router) | ✅ **Hecho 2026-07-10**: nuevo `ventas/services.py` (`confirmar_venta`/`anular_venta` + `VentaError`); los endpoints quedaron delgados (validan transición → delegan → mapean `VentaError`→400). `create_venta` reutiliza `get_venta` (elimina el builder duplicado); quitados los `hasattr(estado,'value')` (es SAEnum). Patrón transaccional documentado (servicios hacen flush, la dependencia commitea). 276 tests verdes, comportamiento idéntico. Rama `refactor/servicios-dominio-ventas` |
| 14a | Unificar Cliente/Proveedor/Tercero a nivel de modelo | ✅ **Puente codeable 2026-07-15**: al crear/editar Cliente o Proveedor se materializa/actualiza `terceros` (tipo Cliente/Proveedor → Mixto si es ambos). Helpers `sync_tercero_from_*` en `asientos.py`. Unificación total de modelo (FK única) queda como refactor mayor opcional; CxC/CxP siguen por NIT string |

## 🟢 Funcional — siguientes features (por prioridad de negocio)

| # | Feature | Alcance (verificado 2026-07-05) |
|---|---|---|
| 18 | **RRHH y nómina** (Fase 2) | Empleados, contratos, liquidación — requiere definiciones de negocio propias |
| 20 | Activación Alegra con facturación electrónica DIAN | ✔ La integración está construida y testeada con mocks; falta cuenta/token real y rotación documentada (SEC-002) |
| 21 | Empaquetado Electron (Fase 4) | App de escritorio .exe |
| 21a | Entorno de staging (aunque sea una carpeta paralela con BD copia en el mismo servidor) | ✅ **Documentado + script 2026-07-15**: `ops/STAGING.md` (LAN carpeta paralela + Docker opcional) y `ops/setup-staging.ps1` (`.env.staging` + copia BD). **Acción operativa**: crear la carpeta staging en el servidor cuando se quiera usar |
| 21b | ¿Multi-bodega? — **pregunta de negocio** | El inventario es global; si Super Ozono maneja planta + punto de venta separados, el kardex actual no lo distingue. Confirmar con la empresa antes de diseñar |

## ⚖️ Cumplimiento Colombia (activar junto con la facturación electrónica)

| # | Pendiente | Notas |
|---|---|---|
| 22 | Requisitos DIAN en la factura impresa | Verificar razón social, régimen, y **resolución de numeración autorizada** (el consecutivo SOG-V-#### es interno) |
| 23 | Habeas Data (Ley 1581 de 2012) | Clientes persona natural: aviso de privacidad y política de tratamiento de datos |
| 24 | Política de redondeo de retenciones validada con la contadora | Hoy `round()` half-even de Python; confirmar contra la práctica DIAN |

## 🔵 Nice-to-have

- ~~Seeder de datos demo (50 clientes, 200 ventas) para probar rendimiento de UI~~ ✅ **Hecho 2026-07-14** (CLI `backend/seeds/seed_demo.py`, BD demo dedicada `superozono_demo.db` con guard anti-producción, idempotente `--clean`; ver DOCUMENTACION.md §13)
- ~~Tests de los utilitarios de impresión (`printFactura.ts`, `printCotizacion.ts`, etc.)~~ ✅ **Hecho 2026-07-11** (24 tests Vitest para las 4 utilidades: HTML generado, escapado XSS, filas condicionales de retención/descuento, ramas CxC/CxP y popup bloqueado; ver DOCUMENTACION.md §13 #55)
- ~~**30 — Access token de `localStorage` a memoria**~~ ✅ **Hecho 2026-07-11**: el token vive solo en memoria (`api.ts` `getAccessToken`/`setAccessToken`), fuera de `localStorage`; la sesión persiste vía refresh token en cookie HttpOnly. 5 tests Vitest nuevos; ver DOCUMENTACION.md §13 #56
- `APP_VERSION` se mantiene manual en `config.py` — recordar alinearla con el tag en cada release (v0.3.0 ✔)
- ~~Política de contraseñas (complejidad)~~ ✅ **Hecho 2026-07-15**: min 8 + letra + dígito; bloquea contraseñas de fábrica (`Admin2026!`, etc.) en alta usuario, cambio propio, reset admin y onboard tenant (`app/core/passwords.py`). Sin expiración (aceptable en LAN).
- Blacklist de JTI en Redis para revocación inmediata de access tokens — innecesario con vida de 15 min; además desde v0.3.0 el Admin puede revocar los refresh tokens (14c)
- ~~**ecdsa / PYSEC-2026-1325** — migrar `python-jose` → `PyJWT` para eliminar la dep `ecdsa`~~ ✅ **Hecho 2026-07-11** (PyJWT 2.13.0, HS256; ver DOCUMENTACION.md §13 #54). El `--ignore-vuln` se quitó del CI y `pip-audit` corre sin excepciones.

---

## 🗺️ Roadmap estratégico enero 2027 (propuesto — investigación 2026-07-09, por confirmar)

Ítems del análisis de ERPs del sector + la web de la empresa (agro-biotech, 17 países, franquicias, fabricante de proceso). **No son decisiones cerradas** — candidatos priorizados para el despliegue de enero 2027.

**Cumplimiento Colombia (obligatorio para operar legal):**
- **Facturación electrónica DIAN — activar (amplía #20):** cuenta/token Alegra real + **resolución de numeración autorizada** + validaciones de la normativa 2026 (Res. 000227/2025 y 000202/2025). **Bloqueante del lanzamiento legal.**
- **Nómina electrónica DIAN:** documento soporte con CUNE, transmisión en los 10 días hábiles del mes siguiente (si hay empleados en nómina).
- **Documento soporte** en adquisiciones a no obligados a facturar.
- **Exógena / medios magnéticos DIAN.**

**Negocio específico (agro / proceso / multi-país):**
- **Producción por fórmula/lote (process manufacturing):** BOM/receta, orden de producción, consumo de insumos → lote de producto terminado. Complementa el módulo de lotes en curso.
- **Multi-moneda / multi-país:** hoy asume COP; el negocio opera en 17 países.
- **Portal/red de distribuidores + comisiones (MLM)** y **ecommerce + pasarela de pago (Stripe LATAM)** — proyectos del roadmap del ecosistema.

**Estándar de ERP (eficiencia/escala):**
- **CRM ligero** (leads/asesores, pipeline B2B).
- **Reórdenes automáticas:** sugerencia de orden de compra cuando `stock ≤ stock_minimo`.
- **Costeo promedio ponderado** (ver #3).

**Decisión de arquitectura (para hablar antes de escalar):**
- **LAN vs cloud/web:** el negocio multi-país + ecommerce + franquicias podría necesitar acceso remoto; hoy es LAN (5 PCs). Decidir antes de conectar ecommerce/red. (Relacionado: #21a staging, #5 backups offsite, #21b multi-bodega.)

---

**Regla de mantenimiento:** al completar un ítem, moverlo a la tabla de completados de
`DOCUMENTACION.md` (sección 13) con fecha, y registrar la sesión en `BITACORA.md`.
