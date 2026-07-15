# Implementation Plan — Run 5: uniques por tenant + onboarding

- **Goal:** Un mismo SKU/email/NIT/número puede existir en empresas distintas;
  API de alta de empresa con Admin inicial (solo plataforma tenant #1).
- **Depende de:** Runs 2–4.

## Hecho

| Pieza | Detalle |
|---|---|
| Migración `a0b1c2d3e4f5` | UNIQUE(tenant_id, col) en claves de negocio |
| ORM | `UniqueConstraint` en productos/usuarios/clientes/proveedores |
| `POST /api/v1/tenants/onboard` | Crea Tenant + Admin (solo Admin tenant #1) |
| `GET /api/v1/tenants` | Plataforma lista todos; resto solo el propio |
| Tests | `test_tenant_onboard.py` |

## Uso onboarding

```http
POST /api/v1/tenants/onboard
Authorization: Bearer <admin_plataforma>
{
  "codigo": "cliente-abc",
  "razon_social": "Cliente ABC SAS",
  "nit": "900123456",
  "admin_email": "admin@cliente-abc.com",
  "admin_nombre": "Admin ABC",
  "admin_password": "TemporalSegura1!"
}
```

## Limitaciones

- Login sigue siendo por email global (si dos tenants usan el mismo email, el
  primero que coincida gana). Preferir emails únicos entre empresas o añadir
  `codigo` de tenant en un Run futuro.
- No clona PUC/catálogo a la empresa nueva (empieza vacía salvo lo que se siembre).
