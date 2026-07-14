# Design Spec — Fundación Postgres (Fase 1, Run 1 de multi-tenancy)

- **Date:** 2026-07-14
- **Branch:** `feat/fundacion-postgres`
- **Deriva de:** ADR `docs/hydraia/adr/0001-lan-monoempresa-a-saas-multitenant-aws.md`,
  runbook Fase 1 (`docs/hydraia/plans/2026-07-14-migracion-aws-runbook.md`).
- **Decomposición confirmada:** este run = **Run 1 (Fundación Postgres) SOLO**. Runs 2–5
  (tenant model, RLS, auth por-tenant, concurrencia) son corridas Hydraia posteriores.

## Goal

Hacer de **PostgreSQL el motor probado y soportado** para desarrollo, la suite de tests
y el CI —requisito previo de RLS, que no existe en SQLite— dejando **los 285 tests verdes
en Postgres**, las **10 migraciones Alembic aplicando limpio en un PG fresco**, y el
**drift de Alembic (#10) reconciliado** (`alembic check` sin diferencias). **Sin lógica de
tenant.** La app **sigue soportando SQLite** (despliegue LAN de v0.3.0 en curso).

## Chosen approach + rejected alternatives

### Naturaleza empírica + verificación por CI (decisión del usuario)
No hay Postgres en el entorno de trabajo (sin Docker/psql). Por decisión del usuario, la
verificación se hace **en el CI de GitHub Actions**, que sí levanta un Postgres real vía
`services:`. El flujo de ejecución es iterativo: implementar → push → CI corre la suite en
PG → corregir lo que falle → repetir hasta verde. Varios fallos solo se conocen al correr
(tipos ENUM nativos, diferencias de comportamiento SQLite↔PG); el plan front-loadea la
estructura conocida y trata los fixes como trabajo de ejecución.

### Motor de tests → Postgres (elegido)
`tests/conftest.py` construye hoy un engine **`sqlite+aiosqlite:///:memory:`**. Cambia a
leer **`TEST_DATABASE_URL`** (env), por defecto
`postgresql+asyncpg://postgres:postgres@localhost:5432/superozono_test`.
- **Rechazado — mantener SQLite en tests + PG aparte:** deja los tests validando un motor
  que no es el de prod/nube y perpetúa justo el drift que #10 busca matar. El usuario
  eligió cambiar toda la suite.

### Aislamiento por test → **behavior-identical primero** (elegido)
El fixture autouse actual hace `drop_all` + `create_all` + siembra admin + un
`ParametroTributario`, **por test**. Se mantiene **esa misma semántica** apuntando a PG
(create_all/drop_all por test), para **maximizar la probabilidad de que los 285 tests
pasen sin cambios** (mismo comportamiento, solo otro motor).
- **Rechazado (por ahora) — truncate + reseed por test / schema por sesión:** más rápido
  en PG, pero cambia sutilmente la semántica (IDs, secuencias) y arriesga romper tests que
  asumen esquema fresco. **Fallback:** si el CI muestra timeouts por lentitud, optimizar a
  `TRUNCATE ... RESTART IDENTITY CASCADE` + reseed. Se difiere hasta tener esa evidencia.

### Reconciliación del drift (#10) → `alembic upgrade head` + `alembic check` (elegido)
Los tests construyen el esquema desde **modelos** (`create_all`). Por separado, un paso de
CI crea un PG fresco, corre **`alembic upgrade head`** y luego **`alembic check`**
(Alembic 1.18): si detecta diferencia entre los modelos y el esquema migrado, **falla** →
eso ES el detector de drift #10. El fix es una migración de reconciliación.
- **Rechazado — construir el esquema de tests desde migraciones:** acopla la velocidad de
  los tests a la cadena de migraciones y mezcla dos preocupaciones; mejor separadas.

### La app sigue dual (SQLite + Postgres)
`app/core/database.py` ya es dialect-aware; `env.py` ya condiciona `render_as_batch` a
SQLite. **No se elimina el soporte SQLite** — el despliegue LAN de v0.3.0 (Carril 0) sigue
en SQLite. Solo se agrega Postgres como camino probado.

## Code-graph anchors

- `backend/tests/conftest.py` — engine de test (hoy sqlite in-memory), fixture autouse
  `setup_db` (drop/create + seed admin + `ParametroTributario`), `override_get_db`.
- `backend/app/core/database.py` — `Base`, `engine`/`async_session` desde
  `settings.DATABASE_URL` (dialect-aware, `_is_sqlite`).
- `backend/app/core/config.py` — `Settings.DATABASE_URL` (requerido).
- `backend/alembic/env.py` — `render_as_batch = dialect == sqlite` (líneas ~60/71).
- `backend/alembic/versions/*.py` — 10 migraciones; baseline
  `99c028642b89_baseline_esquema_inicial_completo`; 3 usan `op.batch_alter_table`
  (funciona en PG, ejecuta ALTER directo).
- `.github/workflows/ci.yml` — job `backend` (ubuntu, `DATABASE_URL=sqlite...test_ci.db`,
  flake8/mypy/pytest). **Falta** un `services: postgres`.
- `docker-compose.yml` — servicio `db` (`postgres:16-alpine`) ya definido para local.
- Modelo: **30 tablas**, muchas con `SAEnum(...)` → PG crea tipos ENUM nativos.

## Global constraints (valores exactos)

- **Sin tenant/RLS/auth/concurrencia** en este run — estrictamente motor.
- **285 tests verdes en Postgres** (criterio de éxito, verificado en CI).
- **`alembic upgrade head` limpio** en PG fresco + **`alembic check` sin diff**.
- **No romper SQLite:** la app y `start.bat` deben seguir arrancando en SQLite.
- Test DB por env `TEST_DATABASE_URL`; CI añade `services: postgres:16`.
- Sin nuevas deps de runtime (asyncpg 0.31, alembic 1.18 ya presentes).
- Idioma respuestas: Español. Código/commits/spec: inglés-portable.

## Threat model + mitigations

Superficie mínima (infra de test/CI, sin input externo), pero:
- **T1 — Credenciales de test en el repo.** El `TEST_DATABASE_URL` y las del servicio
  postgres del CI son de un PG efímero de test (`postgres/postgres`), **nunca**
  producción. Mitigación: documentar que son solo de test; no reutilizar en prod.
- **T2 — Romper la app SQLite de LAN al "postgres-ificar".** Mitigación: no se toca
  `database.py` salvo lo estrictamente dialect-neutral; el job de test SQLite se
  mantiene o se sustituye conservando la cobertura; verificación de que la app arranca en
  SQLite. (OWASP A05 misconfiguration.)
- **T3 — Falsos verdes.** Si el CI no corre realmente contra PG (mala config del env), los
  tests podrían caer a SQLite y "pasar" sin validar nada. Mitigación: un aserto explícito
  en conftest de que el dialecto del engine de test es `postgresql` (falla ruidoso si no).

## Adversarial pass

- *"¿Y si las migraciones no crean los ENUM nativos como los modelos?"* — Real; `alembic
  check` lo detecta y se corrige con una migración. Es el fix empírico esperado.
- *"drop/create por test en PG será lentísimo."* — Riesgo de timeout en CI; mitigado con el
  fallback a truncate documentado, activable con evidencia de CI.
- *"Cambiar conftest podría hacer que los tests caigan a SQLite y den falso verde."* —
  Cerrado con el aserto de dialecto (T3).
- *"¿Se rompe el despliegue LAN SQLite?"* — Mitigado: no se elimina el soporte SQLite; se
  verifica arranque SQLite. La app queda dual a propósito durante la transición.
- *"El `alembic check` podría fallar por diferencias cosméticas (server_default, tipos)."* —
  Posible; se ajusta la migración de reconciliación o se afina `compare_type`/`compare_server_default`
  en `env.py` para evitar ruido, documentándolo.

## Success criteria

1. CI: job backend corre la suite contra un **Postgres real** (servicio) y los **285 tests
   pasan**; un aserto garantiza que el motor de test es `postgresql`.
2. CI: paso de migraciones = `alembic upgrade head` limpio en PG fresco + `alembic check`
   sin diferencias (drift #10 cerrado).
3. La app sigue **arrancando en SQLite** (LAN no se rompe).
4. `TEST_DATABASE_URL` documentado; dev local puede usar `docker compose up -d db`.
5. Cero lógica de tenant/RLS/auth/concurrencia introducida (fuera de alcance).
