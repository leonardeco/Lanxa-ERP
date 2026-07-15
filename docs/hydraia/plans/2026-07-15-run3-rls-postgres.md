# Implementation Plan — Run 3: RLS PostgreSQL (ADR 0001)

- **Goal:** Row-Level Security por `tenant_id` en Postgres; la app fija
  `app.tenant_id` por transacción. SQLite LAN sin cambios de comportamiento.
- **Depende de:** Run 2 (`tenant_id` en tablas + contextvar + JWT).

## Hecho

| Pieza | Detalle |
|---|---|
| Migración `f7a8b9c0d1e2` | ENABLE+FORCE RLS + policy `tenant_isolation` (solo PG) |
| `apply_rls_tenant` | `set_config('app.tenant_id', …, true)` |
| `get_db` / auth | Fijan GUC al abrir sesión y tras login |
| Tests | `test_rls_oculta_productos_de_otro_tenant` (skip en SQLite) |

## Uso

```python
await apply_rls_tenant(session, tenant_id)
# queries / inserts respetan la política
```

## LAN (SQLite)

La migración es **no-op**. No hay RLS; el aislamiento app-level de Run 2 basta
para mono-empresa. Al migrar a Postgres en la nube, RLS queda activo.

## Siguiente (Run 4)

- Filtros explícitos `.where(Model.tenant_id == get_tenant_id())` en listados
  (defensa en profundidad además de RLS).
- Tests HTTP de aislamiento cross-tenant en todos los módulos críticos.
