# Entrega operativa v0.3.0 — Super Ozono ERP

Checklist del Superusuario del PC servidor.

**Snapshot vivo:** [`ESTADO-OPERATIVO-PC.md`](./ESTADO-OPERATIVO-PC.md)  
**Plan de entrega de usuarios (#7):** [`ENTREGA-7-USUARIOS.md`](./ENTREGA-7-USUARIOS.md)  
**Día a día:** [`CHECKLIST-GO-LIVE-DIARIO.md`](./CHECKLIST-GO-LIVE-DIARIO.md)

---

## Estado del sistema

| Check | Estado |
|---|---|
| Código `main` + health `v0.3.0` | Hecho |
| Migraciones Alembic | Head reciente (`c6d7e8f9a0b1` Habeas; ver `alembic current`) |
| Backup diario + offsite OneDrive | Hecho |
| Smoke | `ops/smoke-prod.py` (health + login + me + empresa) |
| Staging LAN | `ops/STAGING.md` |
| Usuarios en BD | **7 cuentas** (estructura Superusuario / Directora / CEO / Contador / Aux×3) |
| Entrega de contraseñas (#7) | **Lista para ejecutar** — ver `ENTREGA-7-USUARIOS.md` |

---

## #7 — Manual y contraseñas (7 usuarios)

### Paquete

| Ubicación | Contenido |
|---|---|
| Escritorio | `Entrega-SuperOzono-v030\` (tarjetas 01–07, checklist, manual, CA) |
| Repo | `MANUAL-DE-USUARIO.md`, `ops/ENTREGA-7-USUARIOS.md` |

### Tabla de seguimiento

| # | Correo | Rol | Recibió paquete | Cambió clave | Entró OK |
|---|---|---|---|---|---|
| 1 | admin@superozonoglobal.com | Superusuario | [ ] | [ ] | [ ] |
| 2 | directora@superozonoglobal.com | Directora | [ ] | [ ] | [ ] |
| 3 | ceo@superozonoglobal.com | CEO | [ ] | [ ] | [ ] |
| 4 | contador@superozonoglobal.com | Contador | [ ] | [ ] | [ ] |
| 5 | auxiliar1@superozonoglobal.com | Auxiliar Contable | [ ] | [ ] | [ ] |
| 6 | auxiliar2@superozonoglobal.com | Auxiliar Contable | [ ] | [ ] | [ ] |
| 7 | auxiliar3@superozonoglobal.com | Auxiliar Contable | [ ] | [ ] | [ ] |

Cuando las 7 filas estén completas: borrar `CREDENCIALES-TEMPORALES*` y marcar #7 cerrado en `PENDIENTES.md`.

### URL y CA

| Dato | Valor |
|---|---|
| App | `https://192.168.1.48:5173` |
| API | `https://192.168.1.48:8000` |
| CA clientes | `certutil -user -addstore Root superozono-ca.crt` |

---

## #7a — Drill de restore

**Próximo:** 2026-10-15 (tarea Windows programada).  
Probar restore real de un `.enc` (no solo que exista el archivo).

## #5 — Backup

Offsite OK. Clave solo en `backend\.env` + gestor personal (no en txt de backups).

## Decisiones producto

Electron y multi-bodega: **cerrados** — ver `DECISIONES-PRODUCTO-SIN-CONTADOR.md`.
