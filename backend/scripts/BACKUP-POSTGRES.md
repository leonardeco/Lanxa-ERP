# Backup PostgreSQL — Super Ozono ERP

## Estado actual (LAN)

| Motor | Uso típico | Script diario |
|---|---|---|
| **SQLite** (`superozono.db`) | Producción LAN v0.3.0 | `backup_db.py` → `*.db.enc` |
| **PostgreSQL** | Tests locales / futuro prod | `backup_pg.py` → `*.dump.enc` |

Mientras `DATABASE_URL` sea SQLite, el backup **de producción** sigue siendo `backup_db.py`.  
Los scripts Postgres quedan listos para cuando migren o para respaldar una BD Postgres de prueba.

## Requisitos

1. Cliente PostgreSQL (`pg_dump` / `pg_restore`) — suele estar en:
   `C:\Program Files\PostgreSQL\17\bin\`
2. `BACKUP_ENCRYPTION_KEY` en `backend\.env` (misma clave Fernet que SQLite).
3. URL Postgres:
   - `DATABASE_URL=postgresql+asyncpg://user:pass@127.0.0.1:5432/superozono` **o**
   - `PG_BACKUP_DATABASE_URL=...` (si la app sigue en SQLite y quieres respaldar solo Postgres).

Opcional: `PG_DUMP` / `PG_RESTORE` con ruta absoluta al `.exe` si no está en PATH.

## Backup manual

```bat
cd backend
venv\Scripts\python.exe scripts\backup_pg.py
```

Con URL explícita (PowerShell):

```powershell
$env:PG_BACKUP_DATABASE_URL = "postgresql://user:pass@127.0.0.1:5432/superozono"
.\venv\Scripts\python.exe scripts\backup_pg.py
```

Salida: `C:\SuperOzono-Backups\superozono_pg_YYYY-MM-DD_HHMMSS.dump.enc`

## Restore

1. `stop.bat` (ERP detenido).
2. Confirmar URL destino en `.env` o `PG_BACKUP_DATABASE_URL`.
3. Ejecutar:

```bat
cd backend
venv\Scripts\python.exe scripts\restore_pg.py C:\SuperOzono-Backups\superozono_pg_AAAA-MM-DD_HHMMSS.dump.enc
```

4. `start.bat` + `ops\smoke-diario.bat`

## Tarea programada (opcional)

```powershell
powershell -ExecutionPolicy Bypass -File backend\scripts\registrar-backup-pg.ps1
```

Crea `SuperOzonoERP-BackupPG` (diario 02:05). Si no hay URL Postgres, la tarea falla de forma visible en el historial del Programador — solo actívala cuando uses Postgres de verdad.

## Offsite

`copy_backups_offsite.ps1` ya copia todos los `*.enc` (incluye `superozono_pg_*.dump.enc`).

## Seguridad

- No exponer el puerto **5432** a Internet.
- No copiar `.env` a OneDrive.
- Guardar `BACKUP_ENCRYPTION_KEY` en gestor de contraseñas.
- Ver también: `ops/SEGURIDAD-LAN.md`
