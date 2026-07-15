# Checklist de despliegue — PC Servidor

Guía operativa para actualizar el ERP en el PC servidor (modo `start.bat` + SQLite).
Tiempo estimado: 15-20 minutos. Hacerlo fuera del horario de uso (los 4 PCs cliente
pierden conexión durante la actualización).

---

## Primer despliegue — go-live empresa #1 (una sola vez)

Pasos que solo se hacen en la **primera** puesta en marcha (después se usa el flujo de
actualización de abajo). Referencia: `docs/hydraia/plans/2026-07-14-roadmap-maestro-erp.md`
(Carril 0). ⚠️ **Verificar los datos de red contra la configuración real antes de ejecutar.**

**A. Red del servidor**
- [ ] Reserva DHCP en el router (`192.168.1.1`): atar MAC `D8-C0-A6-E6-84-4F` → IP fija
  `192.168.1.47` (para que la IP del servidor no cambie).
- [ ] `backend\.env`: `CORS_ORIGINS` incluye `https://192.168.1.47:5173`.
- [ ] `frontend\.env`: `VITE_API_URL=https://192.168.1.47:8000/api`.
- [ ] Cert `certs\server.crt` válido para `192.168.1.47` (vigente hasta oct-2028). Si la IP
  cambió: `venv\Scripts\python.exe scripts\generate_tls_cert.py <IP> localhost 127.0.0.1`.

**B. Servidor:** ejecutar el flujo de "Actualizar el código" → "Migraciones" de abajo
(incluye el `alembic stamp` de primera vez y el `SEED_ADMIN_PASSWORD` propio).

**C. Cada uno de los 4 PCs cliente (una vez):**
- [ ] Copiar `certs\superozono-ca.crt` e instalarla como confiable:
  `certutil -user -addstore Root certs\superozono-ca.crt`
- [ ] Abrir `https://192.168.1.47:5173` y hacer login.

**D. Entrega y operación:**
- [ ] El admin cambia su clave desde la UI tras el primer login.
- [ ] Entregar `MANUAL-DE-USUARIO.md` a los 4 usuarios; cada uno cambia su clave inicial.
- [ ] Documentar la fecha de expiración del cert TLS (oct-2028) y cuándo regenerarlo.
- [ ] Calendarizar el drill de restore trimestral.
- [ ] Confirmar las 2 tareas programadas (backup diario 2am, purga auditoría mensual).

**Checkpoint:** empresa #1 operando desde los 4 PCs cliente + backup copiado **fuera** del
servidor.

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
- [ ] **Desde v0.3.0 — `SEED_ADMIN_PASSWORD` obligatorio**: definir una clave propia
  en `backend\.env` (con `DEBUG=false` la app **no arranca** si se deja la clave por
  defecto del repo). El admin debe volver a cambiarla desde la UI tras el primer login.

## Migraciones de base de datos

- [ ] Primera vez que se despliega con Alembic (**solo una vez**):
  ```bat
  cd backend
  venv\Scripts\python.exe -m alembic stamp 99c028642b89
  ```
- [ ] En cada actualización (**obligatorio desde v0.3.0**):
  ```bat
  venv\Scripts\python.exe -m alembic upgrade head
  ```
  > Desde v0.3.0 el backend en producción (`DEBUG=false`) ya **no** crea tablas
  > al arrancar: el esquema lo gobierna únicamente Alembic. Si se omite este
  > paso tras actualizar, los módulos nuevos fallarán con "no such table".

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
| `SuperOzonoERP-BackupOffsite` | Diario 2:15am | `backend\scripts\copy_backups_offsite.ps1` → OneDrive (o USB/NAS con `-Dest`) |
| `SuperOzonoERP-PurgaAuditoria` | Mensual (día 1, 3:00am) | `backend\scripts\run_purge_auditoria.bat` |

Ver detalle offsite y clave de cifrado: `backend\scripts\LEEME-BACKUPS-OFFSITE.md` (pendiente #5).

> **Purga de auditoría (#28):** archiva y borra los registros del log de auditoría
> anteriores a `AUDITORIA_RETENTION_DAYS` (por defecto 1825 ≈ 5 años, editable en
> `.env`). Antes de borrar, exporta los registros **cifrados** a
> `C:\SuperOzono-Backups\auditoria\auditoria_purga_<fecha>.json.enc` — por eso
> **requiere `BACKUP_ENCRYPTION_KEY` definida** (si falta, aborta sin borrar nada).
> La propia purga queda registrada en el log de auditoría.

## Contactos / referencias

- Guía técnica completa: `DOCUMENTACION.md`
- Certificado CA para PCs cliente nuevos: `certs/superozono-ca.crt` (instalar como
  entidad de confianza — ver DOCUMENTACION.md sección 6)
- Mapeo contable pendiente de validar: `MAPEO-PUC-PARA-CONTADOR.md`
