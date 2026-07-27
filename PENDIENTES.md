# Pendientes — Super Ozono ERP

Backlog vivo del proyecto. Actualizado: **27 de julio de 2026** (48ª revisión).

**Resumen de la jornada 2026-07-27:** Merge + push a `main` de dos ramas grandes: **auditoría de aislamiento cross-tenant** (`fix-cross-tenant-audit`, 8 commits, 394/394 tests) y pulido de **README/DOCUMENTACION** (versiones de stack, módulos faltantes, roadmap sincronizado). Se avanzó también la rama **login por dominio de email** (`fix-login-tenant-domain`, 405/405 tests, actualizada contra el `main` nuevo) — **queda para mañana:** confirmar que el dominio elegido para Perú (`superozonoperu.com`, elegido por Claude a falta de decisión del negocio) es correcto, la prueba visual en navegador (bloqueada por la extensión Chrome sin conectar), y la decisión de merge. Ver tabla "Snapshot" abajo y `BITACORA.md` sesión de hoy para el detalle completo.

**Resumen de la jornada 2026-07-23:** Carril **Perú (Run 6)** — tenant separado + módulo `Ventas Diarias` + importador del histórico Excel, en rama `run6-peru-ventas-diarias`. ✅ **Mergeada 2026-07-24** (tenant Perú onboardeado en producción real ese mismo día). Llegó Excel de Ecuador (`CUENTAS ECUADOR.xlsx`) — revisado, estructura distinta a Perú, queda para un Run aparte. Fuente: `BITACORA.md` sesión 23-jul + `docs/hydraia/plans/2026-07-23-run6-peru-tenant-ventas-diarias*.md`.

**Resumen de la jornada 2026-07-21:** Carril **gerencial / documentación / preparación Contador** (sin cambios de negocio en código). Entregables en Escritorio: informe gerencial Word (línea de tiempo real + estimación de mercado), presentación PPTX 12 slides, acta de validación contable (Word+PDF) con 7 decisiones, resumen de jornada para área administrativa (PDF). Verificado backlog abierto. Solicitado a admin (próximo): Excel de inventario/cuentas/precios + capturas del ERP actual de auxiliares. Fuente: `BITACORA.md` sesión 21-jul + `DOCUMENTACION.md` §13 #59–#61.

**Fuente única de pendientes:** este archivo. Completados → `DOCUMENTACION.md` §13 + `BITACORA.md`.

Estado: LAN **v0.3.0** operativa. Suite API (Postgres local) + Vitest + E2E (CI informativo). Material Contador listo para reunión (acta imprimible).

---

## 🔴 Bloqueados por el negocio / Contador (no inventar en código)

| # | Pendiente | Quién | Notas |
|---|---|---|---|
| 1 | **Validar el mapeo PUC** del motor contable | Contador | Paquete listo: [`MAPEO-PUC-PARA-CONTADOR.md`](./MAPEO-PUC-PARA-CONTADOR.md), `ops/INSTRUCCIONES-REUNION-CONTADOR.md`, Escritorio `Entrega-Contador-PUC\`. **Acta 2026-07-21:** `Acta-Validacion-Contador-PUC-SuperOzono.pdf` (7 decisiones + firmas). **Falta:** reunión + respuestas por escrito firmadas |
| 2 | **Datos maestros reales**: PUC definitivo, inventario inicial, saldos de apertura | Contador + empresa | Importador de inventario listo. **Pedir a admin:** Excel con inventario, productos, precios, clientes/proveedores, PUC y saldos (si existen). Asiento de apertura depende de #3 |
| 3 | Definir **método de costeo** (promedio ponderado recomendado) | Contador | Prerrequisito del #8 · pregunta #6 del acta |
| 4 | Flags **`retiene_*`** en clientes retenedores | Contador + Superusuario | ✅ UVT 52374 + UI filtro/CSV + plantilla/import. **Queda:** rellenar con datos reales (acta #5 + Excel) |
| 8 | **Asiento de costo de venta** (DB 6135 / CR 1435 al confirmar venta) | Dev (tras #3) | Sin esto el P&L muestra ingresos, no margen · pregunta #7 del acta |
| 24 | Política de redondeo de retenciones | Contador elige; dev listo | ✅ `RETENCION_REDONDEO=half_even\|half_up` + `core/money.py` |

---

## 🟠 Operativo (Superusuario del PC servidor)

| # | Pendiente | Estado |
|---|---|---|
| 5 | Backup offsite + `BACKUP_ENCRYPTION_KEY` | ✅ Cerrado 2026-07-17 (offsite + sin plaintext). Residual opcional: gestor personal |
| 6 | Desplegar / mantener v0.3.0 en este servidor | ✅ Operativo. **IP actual LAN: `192.168.1.131`**. Ver `ops/ESTADO-OPERATIVO-PC.md`. Arranque: `start.bat` (auto-sync IP + certs relativos) |
| 7 | Entregar manual + contraseñas a usuarios | 📋 **Listo GO (2026-07-18):** preflight OK + IP .131 + `ops/HOY-ENTREGA-7.md` + Escritorio. **Falta:** repartir tarjetas (humano) |
| 7a | Drill de restore trimestral | ✅ Calendarizado **2026-10-15** |
| 7b | Vigencia certificado TLS | ✅ Documentado; cert regenerado con IP `.131` + localhost (CA local) |
| 27 | Revisar job E2E del CI en cada release | Abierto informativo (`continue-on-error`) |
| 33op | Rotar clave Superusuario en UI | Opcional |
| smoke | Smoke diario | ✅ `ops/smoke-diario.bat` + tarea **SuperOzonoERP-SmokeDiario** 08:00. Verificado login Superusuario |
| 36 | **Tarea 6 Run Perú — alta real del tenant** | ✅ **Completado 2026-07-24**: tenant Perú (`codigo="peru"`) onboardeado en producción real, admin `auxiliar.peru@superozonoglobal.com` |
| 37 | **Confirmar dominio de email de Perú** | 🟡 **Dejado para mañana.** El login ahora resuelve el tenant por dominio de email (rama `fix-login-tenant-domain`) — Perú compartía el dominio de Colombia (`superozonoglobal.com`), lo cual rompía el diseño. Se eligió `superozonoperu.com` **sin confirmación del negocio** (a pedido explícito: "solucionalo a tu manera"). **Falta:** verificar que ese dominio es correcto antes de desplegar; si no, es un cambio de una línea en la migración `d2e3f4a5b6c7`. También hay que avisarle a la persona real detrás de `auxiliar.peru@` que su email de login cambia |
| 38 | **Prueba en navegador — login por dominio** | 🟡 **Dejado para mañana.** La extensión Claude in Chrome no conectó pese a reinstalar y reiniciar Chrome varias veces (incl. matar todos los procesos). Login verificado por API/curl, no visualmente en `LoginView.tsx` |
| 39 | **Decisión de merge — `fix-login-tenant-domain`** | 🟡 **Dejado para mañana.** 405/405 tests, ya actualizada contra `main`. Depende de #37 y #38 |
| 40 | **Migración de `UniqueConstraint`s globales a compuestos con `tenant_id`** | 🟡 Hallazgo de la auditoría cross-tenant (`xfail` documentado en `test_contabilidad_tenant_isolation.py`): `PlanCuentas.codigo_puc`, `CentroCosto.codigo`, `PeriodoContable.periodo`, `Tercero.nit_cc`, etc. son únicos globalmente, no por tenant — bloquea a un tercer tenant usar `contabilidad` directamente. Requiere migración Alembic aparte (toca índices de producción en vivo, más riesgosa que un fix de queries) |

---

## 🟡 Técnico — deuda (dev)

| # | Pendiente | Estado |
|---|---|---|
| 10 | Drift Alembic | ✅ CI `alembic check` |
| 12 / 12a | Locks + numeración | ✅ 2026-07-15 |
| 13 | Servicios dominio ventas | ✅ |
| 14a | Puente Tercero | ✅ (unificación FK opcional) |
| 14a-bis | Roles negocio | ✅ |
| env-ip | Encoding `.env` + IP LAN | ✅ 2026-07-17 — UTF-8 + `ops/sync-lan-ip.ps1` en `start.bat` |
| tests-pg | Suite local Postgres | ✅ guía `ops/TESTES-LOCAL-POSTGRES.md` + `run-tests.ps1` + fixes tests |
| ops-lan-18 | Ops/seguridad/backup/login sin Contador | ✅ 2026-07-18 — ver `ops/BACKLOG-TECNICO-SIN-NEGOCIO.md` + DOCUMENTACION §13 #57–#58 |
| start-paths | start.bat paths con espacios | ✅ 2026-07-18 — `/D` + certs `..\certs\...` |
| backup-auto | Un solo job SQLite/Postgres | ✅ 2026-07-18 — `scripts/backup_auto.py` |
| docs-gerencial-21 | Informe gerencial + PPTX + acta Contador + resumen admin | ✅ 2026-07-21 — ver DOCUMENTACION §13 #59–#61 |
| run6-peru | Tenant Perú + módulo Ventas Diarias + importador Excel | ✅ **Mergeado 2026-07-24** (`run6-peru-ventas-diarias` → `main`). Bug preexistente no relacionado documentado (migración `c4d5e6f7a8b9` falla en Postgres desde cero — no afecta LAN/SQLite) |
| cross-tenant-audit | Auditoría de aislamiento cross-tenant (8 módulos/archivos) | ✅ **Mergeado y pusheado 2026-07-27** (`fix-cross-tenant-audit` → `main`). Suite completa 394/394 (+1 xfail, ver #40) |
| login-tenant-domain | Login resuelve tenant por dominio de email (evita ambigüedad entre tenants) | 🟡 **No mergeado, dejado para mañana** — ver #37/#38/#39 |

---

## 🟢 Funcional — features siguientes (por negocio)

| # | Feature | Notas |
|---|---|---|
| 18 | RRHH y nómina (Fase 2) | Requiere definiciones de negocio |
| 20 | Alegra + FE DIAN | ✅ Checklist + status + smoke. **Falta:** token real (`ops/ACTIVAR-ALEGRA-DIAN.md`) |
| 21 | Electron | ✅ **DESCARTADO** 2026-07-17 |
| 21a | Staging LAN | ✅ |
| 21b | Multi-bodega | ✅ **NO en v0.3** |
| 34 | **Insumos datos (Excel empresa)** | 📋 **Solicitado 2026-07-21:** inventario, productos, precios, clientes/proveedores, PUC, saldos. Alimenta #2/#4 |
| 35 | **Referencia UX ERP actual** | 📋 **Solicitado 2026-07-21:** carpeta de screenshots (o video corto) del ERP que pagan y usan las auxiliares — adaptar flujos/pantallas (no clonar 1:1). Tras adopción básica |

---

## ⚖️ Cumplimiento Colombia (con FE)

| # | Pendiente | Notas |
|---|---|---|
| 22 | DIAN en factura impresa | ✅ Infra; **falta** resolución real en `.env` |
| 23 | Habeas Data | ✅ Infra UI/BD; **falta** validar texto legal |

---

## 🔵 Nice-to-have

- ~~Seeder demo~~ · ~~Tests print~~ · ~~Token memoria~~ · ~~Política contraseñas~~ · ~~PyJWT~~ · ~~Login UX API caída~~ · ~~config APP_VERSION tests~~ ✅
- `APP_VERSION` alinear en cada release (`backend` config.py + `frontend` config.ts); preflight avisa mismatch

---

## Snapshot: qué queda realmente abierto

| Prioridad | Ítems |
|---|---|
| **Mañana — login por dominio (rama sin mergear)** | #37 confirmar dominio de Perú (`superozonoperu.com`, sin verificar) · #38 prueba en navegador (extensión Chrome sin conectar) · #39 decisión de merge |
| **Cuando quieras** | #40 migración `UniqueConstraint` compuesto en `contabilidad` (schema, riesgo medio) |
| **Mañana / Contador** | #1 acta firmada · #3 costeo · #8 aprobación · #4 criterio retenedores |
| **Listo para ti (#7)** | `ops\preflight-entrega-7.bat` + `HOY-ENTREGA-7.md` + Escritorio — **solo falta repartir** |
| **Pedir a administración** | #34 Excel datos reales · #35 screenshots ERP actual |
| **Cuando haya Contador + datos** | #2 maestros/inventario · #8 dev implementa tras #3 |
| **Cuando haya negocio** | #20 token Alegra; #22 resolución DIAN; #23 texto Habeas; #18 nómina |
| **Cuando quieras (1 min)** | Clave backup en gestor (#5 residual); #33op rotar Superusuario |
| **Calendario** | #7a drill restore **2026-10-15** |
| **Cloud** | Docker Desktop / `terraform apply` (código listo) |
| **Ops diarias** | smoke · diagnostico · SEGURIDAD-LAN · readiness · `BACKLOG-TECNICO-SIN-NEGOCIO.md` |
| **Técnico menor (sin Contador)** | E2E CI #27; registrar tarea `backup_auto` en Programador Windows |

**URL LAN actual:** `https://192.168.1.131:5173` (si cambia la IP: `start.bat` o `ops\sync-lan-ip.ps1`).

**Material Contador (Escritorio):** `Entrega-Contador-PUC\` · `Acta-Validacion-Contador-PUC-SuperOzono.pdf` · informe `Linea-de-Tiempo-Desarrollo-SuperOzono-ERP.docx` · PPTX gerencial · `Resumen-Jornada-Administrativa-SuperOzono.pdf`.

**Regla:** al completar un ítem, moverlo a `DOCUMENTACION.md` §13 y registrar en `BITACORA.md`.
