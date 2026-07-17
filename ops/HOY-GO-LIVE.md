# Hoy — go-live usuarios (#7)

**Actualizado:** 2026-07-17  
**URL ERP:** https://192.168.1.48:5173  
**Paquete:** Escritorio → `Entrega-SuperOzono-v030\`  
**Guía completa:** [`ENTREGA-7-USUARIOS.md`](./ENTREGA-7-USUARIOS.md)

---

## A. #7 — Entregar usuarios y cambiar contraseñas

### Orden sugerido (30–45 min)

| # | Rol | Correo | Tarjeta |
|---|---|---|---|
| 1 | Superusuario | admin@superozonoglobal.com | `01-SUPERUSUARIO.txt` |
| 2 | Directora | directora@superozonoglobal.com | `02-DIRECTORA.txt` |
| 3 | CEO | ceo@superozonoglobal.com | `03-CEO.txt` |
| 4 | Contador | contador@superozonoglobal.com | `04-CONTADOR.txt` |
| 5 | Auxiliar Contable 1 | auxiliar1@superozonoglobal.com | `05-AUXILIAR1.txt` |
| 6 | Auxiliar Contable 2 | auxiliar2@superozonoglobal.com | `06-AUXILIAR2.txt` |
| 7 | Auxiliar Contable 3 | auxiliar3@superozonoglobal.com | `07-AUXILIAR3.txt` |

### Por cada persona

1. Entregar su tarjeta + `MANUAL-DE-USUARIO.md`.
2. En PCs cliente nuevos: instalar `superozono-ca.crt`  
   `certutil -user -addstore Root superozono-ca.crt`
3. Login → cambiar contraseña (mín. 8, letra + dígito).
4. Marcar en `CHECKLIST-CAMBIO-CLAVES.txt`.

### Al terminar los 7

- [ ] Borrar `CREDENCIALES-ESTRUCTURA-USUARIOS.txt` y `CREDENCIALES-TEMPORALES.txt`
- [ ] Borrar copia en `C:\SuperOzono-Backups\CREDENCIALES-*-NO-SUBIR.txt` si ya no hace falta
- [ ] Cerrar #7 en `PENDIENTES.md`

---

## B. #5 — Clave de cifrado de backups (cerrado 2026-07-17)

1. Offsite OneDrive: `SuperOzono-Backups-Offsite` — OK.
2. Valor de `BACKUP_ENCRYPTION_KEY` **solo** en `backend\.env` (no en texto plano en la carpeta de backups).
3. **Una vez (si aún no):** copiar la clave desde `backend\.env` al gestor personal (Bitwarden / 1Password).
4. `RECORDATORIO-CLAVE-BACKUP.txt` queda como nota **sin secreto**.

Sin esta clave, un `.db.enc` no se puede restaurar.

---

## C. #1 — Reunión Contador (PUC) — siguiente hilo

Paquete listo en Escritorio:

`Entrega-Contador-PUC\`

Contiene:

- `MAPEO-PUC-PARA-CONTADOR.md` — asientos actuales + preguntas
- `INSTRUCCIONES-REUNION.md` — cómo entrar y qué revisar en el ERP
- Acceso Contador: tarjeta `04-CONTADOR.txt` (misma carpeta de entrega general)

**Objetivo de la reunión:** validar o corregir códigos de cuenta (4135 vs 4120, Caja vs Bancos, compras a gasto, etc.).

Cuando el Contador devuelva respuestas, se implementan en código (#8 costo de venta depende también del método de costeo #3).

---

## ERP día a día

- Arrancar: acceso escritorio **Super Ozono ERP** (`start.bat`)
- Parar: `stop.bat`
- No cerrar las ventanas Backend / Frontend mientras se usa
