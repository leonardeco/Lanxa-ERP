# Implementation Plan — Run 2: Tenancy foundation (ADR 0001)

- **Goal:** Modelo `Tenant`, columna `tenant_id` en tablas de negocio, claim JWT +
  contextvar por request, secuencias por tenant. **Sin RLS aún** (Run 3).
- **Deriva de:** ADR 0001 + runbook AWS Fase 1 (pasos 2–3 parciales).
- **Verificación:** migración en SQLite LAN; tests `test_tenancy.py` en CI Postgres;
  smoke login con JWT que incluye `tenant_id`.

## Hecho en este run

| Pieza | Detalle |
|---|---|
| `tenants` | Tabla + seed empresa #1 (`superozono`) |
| `tenant_id` | FK en tablas de datos (migración `e6f7a8b9c0d1`) |
| ORM | Mixin `TenantScoped` en modelos de negocio |
| Auth | `create_access_token(..., tenant_id=)`; `get_current_user` fija contextvar |
| Numeración | PK `(tenant_id, prefix)` en `document_sequences` |
| Seeds/tests | Seed tenant antes de usuarios; conftest crea tenant #1 |

## No hecho (Runs siguientes)

- Run 3: políticas RLS Postgres + `SET app.tenant_id`
- Run 4: filtros automáticos en todos los list endpoints + tests de aislamiento HTTP
- Run 5: onboarding multi-empresa / subdominio

## LAN

El despliegue actual sigue mono-empresa: todo el dato queda en `tenant_id=1`.
Comportamiento de negocio sin cambio para los 4 usuarios actuales.
