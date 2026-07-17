# Checklist go-live diario — Super Ozono ERP (LAN)

**Sin Contador.** Operación del día a día en el PC servidor.

URL típica: `https://192.168.1.48:5173`  
API: `https://192.168.1.48:8000`  
Más detalle: `ops/ESTADO-OPERATIVO-PC.md`

---

## Cada mañana (2–5 min)

- [ ] Arrancar ERP: acceso escritorio **Super Ozono ERP** o `start.bat`
- [ ] Smoke diario (doble clic o consola):

```bat
ops\smoke-diario.bat
```

o:

```bat
backend\venv\Scripts\python.exe ops\smoke-prod.py
```

Esperado:
```
health: OK
login: OK
users/me: OK
ventas/empresa: OK
alegra: no configurado ...   (normal hasta poner token)
SMOKE: todo OK
```

Cuando tengas Alegra en `.env` y quieras exigir conexión:

```bat
backend\venv\Scripts\python.exe ops\smoke-prod.py --strict-alegra
```

- [ ] Abrir el navegador, login Superusuario (o tu usuario)
- [ ] Dashboard: ¿cargan números? ¿alertas de cartera legibles?

Si el smoke falla: `stop.bat` → esperar 5 s → `start.bat` → reintentar.

Diagnóstico completo (IP, .env UTF-8, puertos, cert, health):

```powershell
powershell -ExecutionPolicy Bypass -File ops\diagnostico.ps1
```

### Tarea programada (opcional)

```powershell
powershell -ExecutionPolicy Bypass -File ops\registrar-smoke-diario.ps1
```

Log: `%USERPROFILE%\SuperOzono-Smoke-Logs\smoke-latest.txt`

---

## Después de `git pull` (actualización)

1. `stop.bat`
2. Seguir `DESPLIEGUE.md` (deps + `alembic upgrade head`)
3. `start.bat`
4. `backend\venv\Scripts\python.exe ops\smoke-prod.py`
5. Probar una pantalla de Ventas y una de Cartera

Migración reciente de ejemplo: `c6d7e8f9a0b1` (Habeas Data en clientes).

---

## Operación recomendada (sin validar contabilidad oficial)

| Tarea | Módulo |
|---|---|
| Alta de clientes / proveedores | Ventas / Compras |
| Cotizaciones y ventas en borrador → confirmar | Ventas |
| Compras y recepción de stock | Compras + Inventario |
| Abonos CxC / CxP | Cartera |
| Importar inventario inicial (si hay Excel) | Inventario → Importar |
| Export / plantilla retenciones (dejar para Contador) | Ventas → Clientes → Plantilla |

**No usar aún como oficial:** Estado de Resultados / Balance para terceros (mapeo PUC pendiente de Contador).

---

## Seguridad operativa

- [ ] Clave de `BACKUP_ENCRYPTION_KEY` en gestor personal (no en txt en la carpeta de backups)
- [ ] OneDrive offsite con `.enc` recientes
- [ ] No entregar tarjetas de acceso hasta decidir **#7**
- [ ] Tras login de cada persona: **cambiar contraseña** (política: min 8, letra + dígito)

---

## Semanal (opcional)

- [ ] `powershell -ExecutionPolicy Bypass -File ops\run-tests.ps1` (requiere Postgres local)
- [ ] Frontend: `cd frontend && npm.cmd test -- --run`
- [ ] Revisar carpeta `C:\SuperOzono-Backups` y offsite

---

## Si algo “no abre”

| Síntoma | Qué hacer |
|---|---|
| Login: no conecta al servidor | `start.bat`; ver ventanas Backend/Frontend |
| Certificado no confiable | Instalar `certs\superozono-ca.crt` en el PC cliente |
| 429 demasiados intentos | Esperar 1 minuto |
| IP cambió | Actualizar `.env` frontend/backend + regenerar cert (ver DESPLIEGUE) |
