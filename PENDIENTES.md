# Pendientes — Super Ozono ERP

Backlog vivo del proyecto. Actualizado: **23 de julio de 2026** (47ª revisión).

**Resumen de la jornada 2026-07-23:** Carril **Perú (Run 6)** — tenant separado + módulo `Ventas Diarias` + importador del histórico Excel, en rama `run6-peru-ventas-diarias` (no mergeada). Tareas 1–5 y 7–8 completas y revisadas; **Tarea 6** (alta real del tenant en producción) pausada por falta de la clave del Superusuario; **Tarea 9** (E2E navegador) interrumpida a medias. Llegó Excel de Ecuador (`CUENTAS ECUADOR.xlsx`) — revisado, estructura distinta a Perú, queda para un Run aparte. Fuente: `BITACORA.md` sesión 23-jul + `docs/hydraia/plans/2026-07-23-run6-peru-tenant-ventas-diarias*.md`.

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
| 36 | **Tarea 6 Run Perú — alta real del tenant** | 🔴 **Bloqueado:** necesita la clave real de `admin@superozonoglobal.com` (no se encontró en esta sesión). Pasos listos en el plan (`docs/hydraia/plans/2026-07-23-run6-peru-tenant-ventas-diarias-plan.md`, Tarea 6): onboard vía API + ajustar rol + verificar login + registrar en BITACORA |

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
| run6-peru | Tenant Perú + módulo Ventas Diarias + importador Excel | 🟡 Rama `run6-peru-ventas-diarias` (no mergeada): Tareas 1–5, 7–8 ✅ revisadas. **Falta:** Tarea 6 (bloqueada, #36) + Tarea 9 (E2E interrumpida, retomar) + revisión final de rama + decisión de merge. Bug preexistente no relacionado encontrado (migración `c4d5e6f7a8b9` falla en Postgres desde cero — no afecta LAN/SQLite) |

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
| **Run Perú (rama sin mergear)** | #36 clave Superusuario para Tarea 6 · retomar Tarea 9 (E2E) · revisión final + merge de `run6-peru-ventas-diarias` |
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
