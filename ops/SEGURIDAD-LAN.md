# Seguridad LAN — Super Ozono ERP

Checklist práctico para el PC servidor y la red de oficina.  
**Modelo:** app en LAN (HTTPS local) + BD en el mismo PC (SQLite hoy; Postgres listo).  
**No** abrir el ERP a Internet sin VPN.

---

## 1. Principios

1. **Solo LAN** — el ERP no se publica en el router (sin port-forward 8000/5173/5432).
2. **Secretos fuera de chats** — contraseñas y claves solo en gestor + `backend\.env`.
3. **Backup recuperable** — cifrado local + copia offsite; clave en gestor.
4. **Un usuario ERP por persona** — no compartir Superusuario en el día a día.
5. **Servidor aburrido** — Windows actualizado, sin descargas dudosas en ese PC.

---

## 2. PC servidor

| Acción | Detalle |
|---|---|
| Contraseña de Windows | Fuerte; bloqueo de pantalla automático |
| Actualizaciones | Windows Update al día |
| Antivirus | Activo (Windows Defender basta si está al día) |
| UPS | Recomendado (evita corrupción de BD al cortar luz) |
| BitLocker | Ideal si el PC es portátil o hay riesgo de robo |
| Uso del PC | Preferible dedicado al ERP; no “PC de todo el mundo” |
| Carpeta del proyecto | Solo administradores; no compartir `backend\.env` |

---

## 3. Red Wi‑Fi / router

| Acción | Detalle |
|---|---|
| Wi‑Fi | WPA2 o WPA3; contraseña distinta a la de fábrica |
| Invitados | Red de invitados separada; ERP solo en red de trabajo |
| Port forwarding | **Nunca** reenviar 8000, 5173 ni 5432 a Internet |
| Admin del router | Cambiar clave por defecto del panel del router |
| Remoto desde casa | **VPN** (Tailscale, WireGuard, VPN del router) — no “abrir puertos del ERP” |

---

## 4. Base de datos

### SQLite (producción LAN actual)

- Archivo: `backend\superozono.db`
- Backup: `backend\scripts\backup_db.py` → `C:\SuperOzono-Backups\*.db.enc`
- Tarea típica: `SuperOzonoERP-BackupDB` (02:00)

### PostgreSQL (tests / futuro prod)

- **No** escuchar en `0.0.0.0` expuesto a Internet; solo localhost o LAN confiable
- Contraseña de rol fuerte (no `postgres/postgres`)
- Backup: `backend\scripts\backup_pg.py` → `*.dump.enc` (ver `BACKUP-POSTGRES.md`)
- Puerto **5432** cerrado al WAN

---

## 5. Secretos y `.env`

| Variable | Cuidado |
|---|---|
| `SECRET_KEY` | Larga y única; no en Git |
| `BACKUP_ENCRYPTION_KEY` | Sin ella los `.enc` no se restauran; **gestor de contraseñas** |
| `SEED_ADMIN_PASSWORD` | No dejar la default del repo en producción |
| Alegra / DIAN | Solo cuando existan; no pegar tokens en WhatsApp |

- `.env` en **UTF-8** (si se rompe el encoding, `start.bat` / `ops\sync-lan-ip.ps1`)
- Nunca copiar `.env` completo a OneDrive “por si acaso”
- `RECORDATORIO-CLAVE-BACKUP.txt` solo nota **sin** el valor de la clave

---

## 6. HTTPS y clientes

1. En cada PC cliente (una vez): instalar `certs\superozono-ca.crt` como CA confiable.
2. Entrar solo por la URL LAN (`https://IP:5173`), no por HTTP.
3. Si cambia la IP: `start.bat` o `ops\sync-lan-ip.ps1` (regenera cert SAN).

---

## 7. Usuarios del ERP

- Crear usuarios con rol mínimo necesario (`ops/ENTREGA-7-USUARIOS.md`).
- Desactivar cuentas de quienes salen de la empresa.
- Rotar Superusuario cuando haya duda de filtración (`#33op`).
- Cerrar sesión en PCs compartidos.

---

## 8. Backups y recuperación

| Qué | Dónde |
|---|---|
| Local cifrado | `C:\SuperOzono-Backups\` |
| Offsite | OneDrive u otro (`copy_backups_offsite.ps1`) |
| SQLite restore | `scripts\restore_db.py ruta.db.enc` |
| Postgres restore | `scripts\restore_pg.py ruta.dump.enc` |
| Drill | Calendarizado (ver PENDIENTES #7a) |

Sin la clave Fernet del gestor, **el offsite no sirve**.

---

## 9. Rutinas

### Cada mañana (2–5 min)

```bat
ops\smoke-diario.bat
```

o checklist: `ops/CHECKLIST-GO-LIVE-DIARIO.md`

### Cuando algo “no abre”

```powershell
powershell -ExecutionPolicy Bypass -File ops\diagnostico.ps1
```

### Semanal (5 min)

- [ ] ¿Backup reciente en `C:\SuperOzono-Backups` (hoy o ayer)?
- [ ] ¿Offsite con archivos `.enc`?
- [ ] ¿Windows Update / antivirus OK en el servidor?
- [ ] ¿Usuarios que ya no trabajan siguen activos?
- [ ] ¿Router sin port-forward raro?

### Tras `git pull`

Seguir `DESPLIEGUE.md` (deps, migraciones, smoke).

---

## 10. Qué no hacer

- Abrir el ERP a Internet “solo un rato”
- Hosting compartido tipo GoDaddy para la BD del ERP
- Compartir Superusuario por chat
- Desactivar HTTPS “porque el certificado molesta”
- Guardar la clave de backup en la misma carpeta de backups en texto plano
- Confiar solo en un disco (servidor sin offsite)

---

## 11. Remoto seguro (cuando haga falta)

1. Instalar **Tailscale** (o VPN del router) en el PC servidor y en el portátil del contador/admin.
2. Entrar al ERP por la IP/hostname de la VPN, con el mismo HTTPS local.
3. No reenviar puertos en el router doméstico/oficina.

---

## Referencias en el repo

| Doc / script | Uso |
|---|---|
| `ops/diagnostico.ps1` | IP, UTF-8, puertos, cert, health, Postgres, backups |
| `ops/CHECKLIST-GO-LIVE-DIARIO.md` | Rutina diaria |
| `backend/scripts/LEEME-BACKUPS-OFFSITE.md` | Offsite + tareas |
| `backend/scripts/BACKUP-POSTGRES.md` | Backup/restore Postgres |
| `ops/ENTREGA-7-USUARIOS.md` | Usuarios y CA en clientes |
| `DESPLIEGUE.md` | Despliegue y tareas Windows |
