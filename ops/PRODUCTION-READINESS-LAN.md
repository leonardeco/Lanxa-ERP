# Production readiness — Super Ozono ERP (LAN v0.3.0)

Checklist del skill full-dev-team, adaptado a **servidor LAN** (no cloud).  
**Fecha:** 2026-07-17 · **IP:** `192.168.1.131`

## Codigo y calidad

| Check | Estado | Notas |
|---|---|---|
| Criterios de aceptacion del release | OK | v0.3.0 operativa; backlog Contador separado |
| Tests nivel adecuado | OK | Suite API + Vitest; E2E CI informativo |
| TODOs bloqueantes path critico | OK | Ninguno para login/ventas/compras/cartera |
| Logs sin secretos | OK | Auditoria + logs; secretos en `.env` |

## Datos y migraciones

| Check | Estado | Notas |
|---|---|---|
| Alembic | OK | Head en servidor; CI `alembic check` |
| Rollback schema | Parcial | Restore de backup SQLite cifrado |
| Seeds/admin | OK | Validator bloquea default en prod |
| Motor prod | SQLite | Postgres scripts de backup listos |

## Seguridad

| Check | Estado | Notas |
|---|---|---|
| AuthZ por roles | OK | Superusuario / Directora / CEO / Contador / Aux |
| Secretos en env | OK | No en Git |
| HTTPS LAN | OK | CA local + SAN IP actual |
| Puertos no expuestos a Internet | Responsabilidad ops | Ver `SEGURIDAD-LAN.md` |
| Backup cifrado + offsite | OK | Fernet + OneDrive; clave en gestor (humano) |
| Diagnostico | OK | `ops/diagnostico.ps1` |

## Operacion

| Check | Estado | Notas |
|---|---|---|
| Deploy | OK | `DESPLIEGUE.md` + `start.bat` / `stop.bat` |
| Health | OK | `/health` |
| Smoke diario | OK | Tarea 08:00 + `smoke-diario.bat` |
| Cert en clientes | Doc | `superozono-ca.crt` en paquete #7 |

## Observabilidad y soporte

| Check | Estado | Notas |
|---|---|---|
| Errores de usuario | OK | Login probe, ErrorState, mensajes start.bat |
| Auditoria | OK | Modulo activo |
| Post-arranque | Superusuario | Checklist go-live diario |

## Riesgos residuales (PO)

1. **#7** entrega humana de tarjetas pendiente.
2. **Contador** no valido PUC → P&L sin costo de venta (#8).
3. **Alegra** sin token → sin FE DIAN real.
4. Prod en **SQLite** (adecuado para LAN pequena; migrar a Postgres cuando crezcan).
5. Clave de backup debe estar en **gestor personal** (no solo .env).

## Comandos de verificacion

```bat
powershell -ExecutionPolicy Bypass -File ops\diagnostico.ps1
ops\smoke-diario.bat
```

```bat
cd backend
venv\Scripts\python.exe scripts\backup_db.py
```

## Cierre de esta revision

- [x] Docs de entrega y checklist con IP **.131**
- [x] Paquetes Escritorio actualizados
- [x] Guia `ops/SEGURIDAD-LAN.md`
- [x] Backup Postgres scripts (futuro)
- [ ] Smoke en caliente cuando el ERP este arrancado (`start.bat`)
