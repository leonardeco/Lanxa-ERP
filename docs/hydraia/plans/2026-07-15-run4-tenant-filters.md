# Implementation Plan — Run 4: filtros tenant + tests HTTP

- **Goal:** Defensa en profundidad además de RLS: todo list/get crítico filtra por
  `tenant_id`; inserts se estampan con el tenant del request.
- **Depende de:** Run 2 (columna) + Run 3 (RLS PG).

## Hecho

| Pieza | Detalle |
|---|---|
| `for_tenant` / `tenant_clause` / `get_for_tenant` | Helpers en `app/core/tenancy.py` |
| `before_insert` stamp | Mapper event fuerza `tenant_id = get_tenant_id()` |
| Ventas | productos, clientes, ventas list/get |
| Compras | proveedores, compras list/get |
| Contabilidad | PUC, centros, periodos, CxC, CxP |
| Usuarios | list + unique email por tenant |
| Reportes | aging cartera |
| Tests HTTP | `test_tenant_http_isolation.py` |

## Pendiente (endurecer)

- Cotizaciones, devoluciones, inventario router, asientos list, inventarios import
- Unicidad compuesta formal en Alembic (`UNIQUE(tenant_id, sku)`) en lugar de unique global

## LAN

Filtros son no-ops efectivos con un solo tenant (`id=1`).
