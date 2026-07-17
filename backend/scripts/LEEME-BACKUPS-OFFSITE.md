# Backups offsite (#5)

## Qué protege

Los backups cifrados viven en `C:\SuperOzono-Backups`. Si solo están en el mismo disco
que la BD, un fallo de disco pierde **todo**. Hay que copiarlos a otro medio.

## Destino actual

Por defecto el script `copy_backups_offsite.ps1` copia a:

```text
%USERPROFILE%\OneDrive\SuperOzono-Backups-Offsite
```

OneDrive sincroniza a la nube (segundo sitio). Si hay USB/NAS, pasar `-Dest`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\copy_backups_offsite.ps1 -Dest "E:\SuperOzono-Backups"
```

## Clave de cifrado

Los `.enc` **no se pueden restaurar** sin `BACKUP_ENCRYPTION_KEY` del `backend\.env`.

- Guardar esa clave en un **gestor de contraseñas** (Bitwarden, 1Password, etc.).
- **Nunca** copiar el `.env` completo a OneDrive/USB sin control.
- **Nunca** dejar el valor de la clave en un `.txt` dentro de `C:\SuperOzono-Backups` (el offsite copiaría el secreto a OneDrive).
- Si existe `RECORDATORIO-CLAVE-BACKUP.txt`, debe ser solo una nota **sin** el valor (estado desde 2026-07-17).
- Sin la clave, los backups offsite no sirven.

## Tareas programadas

| Tarea | Cuándo | Qué hace |
|---|---|---|
| `SuperOzonoERP-BackupDB` | Diario 02:00 | Crea `.enc` en `C:\SuperOzono-Backups` |
| `SuperOzonoERP-BackupOffsite` | Diario 02:15 | Copia `.enc` a OneDrive (u otro `-Dest`) |
| `SuperOzonoERP-PurgaAuditoria` | Día 1, 03:00 | Archiva/purga log de auditoría (también cifra) |

## Restore (recordatorio)

```bat
cd backend
venv\Scripts\python.exe scripts\restore_db.py C:\SuperOzono-Backups\superozono_AAAA-MM-DD_HHMMSS.db.enc
```
