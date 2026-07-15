# Entrega operativa v0.3.0 — Super Ozono ERP

Checklist del administrador del PC servidor. Completar fuera de horario si afecta a los PCs cliente.

**Estado del sistema (2026-07-15 en este servidor):**

| Check | Estado |
|---|---|
| Código `main` + health `v0.3.0` | Hecho |
| Migraciones Alembic en head | Hecho |
| Backup diario + offsite OneDrive | Hecho |
| Admin sin clave de fábrica `Admin2026!` | Hecho (rotada; cambiar otra vez en UI) |
| Usuarios en BD | **Solo 1:** `admin@superozonoglobal.com` (Admin) |

---

## #7 — Manual y contraseñas (4 usuarios)

### A. Crear los usuarios que faltan

Hoy solo existe el Admin. Crear los otros desde **Usuarios & Accesos** (login Admin):

| # | Nombre sugerido | Correo (completar) | Rol | Temp password | Cambió clave |
|---|---|---|---|---|---|
| 1 | Administrador del Sistema | admin@superozonoglobal.com | Admin | (ya rotada en servidor) | [ ] en UI |
| 2 | | | Administradora / Contador / Auxiliar | | [ ] |
| 3 | | | | | [ ] |
| 4 | | | | | [ ] |

Pasos por usuario nuevo:

1. Admin → **Usuarios & Accesos → + Nuevo**.
2. Asignar rol correcto (ver manual).
3. Anotar contraseña temporal **fuera del chat/correo público** (papel o gestor).
4. Entregar acceso + manual (sección B).
5. Usuario entra y **cambia la contraseña**.
6. Marcar la fila.

### B. Entregar el manual

Archivo: [`MANUAL-DE-USUARIO.md`](../MANUAL-DE-USUARIO.md)

Copias listas para entregar (generadas en el servidor):

- Escritorio del admin: carpeta `Entrega-SuperOzono-v030\` (si se creó con el script de ops)
- OneDrive: `OneDrive\SuperOzono-Entrega\`

Marcar:

- [ ] Usuario 1 recibió manual + URL/acceso
- [ ] Usuario 2 recibió manual + URL/acceso
- [ ] Usuario 3 recibió manual + URL/acceso
- [ ] Usuario 4 recibió manual + URL/acceso
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

- [ ] Tabla de 4 usuarios completa y claves cambiadas
- [ ] Manual entregado
- [ ] `BACKUP_ENCRYPTION_KEY` en gestor de contraseñas
- [ ] Confirmado OneDrive sync de `SuperOzono-Backups-Offsite`
- [ ] Recordatorio de drill 2026-10-15 aceptado

**Al terminar:** mover ítems cerrados a `DOCUMENTACION.md` §13 y una línea en `BITACORA.md`.
