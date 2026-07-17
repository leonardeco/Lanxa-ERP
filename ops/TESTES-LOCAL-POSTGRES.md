# Tests locales con PostgreSQL (Windows)

La suite de API del backend **exige PostgreSQL** (no SQLite): RLS, locks y dialecto de producción.

## Prerrequisitos

1. **PostgreSQL 16+** corriendo en `localhost:5432`.
2. Usuario/clave de superusuario (en este PC de desarrollo: `postgres` / `postgres`).
3. BDs creadas:

```bat
set PGPASSWORD=postgres
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE superozono_test;"
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE superozono_migcheck;"
```

(Si ya existen, omitir. Si fallan por contraseña, usa la que definiste al instalar.)

4. Dependencias: `backend\venv` con `requirements.txt` + `requirements-dev.txt`.

## Arranque rápido (PowerShell)

Desde la **raíz del repo**:

```powershell
powershell -ExecutionPolicy Bypass -File ops\run-tests.ps1
```

Solo unitarios sin BD (`@pytest.mark.no_db`):

```powershell
powershell -ExecutionPolicy Bypass -File ops\run-tests.ps1 -NoDb
```

Solo un archivo:

```powershell
powershell -ExecutionPolicy Bypass -File ops\run-tests.ps1 -PytestArgs "tests/test_locks_stock.py -q"
```

## Variables de entorno (lo que usa el script)

| Variable | Valor típico |
|---|---|
| `TEST_DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/superozono_test` |
| `DATABASE_URL` | igual (Alembic / app en algunos tests) |
| `SECRET_KEY` | cadena ≥ 32 chars (el script pone una de test) |
| `SEED_ADMIN_PASSWORD` | no de fábrica (el script pone una de test) |

## Frontend (Vitest)

```bat
cd frontend
npm.cmd test -- --run
```

## E2E Playwright (opcional)

Levanta API en 8100 + Vite 5273 (ver `frontend/playwright.config.ts`):

```bat
cd frontend
npm.cmd run test:e2e
```

En CI el job E2E es informativo (`continue-on-error`).

## Alembic check (drift)

En una BD limpia de migcheck (como CI):

```bat
cd backend
set DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/superozono_migcheck
set SECRET_KEY=ci-secret-key-solo-para-tests-0123456789abcdef
set SEED_ADMIN_PASSWORD=ci-admin-pass-no-produccion
venv\Scripts\python.exe -m alembic upgrade head
venv\Scripts\python.exe -m alembic check
```

> Si `alembic upgrade` falla a mitad en una BD que ya tenía tablas a medias,  
> `DROP DATABASE` / `CREATE DATABASE` y reintentar.

## Servicio Windows en este PC

- Servicio: `postgresql-x64-17`
- Arrancar: `Start-Service postgresql-x64-17`
- Puerto: `5432`

## Nota LAN vs tests

| Entorno | Motor |
|---|---|
| ERP LAN v0.3.0 (`start.bat`) | **SQLite** (`backend\superozono.db`) |
| Suite pytest / CI | **PostgreSQL** |

No mezclar: no apuntes `TEST_DATABASE_URL` a la BD de producción LAN.
