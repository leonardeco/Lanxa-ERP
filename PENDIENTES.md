# Pendientes — Super Ozono ERP

Backlog vivo del proyecto. Actualizado: **3 de agosto de 2026** (49ª revisión).

**Resumen de la jornada 2026-08-03:** Setup completo en PC nuevo (Python 3.14, venv, npm, migraciones, seed). Tres bloques entregados directamente a `main` con Hydraia: (1) **#40 drift Alembic** — migración `3deee189e9bd` con FKs nombradas a `tenants` + UniqueConstraints compuestos; `alembic check` en verde sin drift. (2) **#37/#38/#39 login por dominio** — feature reimplementado desde cero (la rama original `fix-login-tenant-domain` nunca fue pusheada al remote): campo `Tenant.dominio`, migración `4e24b843eccd` con backfill Colombia/Perú, router de login actualizado. (3) **start.bat auto-setup** — detecta Python 3.14, crea venv, instala deps, corre migraciones y seed automáticamente en el primer arranque. Pusheado a `origin/main` (`1417fc2..f3340bd`). **Queda**: confirmar dominio real de Perú (#37 técnicamente cerrado pero pendiente validación del negocio).

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
| 37 | **Confirmar dominio de email de Perú** | 🟡 **Técnicamente resuelto 2026-08-03** — feature implementado en `main` (migración `4e24b843eccd`). Dominio elegido: `superozonoperu.com`. **Queda:** validación por el negocio. Si no es correcto: `UPDATE tenants SET dominio = 'dominio-real.com' WHERE codigo = 'peru';` + notificar al usuario auxiliar.peru |
| 38 | **Prueba en navegador — login por dominio** | 🟡 **Pendiente** — login verificado por DB directamente (query OK). Probar visualmente en `https://192.168.20.108:5173` con `admin@superozonoglobal.com` / `superozonoglobal` |
| 39 | **Merge — `fix-login-tenant-domain`** | ✅ **Cerrado 2026-08-03** — feature reimplementado directamente en `main` (rama original nunca pusheada al remote). Commit `f3340bd`. |
| 40 | **Migración de `UniqueConstraint`s + FK tenants** | ✅ **Cerrado 2026-08-03** — migración `3deee189e9bd` aplicada. FKs nombradas, unique constraints compuestos, `alembic check` sin drift. |

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
| login-tenant-domain | Login resuelve tenant por dominio de email (evita ambigüedad entre tenants) | ✅ **Implementado directo en `main` 2026-08-03** — reimplementado desde cero (rama original no pusheada). Commit `f3340bd`. |

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
| **Validar con negocio** | #37 confirmar dominio real de Perú (`superozonoperu.com`, sin verificar) |
| **Cuando quieras** | #38 prueba visual en navegador (`https://192.168.20.108:5173`) |
| ~~#39 merge login-domain~~ | ✅ Cerrado 2026-08-03 |
| ~~#40 UniqueConstraints~~ | ✅ Cerrado 2026-08-03 |
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
