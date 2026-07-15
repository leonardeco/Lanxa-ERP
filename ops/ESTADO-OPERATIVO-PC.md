# Estado operativo — este PC servidor

**Verificado:** 2026-07-15  
**Código:** `main` (incluye política de contraseñas + puente Tercero + docs staging)

## Ahora mismo (producción LAN)

| Componente | Estado | Detalle |
|---|---|---|
| Backend | **ON** | `https://192.168.1.48:8000` / health `v0.3.0` |
| Frontend | **ON** | `https://192.168.1.48:5173` |
| Login admin | **OK** | `admin@superozonoglobal.com` |
| BD SQLite | **OK** | `backend\superozono.db` — Alembic head `a0b1c2d3e4f5` |
| Usuarios | **4 activos** | Admin, Administradora, Contador, Auxiliar |
| IP LAN | `192.168.1.48` | Alineada con `frontend\.env` y cert SAN |
| CA confiable (este PC) | **OK** | instalada en almacén Root del usuario |
| Acceso escritorio | **OK** | `Super Ozono ERP.lnk` → `start.bat` |

## Backups

| Check | Estado |
|---|---|
| Carpeta local | `C:\SuperOzono-Backups` |
| Último backup (sesión) | `superozono_2026-07-15_152805.db.enc` |
| Offsite OneDrive | `OneDrive\SuperOzono-Backups-Offsite` (sync) |
| Tarea `SuperOzonoERP-BackupDB` | Ready (diario 2:00) |
| Tarea `SuperOzonoERP-BackupOffsite` | Ready (diario 2:15) |
| Tarea purga auditoría | Ready |
| Recordatorio drill restore | Ready — **próximo drill: 2026-10-15** |

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
4. Smoke rápido:  
   `backend\venv\Scripts\python.exe ops\smoke-prod.py`

## Entrega a personas (queda en tu mano)

No se puede “automatizar” que cada usuario cambie su clave:

1. Carpeta escritorio: `Entrega-SuperOzono-v030\`  
   (manual + CA + credenciales temporales).
2. Entregar a cada uno y marcar “Cambió clave” en `ops\ENTREGA-OPERATIVA-v030.md`.
3. Cuando los 4 cambien: borrar `CREDENCIALES-TEMPORALES*`.
4. Guardar `BACKUP_ENCRYPTION_KEY` (de `backend\.env`) en un gestor de contraseñas personal.

## Lo que NO es de este PC

- Validación contable (#1–4, #8) — contadora.
- AWS / Docker apply — sin Docker Desktop ni cuenta AWS en este equipo.
