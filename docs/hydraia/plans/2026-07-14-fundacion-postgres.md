# Implementation Plan — Fundación Postgres (Run 1)

- **Goal:** PostgreSQL como motor probado en dev/tests/CI; 285 tests verdes en PG;
  migraciones limpias en PG fresco + `alembic check` sin drift (#10); la app sigue
  soportando SQLite (LAN). Sin lógica de tenant.
- **Deriva de spec:** `docs/hydraia/specs/2026-07-14-fundacion-postgres-design.md`.
- **Verificación:** por CI (no hay Postgres local). Ejecución iterativa: cambiar → push →
  CI corre en PG real → corregir → repetir hasta verde.
- **Ejecución:** la conduce la sesión principal (Opus) porque los fixes dependen del
  feedback del CI que se observa vuelta a vuelta — no son tareas paralelizables a
  executors fríos. (Divulgado, como en runs previos de esta sesión.)

## Global Constraints
- Motor de test por `TEST_DATABASE_URL` (default `postgresql+asyncpg://postgres:postgres@localhost:5432/superozono_test`).
- Aserto en conftest: `engine.dialect.name == "postgresql"` (evita falso verde en SQLite).
- Aislamiento **behavior-identical** (drop_all/create_all + seeds por test). Fallback a
  truncate solo con evidencia de timeout en CI.
- `alembic check` como detector de drift; ajustar `compare_type`/`compare_server_default`
  en `env.py` solo si hay ruido cosmético.
- **No** eliminar soporte SQLite; la app debe arrancar en SQLite.
- Sin tenant/RLS/auth/concurrencia. Sin nuevas deps.

## File Structure
| File | Responsabilidad |
|---|---|
| `backend/tests/conftest.py` | **Modify.** Engine de test → Postgres por env + aserto de dialecto. |
| `.github/workflows/ci.yml` | **Modify.** `services: postgres` + env PG + paso `alembic upgrade head`+`check`. |
| `backend/.env.example` | **Modify.** Documentar `TEST_DATABASE_URL` + PG de dev. |
| `README.md` / `DOCUMENTACION.md` | **Modify.** Postgres = motor probado; `docker compose up -d db` para tests locales; SQLite sigue para LAN. |
| `backend/alembic/versions/*` | **(Empírico)** posible migración de reconciliación si `alembic check` marca drift. |

---

## Task 1 — `conftest.py` → Postgres (motor de test + aserto)

**Files:** `Modify: backend/tests/conftest.py`.

**Cambios exactos:**
- Reemplazar el bloque del engine sqlite:
  ```python
  # antes
  SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
  engine = create_async_engine(
      SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
  )
  ```
  por (leer env, default PG, aserto anti-falso-verde):
  ```python
  import os as _os
  TEST_DATABASE_URL = _os.environ.get(
      "TEST_DATABASE_URL",
      "postgresql+asyncpg://postgres:postgres@localhost:5432/superozono_test",
  )
  engine = create_async_engine(TEST_DATABASE_URL)
  assert engine.dialect.name == "postgresql", (
      f"La suite debe correr en PostgreSQL (T3). TEST_DATABASE_URL={TEST_DATABASE_URL!r} "
      f"resolvió a dialecto {engine.dialect.name!r}."
  )
  ```
  (Ya existe `import os` en la línea 1; reutilizar. `create_async_engine`/`async_sessionmaker`
  ya importados.)
- El fixture `setup_db` (drop_all/create_all + seeds admin + 2 `ParametroTributario`) se
  **mantiene igual** — misma semántica en PG.

**Verificación:**
- Local (sin PG): `python -c "import ast; ast.parse(open('backend/tests/conftest.py').read()); print('OK')"` → `OK`.
- Real: en CI (Task 2), la suite corre y el aserto garantiza dialecto `postgresql`.

**Commit:** `test: correr la suite contra PostgreSQL via TEST_DATABASE_URL`.

---

## Task 2 — CI: servicio Postgres + migración/check

**Files:** `Modify: .github/workflows/ci.yml` (job `backend`).

**Cambios exactos en el job `backend`:**
- Añadir bloque `services` (mismo nivel que `steps`):
  ```yaml
      services:
        postgres:
          image: postgres:16-alpine
          env:
            POSTGRES_USER: postgres
            POSTGRES_PASSWORD: postgres
            POSTGRES_DB: superozono_test
          ports:
            - 5432:5432
          options: >-
            --health-cmd "pg_isready -U postgres"
            --health-interval 10s --health-timeout 5s --health-retries 5
  ```
- En el paso **pytest**, cambiar el `env` de SQLite a PG:
  ```yaml
          env:
            DATABASE_URL: "postgresql+asyncpg://postgres:postgres@localhost:5432/superozono_test"
            TEST_DATABASE_URL: "postgresql+asyncpg://postgres:postgres@localhost:5432/superozono_test"
            SECRET_KEY: "ci-secret-key-solo-para-tests-0123456789abcdef"
            SEED_ADMIN_PASSWORD: "ci-admin-pass-no-produccion"
  ```
- Añadir un paso **antes** de pytest (o después, independiente) que valida migraciones y
  drift en una BD separada:
  ```yaml
      - name: Migraciones + alembic check (drift #10)
        env:
          PGPASSWORD: postgres
          DATABASE_URL: "postgresql+asyncpg://postgres:postgres@localhost:5432/superozono_migcheck"
          SECRET_KEY: "ci-secret-key-solo-para-tests-0123456789abcdef"
          SEED_ADMIN_PASSWORD: "ci-admin-pass-no-produccion"
        run: |
          psql -h localhost -U postgres -c "CREATE DATABASE superozono_migcheck" || true
          python -m alembic upgrade head
          python -m alembic check
  ```
  (Si `env.py` no toma `DATABASE_URL` del entorno para alembic, ajustarlo — verificar en
  Task 4.)

**Verificación:** el CI del PR corre y este job pasa (los 285 tests + migración/check).

**Commit:** `ci: servicio Postgres + alembic upgrade/check en el job backend`.

---

## Task 3 — Docs + ergonomía de dev

**Files:** `Modify: backend/.env.example`, `README.md`, `DOCUMENTACION.md`.

- `.env.example`: añadir `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/superozono_test`
  y una nota de que dev/tests corren en Postgres (`docker compose up -d db`), mientras el
  LAN sigue en SQLite.
- `README.md`: subsección "Tests / desarrollo con Postgres" con `docker compose up -d db`
  + `createdb superozono_test` (o vía compose) + `pytest`. Aclarar que **SQLite sigue
  soportado** para el despliegue LAN.
- `DOCUMENTACION.md` §13: nota de que Run 1 (Fundación Postgres) migró tests/CI a PG y
  cerró el drift #10; enlazar el ADR/runbook.

**Verificación:** `grep -c TEST_DATABASE_URL backend/.env.example` → ≥1; `grep -c "docker compose up -d db" README.md` → ≥1.

**Commit:** `docs: documentar Postgres como motor de tests/dev (SQLite sigue en LAN)`.

---

## Task 4 — (Empírico) Iterar el CI hasta verde

**Objetivo:** con el CI corriendo en Postgres real, cerrar los fallos que solo aparecen al
ejecutar. No se pueden pre-especificar; se abordan por evidencia del CI.

**Procedimiento:**
1. Push de la rama `feat/fundacion-postgres` → observar el job backend.
2. Categorías de fallo esperadas y su fix:
   - **`alembic upgrade head` falla en PG** (tipos ENUM, batch): corregir la migración
     ofensora o añadir manejo de tipos PG.
   - **`alembic check` reporta drift (#10):** generar/añadir una migración de
     reconciliación; si es ruido cosmético (server_default/tipo), afinar `compare_*` en
     `env.py` y documentarlo.
   - **Tests fallan por diferencias SQLite↔PG** (LIKE case-sensitive, boolean, decimal,
     orden sin ORDER BY, autoincrement): corregir el test o el código de forma
     dialect-neutral (preferir el fix mínimo y correcto).
   - **Timeout por lentitud** (drop/create por test): activar el fallback truncate +
     reseed en `conftest.py` (documentado en el spec).
   - **El aserto de dialecto falla:** el env del CI no llegó al engine → corregir env.
3. Verificar cada vuelta con `gh run watch` hasta `conclusion: success`.

**Criterio de cierre (verificación real):** el job backend del CI termina verde con los
285 tests en Postgres **y** el paso de migración/check en verde.

**Commits:** uno por fix coherente, mensajes claros (`fix(db): ...`, `fix(migrations): ...`).

---

## Notas de alcance (lo que este run NO hace)
- No agrega `tenant_id`, RLS, ni cambia auth/roles ni concurrencia (Runs 2–5).
- No elimina SQLite; la app y `start.bat` siguen funcionando en SQLite (LAN).
