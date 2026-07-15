# Entorno de staging (LAN, sin contadora)

Objetivo: **probar cambios sin tocar la BD de producción** en el mismo PC servidor
(o en una carpeta paralela). No requiere Docker ni AWS.

## Opciones

| Opción | Cuándo | Esfuerzo |
|---|---|---|
| **A. Carpeta paralela + SQLite copia** | LAN v0.3.0 actual | Bajo — recomendada |
| **B. Docker compose prod con puertos distintos** | Cuando haya Docker Desktop | Medio |
| **C. RDS/ECS staging en AWS** | Solo tras `terraform apply` | Alto — no en este PC |

---

## A. Staging LAN (recomendado hoy)

### 1. Una sola vez — copiar el repo a una carpeta staging

```bat
xcopy /E /I /H "C:\ruta\prod\superozono-erp" "C:\SuperOzono-Staging\superozono-erp"
```

O clonar de nuevo:

```bat
cd C:\SuperOzono-Staging
git clone https://github.com/leonardeco/superozono-erp.git
```

### 2. Script de preparación (copia BD + puertos)

Desde la raíz del repo de **staging**:

```powershell
powershell -ExecutionPolicy Bypass -File ops\setup-staging.ps1
```

El script:

- crea `backend\.env.staging` si no existe
- copia `backend\superozono.db` → `backend\superozono_staging.db` (si hay BD prod local)
- fija puertos **8010** (API) y **5180** (Vite) y CORS de staging
- no toca la BD ni los puertos de producción

### 3. Arrancar staging (manual)

**Backend** (otra ventana, no uses `start.bat` de prod):

```bat
cd backend
set DATABASE_URL=sqlite+aiosqlite:///./superozono_staging.db
venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --ssl-keyfile ..\certs\server.key --ssl-certfile ..\certs\server.crt
```

**Frontend**:

```bat
cd frontend
set VITE_API_URL=https://127.0.0.1:8010/api
npm run dev -- --host 127.0.0.1 --port 5180
```

Abrir: `https://127.0.0.1:5180` (aceptar el cert local si es la CA de Super Ozono).

### 4. Reglas de seguridad

- **Nunca** apuntes el staging a `superozono.db` de producción.
- **Nunca** corras seed demo sobre la BD de producción (`seed_demo.py` ya tiene guard).
- Tras validar en staging: `git pull` en prod → checklist `DESPLIEGUE.md`.
- Si copiaste una BD real a staging, trátala como dato sensible (mismas contraseñas de usuarios).

### 5. Refrescar datos de staging desde prod

Con el ERP de prod **apagado** (o al menos sin escrituras):

```powershell
Copy-Item backend\superozono.db backend\superozono_staging.db -Force
```

(ajusta rutas si prod y staging están en carpetas distintas).

---

## B. Staging con Docker (`docker-compose.prod.yml`)

Cuando exista Docker Desktop:

```bat
copy .env.docker.example .env.docker.staging
```

Editar `.env.docker.staging`:

- `POSTGRES_DB=superozono_staging`
- `FRONTEND_PORT=8080`
- `BACKEND_PORT=8001`
- `DEBUG=true` solo en staging (opcional)
- secretos **distintos** a prod

```bat
docker compose -f docker-compose.prod.yml --env-file .env.docker.staging -p superozono-staging up -d --build
```

`-p superozono-staging` evita chocar con contenedores de otro compose en el mismo host.

---

## Checklist rápido antes de promover a prod

- [ ] Tests CI verdes en la rama/commit a desplegar
- [ ] Smoke login + crear venta borrador en staging
- [ ] Backup manual de prod (`scripts\backup_db.py`)
- [ ] Seguir `DESPLIEGUE.md` (stop → pull → deps → alembic → start)
