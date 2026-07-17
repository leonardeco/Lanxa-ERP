# Pendientes — Super Ozono ERP

Backlog vivo del proyecto. Actualizado: **17 de julio de 2026** (35ª revisión).

**Resumen de la sesión 2026-07-17:** Cierre ops **#5** + sync docs (34ª). Luego **#4 parcial:** `UVT_VALOR` default **52374** (DIAN Res. 000238/2025). Siguen con Contador: flags `retiene_*`, PUC #1, costeo #3→#8. **#7 entrega de contraseñas sigue aplazada.**

**Fuente única de pendientes:** este archivo. Completados → `DOCUMENTACION.md` §13 + `BITACORA.md`.

Estado: suite API + Vitest + E2E (local/CI). Versión LAN **v0.3.0**.

---

## 🔴 Bloqueados por el negocio / Contador (no inventar en código)

| # | Pendiente | Quién | Notas |
|---|---|---|---|
| 1 | **Validar el mapeo PUC** del motor contable | Contador | Paquete listo: [`MAPEO-PUC-PARA-CONTADOR.md`](./MAPEO-PUC-PARA-CONTADOR.md), `ops/INSTRUCCIONES-REUNION-CONTADOR.md`, Escritorio `Entrega-Contador-PUC\`. **Falta:** reunión + respuestas por escrito |
| 2 | **Datos maestros reales**: PUC definitivo, inventario inicial, saldos de apertura | Contador + empresa | Importador de inventario listo. Asiento de apertura depende de #3 |
| 3 | Definir **método de costeo** (promedio ponderado recomendado) | Contador | Prerrequisito del #8 |
| 4 | Flags **`retiene_*`** en clientes retenedores (+ revisar UVT en `.env` si se sobreescribe) | Contador | ✅ Default código **52374** (DIAN 2026). **Queda:** marcar en maestros qué clientes retienen fuente/IVA/ICA |
| 8 | **Asiento de costo de venta** (DB 6135 / CR 1435 al confirmar venta) | Dev (tras #3) | Sin esto el P&L muestra ingresos, no margen |
| 24 | Política de redondeo de retenciones | Contador | Hoy `round()` half-even de Python |

---

## 🟠 Operativo (Superusuario del PC servidor)

| # | Pendiente | Estado |
|---|---|---|
| 5 | Backup offsite + `BACKUP_ENCRYPTION_KEY` | ✅ **Cerrado 2026-07-17:** offsite OneDrive OK; clave solo en `backend\.env`; RECORDATORIO sin valor en claro. **Residual opcional:** confirmar copia en gestor personal |
| 6 | Desplegar v0.3.0 en este servidor | ✅ Hecho (health, Alembic, IP `192.168.1.48`, `start.bat`). Ver `ops/ESTADO-OPERATIVO-PC.md` |
| 7 | Entregar manual + contraseñas a usuarios | ⏸ **Aplazado (2026-07-15):** paquete listo en `Entrega-SuperOzono-v030` (7 tarjetas); no entregar hasta decisión del Superusuario |
| 7a | Drill de restore trimestral | ✅ Calendarizado **2026-10-15** (tarea Windows) |
| 7b | Vigencia certificado TLS | ✅ Documentado: expira **2028-10-17** |
| 27 | Revisar job E2E del CI en cada release | Abierto (informativo, `continue-on-error`) |
| 33op | Rotar clave Superusuario en UI | Clave ya no es de fábrica en `.env`. **Opcional:** cambiar otra vez desde Usuarios |

---

## 🟡 Técnico — deuda (dev)

| # | Pendiente | Estado |
|---|---|---|
| 10 | Drift Alembic legacy / nulabilidad | ✅ Blindado en CI (`alembic check`). BD local reconciliada |
| 12 | Locks stock/abonos | ✅ 2026-07-15 |
| 12a | Numeración concurrente-safe | ✅ 2026-07-15 |
| 13 | Servicios de dominio ventas | ✅ 2026-07-10 |
| 14a | Puente Cliente/Proveedor → Tercero | ✅ 2026-07-15 (unificación FK total queda opcional) |
| 14a-bis | Roles Superusuario/Directora/CEO/Aux. Contable | ✅ 2026-07-15 — migración `b1c2d3e4f5a6` + script `aplicar_estructura_usuarios.py` |
| docs | README / estado operativo desfasados | ✅ 2026-07-17 — lotes, roles, 7 usuarios, #5 |

---

## 🟢 Funcional — features siguientes (por negocio)

| # | Feature | Notas |
|---|---|---|
| 18 | RRHH y nómina (Fase 2) | Requiere definiciones de negocio |
| 20 | Alegra + facturación electrónica DIAN | Código mock listo; falta cuenta/token real |
| 21 | Empaquetado Electron | App .exe — candidato a descartar si SaaS web |
| 21a | Staging LAN | ✅ Docs+script listos (`ops/STAGING.md`) |
| 21b | ¿Multi-bodega? | Pregunta de negocio |

---

## ⚖️ Cumplimiento Colombia (con FE)

| # | Pendiente | Notas |
|---|---|---|
| 22 | Requisitos DIAN en factura impresa | Resolución de numeración autorizada |
| 23 | Habeas Data (Ley 1581) | Clientes persona natural |

---

## 🔵 Nice-to-have

- ~~Seeder demo~~ ✅ · ~~Tests print~~ ✅ · ~~Token en memoria~~ ✅ · ~~Política contraseñas~~ ✅ · ~~PyJWT~~ ✅
- `APP_VERSION` manual en `config.py` (alinear en cada release)
- Blacklist JTI en Redis — innecesario con access 15 min
- Mensajes login si API caída / rate limit — ✅ 2026-07-15 (`LoginView.tsx`)

---

## 🗺️ Roadmap estratégico enero 2027 (propuesto, no cerrado)

DIAN FE, nómina electrónica, documento soporte, exógena; producción por fórmula; multi-moneda; CRM; reórdenes; LAN vs cloud.

---

## Snapshot: qué queda realmente abierto

| Prioridad | Ítems |
|---|---|
| **Cuando quieras (1 min)** | Confirmar clave backup en gestor personal (residual #5); #33op rotar clave Superusuario |
| **Cuando haya Contador** | #1 → #2/#3 → #8 + #24; #4 flags `retiene_*` en clientes |
| **Cuando haya negocio/legal** | #20+#22, #18, #21, #21b, #23 |
| **Cuando digas** | #7 entregar accesos a los 7 usuarios |
| **Calendario** | #7a drill restore 2026-10-15 |
| **Cloud** | `terraform apply` / Docker Desktop (código listo) |

**Regla:** al completar un ítem, moverlo a `DOCUMENTACION.md` §13 y registrar en `BITACORA.md`.
