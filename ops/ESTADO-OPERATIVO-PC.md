# Estado operativo — este PC servidor

**Verificado:** 2026-07-17  
**Código:** `main` (v0.3.0 + cumplimiento DIAN/Habeas infra + tests Postgres local)

## Ahora mismo (producción LAN)

| Componente | Estado | Detalle |
|---|---|---|
| Backend | **ON** (si `start.bat` activo) | `https://192.168.1.48:8000` / health `v0.3.0` |
| Frontend | **ON** (si `start.bat` activo) | `https://192.168.1.48:5173` |
| Login Superusuario | **OK** | `admin@superozonoglobal.com` |
| BD SQLite | **OK** | `backend\superozono.db` — Alembic head `c6d7e8f9a0b1` (Habeas) |
| Usuarios | **7 activos** | Superusuario, Directora, CEO, Contador, Auxiliar×3 |
| IP LAN | `192.168.1.48` | Alineada con `frontend\.env` y cert SAN |
| CA confiable (este PC) | **OK** | instalada en almacén Root del usuario |
| Acceso escritorio | **OK** | `Super Ozono ERP.lnk` → `start.bat` |
| Postgres (solo tests) | **Running** | servicio `postgresql-x64-17`, BD `superozono_test` |
| Checklist diario | — | `ops\CHECKLIST-GO-LIVE-DIARIO.md` |
| Tests locales | — | `ops\TESTES-LOCAL-POSTGRES.md` + `ops\run-tests.ps1` |

## Backups (#5)

| Check | Estado |
|---|---|
| Carpeta local | `C:\SuperOzono-Backups` |
| Offsite OneDrive | `OneDrive\SuperOzono-Backups-Offsite` (sync) |
| Clave cifrado | En `backend\.env` (`BACKUP_ENCRYPTION_KEY`). **No** en texto plano en la carpeta de backups |
| RECORDATORIO | Solo nota sin secreto (2026-07-17) |
| Tarea `SuperOzonoERP-BackupDB` | Ready (diario 2:00) |
| Tarea `SuperOzonoERP-BackupOffsite` | Ready (diario 2:15) |
| Tarea purga auditoría | Ready |
| Recordatorio drill restore | Ready — **próximo drill: 2026-10-15** |

**Acción residual del Superusuario:** confirmar una vez que la clave también está en el gestor de contraseñas personal (Bitwarden / 1Password). Fuente: `backend\.env` — nunca WhatsApp/correo.

## Staging (listo, no corre 24/7)

| Artefacto | Ruta |
|---|---|
| Guía | `ops\STAGING.md` |
| Setup | `ops\setup-staging.ps1` (ya ejecutado: BD + `.env.staging`) |
| Arranque | `ops\start-staging.ps1` → API **8010**, UI **5180** |
| BD staging | `backend\superozono_staging.db` (copia de prod) |
| Smoke prod | `ops\smoke-prod.py` |

```powershell
# Preparar (una vez o al refrescar BD)
powershell -ExecutionPolicy Bypass -File ops\setup-staging.ps1
# Arrancar staging (prod puede seguir en 8000/5173)
powershell -ExecutionPolicy Bypass -File ops\start-staging.ps1
```

## TLS

| Campo | Valor |
|---|---|
| Expira | **2028-10-17** |
| SAN | `192.168.1.48`, `localhost`, `127.0.0.1` |
| CA clientes | `certs\superozono-ca.crt` (en carpeta Entrega del escritorio) |

## Cómo arrancar / parar (día a día)

1. Doble clic **Super Ozono ERP** en el escritorio (`start.bat`).
2. Para parar: `stop.bat` o cerrar ventanas Backend/Frontend.
3. Tras `git pull`: `stop.bat` → `DESPLIEGUE.md` (deps + `alembic upgrade head`) → `start.bat`.
4. Smoke diario (health + login + me + empresa + Alegra):  
   `ops\smoke-diario.bat`  
   o `backend\venv\Scripts\python.exe ops\smoke-prod.py`  
   Tarea opcional: `ops\registrar-smoke-diario.ps1`

## Entrega a personas (#7 — aplazada)

No se puede “automatizar” que cada usuario cambie su clave:

1. Carpeta escritorio: `Entrega-SuperOzono-v030\`  
   (manual + CA + credenciales temporales, 7 tarjetas).
2. Entregar a cada uno y marcar “Cambió clave” en `ops\ENTREGA-OPERATIVA-v030.md`.
3. Cuando los 7 cambien: borrar `CREDENCIALES-TEMPORALES*` y copias en `C:\SuperOzono-Backups\CREDENCIALES-*-NO-SUBIR.txt`.

## Lo que NO es de este PC

- Validación contable (#1–4, #8, #24) — Contador.
- AWS / Docker apply — sin Docker Desktop ni cuenta AWS en este equipo.
