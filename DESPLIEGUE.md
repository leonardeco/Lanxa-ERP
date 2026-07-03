# Checklist de despliegue — PC Servidor

Guía operativa para actualizar el ERP en el PC servidor (modo `start.bat` + SQLite).
Tiempo estimado: 15-20 minutos. Hacerlo fuera del horario de uso (los 4 PCs cliente
pierden conexión durante la actualización).

---

## Antes de empezar (una sola vez por actualización)

- [ ] **Backup manual previo** (además del automático de las 2:00am):
  ```bat
  cd backend
  venv\Scripts\python.exe scripts\backup_db.py
  ```
- [ ] Verificar que existe el backup del día en `C:\SuperOzono-Backups`
- [ ] Copiar la carpeta de backups (y `BACKUP_ENCRYPTION_KEY` en un gestor de
  contraseñas) a un destino **fuera de este PC** — sin esto, un daño de disco
  pierde BD + backups juntos

## Actualizar el código

- [ ] Cerrar el ERP: doble clic en `stop.bat`
- [ ] Traer los cambios:
  ```bat
  git pull origin main
  ```

## Actualizar dependencias (solo si cambió `requirements.txt` / `package-lock.json`)

- [ ] Backend:
  ```bat
  cd backend
  venv\Scripts\python.exe -m pip install -r requirements.txt
  ```
- [ ] Frontend:
  ```bat
  cd frontend
  npm ci
  ```

## Actualizar el archivo `.env` del servidor (si esta actualización lo requiere)

- [ ] **Actualización de julio 2026**: renombrar en `backend\.env`:
  `ACCESS_TOKEN_EXPIRE_HOURS=1` → `ACCESS_TOKEN_EXPIRE_MINUTES=15`
- [ ] Nunca poner `CORS_ORIGINS=*` (con `DEBUG=false` la app no arranca a propósito)

## Migraciones de base de datos

- [ ] Primera vez que se despliega con Alembic (**solo una vez**):
  ```bat
  cd backend
  venv\Scripts\python.exe -m alembic stamp 99c028642b89
  ```
- [ ] En cada actualización:
  ```bat
  venv\Scripts\python.exe -m alembic upgrade head
  ```

## Arrancar y verificar

- [ ] Doble clic en `start.bat`
- [ ] Abrir `https://localhost:5173` → login OK
- [ ] Verificar `https://localhost:8000/health` → `{"status": "ok"}`
- [ ] Desde un PC cliente: abrir la app y hacer login
- [ ] Revisar el Dashboard (las alertas de cartera y stats cargan)

## Si algo sale mal — rollback

- [ ] `stop.bat`
- [ ] Volver al código anterior: `git log --oneline -5` y `git checkout <commit-anterior>`
- [ ] Si la BD quedó dañada, restaurar el backup:
  ```bat
  cd backend
  venv\Scripts\python.exe scripts\restore_db.py C:\SuperOzono-Backups\superozono_<fecha>.db.enc
  ```
  (el script guarda una copia `.bak-<fecha>` de la BD actual antes de sobreescribir)
- [ ] `start.bat` y verificar login

> **Procedimiento de restore verificado el 2026-07-02**: backup → BD destruida →
> restore → contenido idéntico (mismas tablas y filas). El script funciona.

---

## Tareas programadas que deben existir en este PC

| Tarea | Programación | Comando |
|---|---|---|
| `SuperOzonoERP-BackupDB` | Diario 2:00am | `backend\venv\Scripts\python.exe backend\scripts\backup_db.py` |

## Contactos / referencias

- Guía técnica completa: `DOCUMENTACION.md`
- Certificado CA para PCs cliente nuevos: `certs/superozono-ca.crt` (instalar como
  entidad de confianza — ver DOCUMENTACION.md sección 6)
- Mapeo contable pendiente de validar: `MAPEO-PUC-PARA-CONTADOR.md`
