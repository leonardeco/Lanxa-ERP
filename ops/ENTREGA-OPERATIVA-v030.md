# Entrega operativa v0.3.0 — Super Ozono ERP

Checklist del administrador del PC servidor. Completar fuera de horario si afecta a los PCs cliente.

**Estado del sistema (2026-07-15 en este servidor):**  
Ver también el snapshot vivo [`ESTADO-OPERATIVO-PC.md`](./ESTADO-OPERATIVO-PC.md).

| Check | Estado |
|---|---|
| Código `main` + health `v0.3.0` | Hecho (reinicio con último código 2026-07-15) |
| Migraciones Alembic en head | Hecho (`a0b1c2d3e4f5`) |
| Backup diario + offsite OneDrive | Hecho (backup + copia offsite 15:28) |
| Smoke login admin | Hecho (`ops/smoke-prod.py`) |
| Staging LAN preparado | Hecho (`setup-staging.ps1` → BD + `.env.staging`) |
| Admin sin clave de fábrica `Admin2026!` | Hecho (rotada; cada usuario debe cambiar en UI) |
| Usuarios en BD | **4 activos** (Admin + Administradora + Contador + Auxiliar) |

---

## #7 — Manual y contraseñas (4 usuarios)

### A. Usuarios en el sistema (creados 2026-07-15)

| # | Nombre | Correo | Rol | Temp password | Cambió clave |
|---|---|---|---|---|---|
| 1 | Administrador del Sistema | admin@superozonoglobal.com | Admin | ver `01-ADMIN.txt` o `backend\.env` | [ ] en UI |
| 2 | Administradora Operativa | administradora@superozonoglobal.com | Administradora | ver `02-ADMINISTRADORA.txt` | [ ] |
| 3 | Contador / Area Contable | contador@superozonoglobal.com | Contador | ver `03-CONTADOR.txt` | [ ] |
| 4 | Auxiliar Comercial | auxiliar@superozonoglobal.com | Auxiliar | ver `04-AUXILIAR.txt` | [ ] |

**Paquete de entrega listo (2026-07-15, go-live #7):**

| Ubicación | Contenido |
|---|---|
| Escritorio | `Entrega-SuperOzono-v030\` |
| OneDrive | `SuperOzono-Entrega\` |
| Servidor | `C:\SuperOzono-Backups\CREDENCIALES-TEMPORALES-NO-SUBIR.txt` |

Incluye: `INICIO.txt`, `01`–`04` tarjetas por usuario, `CHECKLIST-CAMBIO-CLAVES.txt`, manual, CA, credenciales maestras.

Si los nombres/correos reales de la empresa son otros: Admin → Usuarios & Accesos → editar o recrear; luego actualizar esta tabla.

Pasos de entrega por usuario:

1. Entregar **tarjeta `0N-….txt`** + `MANUAL-DE-USUARIO.md` + URL.
2. Usuario entra y **cambia la contraseña** (Usuarios & Accesos → Cambiar mi contraseña).
3. Marcar en `CHECKLIST-CAMBIO-CLAVES.txt` y en la tabla de arriba.
4. Cuando los 4 hayan cambiado: **borrar** los archivos `CREDENCIALES-TEMPORALES*` y las tarjetas `01`–`04` si ya no hacen falta.

### B. Entregar el manual

Archivo: [`MANUAL-DE-USUARIO.md`](../MANUAL-DE-USUARIO.md)

Copias listas para entregar (generadas en el servidor):

- Escritorio del admin: carpeta `Entrega-SuperOzono-v030\`
- OneDrive: `OneDrive\SuperOzono-Entrega\`

Marcar:

- [ ] Usuario 1 recibió manual + tarjeta + URL/acceso
- [ ] Usuario 2 recibió manual + tarjeta + URL/acceso
- [ ] Usuario 3 recibió manual + tarjeta + URL/acceso
- [ ] Usuario 4 recibió manual + tarjeta + URL/acceso
- [ ] Cada uno confirmó que puede entrar y ve los módulos de su rol

### C. URL y acceso cliente

| Dato | Valor actual |
|---|---|
| App | `https://192.168.1.48:5173` |
| API | `https://192.168.1.48:8000` |
| Acceso directo servidor | Escritorio → **Super Ozono ERP** (`start.bat`) |
| CA en PCs cliente nuevos | `certs\superozono-ca.crt` → `certutil -user -addstore Root certs\superozono-ca.crt` |

---

## #7a — Drill de restore trimestral

**Objetivo:** probar que un backup `.enc` se puede restaurar (no solo “existe el archivo”).

| Campo | Valor |
|---|---|
| Frecuencia | Cada 3 meses |
| Tarea Windows | `SuperOzonoERP-RestoreDrillReminder` (abre checklist) |
| Procedimiento verificado | 2026-07-02 (backup → destroy → restore idéntico) |
| Próximo drill a ejecutar | **2026-10-15** (calendario) |

### Pasos del drill (fuera de horario)

1. Confirmar backup reciente en `C:\SuperOzono-Backups` **y** en OneDrive offsite.
2. `stop.bat`.
3. Copiar `backend\superozono.db` a `superozono.db.before-drill`.
4. Restaurar:
   ```bat
   cd backend
   venv\Scripts\python.exe scripts\restore_db.py C:\SuperOzono-Backups\superozono_FECHA.db.enc
   ```
5. `start.bat` → login → verificar un dato conocido (usuario, factura de prueba).
6. Si el drill fue en copia de prueba, restaurar `superozono.db.before-drill` y arrancar de nuevo.
7. Anotar fecha y resultado abajo.

| Fecha drill | Backup usado | Resultado | Quién |
|---|---|---|---|
| 2026-07-02 | (simulacro inicial) | OK | — |
| 2026-10-15 | | [ ] | |
| 2027-01-15 | | [ ] | |

---

## #7b — Certificado TLS

| Campo | Valor |
|---|---|
| Archivo | `certs\server.crt` |
| CN / SAN | `192.168.1.48`, `localhost`, `127.0.0.1` |
| Válido desde | 2026-07-15 (aprox.) |
| **Expira** | **2028-10-17** |
| CA (clientes) | `certs\superozono-ca.crt` (no regenerar a la ligera) |

**Regenerar servidor** (mantiene la CA; no hay que reinstalar CA en clientes):

```bat
cd backend
venv\Scripts\python.exe scripts\generate_tls_cert.py 192.168.1.48 localhost 127.0.0.1
```

Si cambia la IP del servidor: actualizar `frontend\.env` (`VITE_API_URL`), `backend\.env` (`CORS_ORIGINS`), regenerar cert con la IP nueva, y avisar a los 4 PCs.

---

## Cierre de esta entrega

- [x] Paquete de **7 usuarios** (Superusuario, Directora, CEO, Contador, 3 Aux. Contable) — tarjetas en Escritorio
- [ ] Claves **cambiadas en UI** por cada persona (humano) — ver `ops/HOY-GO-LIVE.md`
- [ ] Manual entregado en mano a cada persona (humano)
- [ ] `BACKUP_ENCRYPTION_KEY` en gestor de contraseñas — `C:\SuperOzono-Backups\RECORDATORIO-CLAVE-BACKUP.txt`
- [x] Confirmado OneDrive `SuperOzono-Backups-Offsite` (backup 2026-07-15 15:55)
- [x] Recordatorio de drill 2026-10-15 (tarea Windows + ENTREGA)
- [x] Paquete Contador #1 PUC en Escritorio `Entrega-Contador-PUC\`

**Al terminar:** mover ítems cerrados a `DOCUMENTACION.md` §13 y una línea en `BITACORA.md`.
