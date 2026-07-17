# Pendientes — Super Ozono ERP

Backlog vivo del proyecto. Actualizado: **17 de julio de 2026** (44ª revisión).

**Resumen de la jornada 2026-07-17:** Sin Contador se avanzó ops, tests Postgres, go-live, Alegra checklist, descarte Electron/multi-bodega, plan #7, smoke diario + tarea 08:00. **Fix crítico de arranque:** `.env` UTF-8 roto + IP LAN `192.168.1.48` → **`192.168.1.131`** (`start.bat` + `ops/sync-lan-ip.ps1`). **Verificado:** Superusuario entra por API y por UI (Playwright); usuario confirmó “ya estoy dentro”.

**Fuente única de pendientes:** este archivo. Completados → `DOCUMENTACION.md` §13 + `BITACORA.md`.

Estado: LAN **v0.3.0** operativa. Suite API (Postgres local) + Vitest + E2E (CI informativo).

---

## 🔴 Bloqueados por el negocio / Contador (no inventar en código)

| # | Pendiente | Quién | Notas |
|---|---|---|---|
| 1 | **Validar el mapeo PUC** del motor contable | Contador | Paquete listo: [`MAPEO-PUC-PARA-CONTADOR.md`](./MAPEO-PUC-PARA-CONTADOR.md), `ops/INSTRUCCIONES-REUNION-CONTADOR.md`, Escritorio `Entrega-Contador-PUC\`. **Falta:** reunión + respuestas por escrito |
| 2 | **Datos maestros reales**: PUC definitivo, inventario inicial, saldos de apertura | Contador + empresa | Importador de inventario listo. Asiento de apertura depende de #3 |
| 3 | Definir **método de costeo** (promedio ponderado recomendado) | Contador | Prerrequisito del #8 |
| 4 | Flags **`retiene_*`** en clientes retenedores | Contador + Superusuario | ✅ UVT 52374 + UI filtro/CSV + plantilla/import. **Queda:** rellenar con datos reales |
| 8 | **Asiento de costo de venta** (DB 6135 / CR 1435 al confirmar venta) | Dev (tras #3) | Sin esto el P&L muestra ingresos, no margen |
| 24 | Política de redondeo de retenciones | Contador elige; dev listo | ✅ `RETENCION_REDONDEO=half_even\|half_up` + `core/money.py` |

---

## 🟠 Operativo (Superusuario del PC servidor)

| # | Pendiente | Estado |
|---|---|---|
| 5 | Backup offsite + `BACKUP_ENCRYPTION_KEY` | ✅ Cerrado 2026-07-17 (offsite + sin plaintext). Residual opcional: gestor personal |
| 6 | Desplegar / mantener v0.3.0 en este servidor | ✅ Operativo. **IP actual LAN: `192.168.1.131`**. Ver `ops/ESTADO-OPERATIVO-PC.md`. Arranque: `start.bat` (auto-sync IP) |
| 7 | Entregar manual + contraseñas a usuarios | 📋 **Listo para ejecutar:** `ops/ENTREGA-7-USUARIOS.md` + Escritorio `Entrega-SuperOzono-v030\`. **Falta:** repartir tarjetas (humano) |
| 7a | Drill de restore trimestral | ✅ Calendarizado **2026-10-15** |
| 7b | Vigencia certificado TLS | ✅ Documentado; cert regenerado con IP `.131` + localhost (CA local) |
| 27 | Revisar job E2E del CI en cada release | Abierto informativo (`continue-on-error`) |
| 33op | Rotar clave Superusuario en UI | Opcional |
| smoke | Smoke diario | ✅ `ops/smoke-diario.bat` + tarea **SuperOzonoERP-SmokeDiario** 08:00. Verificado login Superusuario |

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

---

## 🟢 Funcional — features siguientes (por negocio)

| # | Feature | Notas |
|---|---|---|
| 18 | RRHH y nómina (Fase 2) | Requiere definiciones de negocio |
| 20 | Alegra + FE DIAN | ✅ Checklist + status + smoke. **Falta:** token real (`ops/ACTIVAR-ALEGRA-DIAN.md`) |
| 21 | Electron | ✅ **DESCARTADO** 2026-07-17 |
| 21a | Staging LAN | ✅ |
| 21b | Multi-bodega | ✅ **NO en v0.3** |

---

## ⚖️ Cumplimiento Colombia (con FE)

| # | Pendiente | Notas |
|---|---|---|
| 22 | DIAN en factura impresa | ✅ Infra; **falta** resolución real en `.env` |
| 23 | Habeas Data | ✅ Infra UI/BD; **falta** validar texto legal |

---

## 🔵 Nice-to-have

- ~~Seeder demo~~ · ~~Tests print~~ · ~~Token memoria~~ · ~~Política contraseñas~~ · ~~PyJWT~~ · ~~Login UX API caída~~ ✅
- `APP_VERSION` manual en `config.py` alinear en cada release

---

## Snapshot: qué queda realmente abierto

| Prioridad | Ítems |
|---|---|
| **Cuando quieras (1 min)** | Clave backup en gestor (#5 residual); #33op rotar Superusuario |
| **Listo para ti (#7)** | Paquete Escritorio IP **.131** actualizada — repartir 7 tarjetas (`ops/ENTREGA-7-USUARIOS.md`) |
| **Cuando haya Contador** | #1 → #2/#3 → #8; #4 flags reales; opcional #24 half_up |
| **Cuando haya negocio** | #20 token Alegra; #22 resolución DIAN; #23 texto Habeas; #18 nómina |
| **Calendario** | #7a drill restore **2026-10-15** |
| **Cloud** | Docker Desktop / `terraform apply` (código listo) |
| **Ops diarias** | smoke · diagnostico · `SEGURIDAD-LAN` · `PRODUCTION-READINESS-LAN` |

**URL LAN actual:** `https://192.168.1.131:5173` (si cambia la IP: `start.bat` o `ops\sync-lan-ip.ps1`).

**Regla:** al completar un ítem, moverlo a `DOCUMENTACION.md` §13 y registrar en `BITACORA.md`.
