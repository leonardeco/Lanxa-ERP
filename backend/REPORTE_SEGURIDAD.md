# Reporte de Seguridad — Super Ozono Global ERP
**Fecha:** 2026-06-26
**Versión analizada:** 0.2.0
**Alcance:** Backend FastAPI (`superozono-erp/backend`)
**Método:** Análisis estático de código fuente completo
**Auditor:** Claude Sonnet 4.6

---

## Resumen Ejecutivo

El ERP tiene una base de seguridad **sólida** para su etapa actual:
- Refresh tokens con rotación automática y almacenamiento hasheado (SHA-256) en BD
- Cookies HttpOnly + Secure + SameSite=Strict
- Rate limiting en login (5 req/min con SlowAPI)
- Control de acceso por roles verificado en BD (Admin / Administradora / Auxiliar)
- Contraseñas hasheadas con bcrypt
- Sin SQL injection posible (uso de ORM parametrizado)
- Constraint de BD que rechaza roles inválidos

**Hallazgos:** 2 ALTO · 4 MEDIO · 3 BAJO

---

## ALTO

### SEC-001 — Swagger UI expuesto en producción
**Archivo:** `app/main.py` línea 84
**Riesgo:** Reconocimiento facilitado para atacantes

```python
app = FastAPI(
    docs_url="/docs",    # expuesto en producción
    redoc_url="/redoc",  # expuesto en producción
    ...
)
```

**Impacto:** Cualquier persona con acceso a la URL puede explorar toda la estructura de la API, ver todos los schemas de request/response, y probar endpoints directamente desde el navegador sin necesidad de herramientas especializadas. Facilita enormemente el reconocimiento en un ataque.

**Fix:**
```python
# app/main.py
app = FastAPI(
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)
```

---

### SEC-002 — Token de Alegra (API key) en archivo .env sin rotación documentada
**Archivo:** `app/core/config.py` líneas 37-38 · `backend/.env`
**Riesgo:** Compromiso de cuenta de facturación electrónica

```python
ALEGRA_EMAIL: str = ""
ALEGRA_TOKEN: str = ""
```

**Impacto:** El token de Alegra se almacena en texto plano en `.env`. Si el archivo se expone (commit accidental a git, acceso al servidor, backup sin cifrar), un atacante puede:
- Emitir facturas electrónicas fraudulentas a nombre de la empresa
- Extraer toda la información fiscal de clientes y proveedores
- Cancelar facturas reales

**Verificar urgente:**
```bash
# Confirmar que .env nunca se commiteó
git log --all --full-history -- .env .env.produccion
```

**Recomendaciones:**
1. Rotar el token de Alegra inmediatamente si hay duda de exposición
2. Usar variables de entorno del sistema operativo en lugar de archivos `.env` en producción
3. Documentar procedimiento de rotación del token (cuándo y cómo rotarlo)

---

## MEDIO

### SEC-003 — `datetime.utcnow()` deprecado en Python 3.12+
**Archivos:**
- `app/core/security.py` líneas 24, 25, 44, 45
- `app/modules/ventas/models.py` líneas 77, 78
- `app/modules/usuarios/models.py` línea 36

**Impacto:** `datetime.utcnow()` produce objetos "naive" (sin información de timezone). En Python 3.12 genera `DeprecationWarning`. Los comparadores de tiempo en `refresh_token_expiry()` comparan naive vs naive, que es consistente hoy, pero un cambio parcial en el futuro podría introducir bugs sutiles de timezone difíciles de detectar.

**Fix (aplicar en todos los archivos):**
```python
# Cambiar el import:
from datetime import datetime, timedelta, timezone

# Cambiar todas las ocurrencias:
datetime.utcnow()  →  datetime.now(timezone.utc)
```

---

### SEC-004 — Access token JWT sigue válido 1 hora tras logout
**Archivo:** `app/modules/usuarios/router.py` — endpoint `POST /login/logout`

**Impacto:** El logout solo invalida el refresh token en BD. El JWT de acceso permanece criptográficamente válido durante `ACCESS_TOKEN_EXPIRE_HOURS` (actualmente 1 hora). Si un atacante captura el access token justo antes del logout (p.ej. en logs de red, proxy corporativo), puede usarlo libremente hasta que expire.

**Opciones:**
- **Corto plazo (recomendado):** Reducir `ACCESS_TOKEN_EXPIRE_HOURS` a 15 minutos. Los refresh tokens manejan la sesión larga; el access token debería ser de vida corta.
- **Largo plazo:** Implementar una blacklist de JTI (JWT ID) en Redis para revocar tokens específicos.

```python
# .env
ACCESS_TOKEN_EXPIRE_HOURS=0  # usar minutos
ACCESS_TOKEN_EXPIRE_MINUTES=15  # agregar nueva variable
```

---

### SEC-005 — Sin rate limiting en endpoints de cambio de contraseña
**Archivo:** `app/modules/usuarios/router.py` líneas 182, 197

Los endpoints `PUT /v1/usuarios/{id}/reset-password` y `PUT /v1/usuarios/me/password` no tienen rate limiting. Un usuario autenticado malintencionado podría intentar passwords masivamente contra otros usuarios o contra su propia cuenta para pruebas de fuerza bruta interna.

**Fix:**
```python
from app.core.limiter import limiter

@router.put("/v1/usuarios/{user_id}/reset-password")
@limiter.limit("5/minute")
async def reset_usuario_password(request: Request, ...):
    ...

@router.put("/v1/usuarios/me/password")
@limiter.limit("10/minute")
async def change_my_password(request: Request, ...):
    ...
```

---

### SEC-006 — CORS acepta `*` si se configura mal en producción
**Archivo:** `app/core/config.py` línea 33

```python
CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
```

No hay validación que impida configurar `*` en producción. Si alguien pone `CORS_ORIGINS=*` en el `.env` del servidor, cualquier sitio web podría hacer peticiones autenticadas al ERP desde el navegador del usuario logueado.

**Fix — agregar validador en Settings:**
```python
from pydantic import field_validator

@field_validator("CORS_ORIGINS")
@classmethod
def cors_no_wildcard_en_produccion(cls, v, info):
    if not info.data.get("DEBUG", True) and "*" in v:
        raise ValueError("CORS wildcard (*) no permitido en producción (DEBUG=false)")
    return v
```

---

## BAJO

### SEC-007 — Información del sistema expuesta en endpoint público `/`
**Archivo:** `app/main.py` línea 126

```python
return {
    "app": settings.APP_NAME,
    "version": settings.APP_VERSION,   # versión exacta del sistema
    "empresa": settings.EMPRESA_RAZON_SOCIAL,
    "nit": settings.EMPRESA_NIT,       # NIT expuesto sin autenticación
    "docs": "/docs",
    "health": "/health",
}
```

**Impacto:** La versión exacta del sistema permite buscar vulnerabilidades conocidas de esa versión. El NIT expuesto es información fiscal sensible.

**Fix para producción:**
```python
@app.get("/")
async def root():
    if settings.DEBUG:
        return {"app": settings.APP_NAME, "version": settings.APP_VERSION, ...}
    return {"status": "online"}
```

---

### SEC-008 — Clave de cifrado de backups opcional
**Archivo:** `app/core/config.py` línea 42

```python
BACKUP_ENCRYPTION_KEY: str = ""
```

Si `BACKUP_ENCRYPTION_KEY` está vacío, los backups de la BD (facturas, hashes de contraseñas, datos de clientes y proveedores) pueden ser almacenados sin cifrar.

**Fix en `scripts/backup_db.py`:**
```python
from app.core.config import get_settings
settings = get_settings()

if not settings.BACKUP_ENCRYPTION_KEY:
    raise RuntimeError("BACKUP_ENCRYPTION_KEY no configurado. Los backups no se ejecutarán sin cifrado.")
```

---

### SEC-009 — Integración Alegra usa POST para actualizar contactos
**Archivo:** `app/modules/alegra/router.py` línea 76

```python
if cliente.alegra_id:
    result = await alegra_post(f"/contacts/{cliente.alegra_id}", payload)  # debería ser PUT?
```

La API REST de Alegra probablemente requiere `PUT` para actualizar un contacto existente, no `POST`. Usar `POST` a una URL con ID podría crear contactos duplicados o fallar silenciosamente.

**Fix:**
```python
# En app/modules/alegra/client.py — agregar función alegra_put()
async def alegra_put(path: str, payload: dict) -> dict:
    ...

# En alegra/router.py:
if cliente.alegra_id:
    result = await alegra_put(f"/contacts/{cliente.alegra_id}", payload)
else:
    result = await alegra_post("/contacts", payload)
```

---

## Aspectos de seguridad correctamente implementados

| Aspecto | Implementación | Archivo |
|---|---|---|
| Hash de contraseñas | bcrypt via passlib | `security.py` |
| JWT con expiración | python-jose, HS256 | `security.py` |
| Refresh token hasheado | SHA-256 en BD, nunca texto plano | `security.py` |
| Rotación de refresh tokens | El viejo se invalida al usar | `usuarios/router.py` |
| Cookie segura | HttpOnly + Secure + SameSite=Strict | `usuarios/router.py` |
| Rate limiting en login | 5 req/min con SlowAPI | `usuarios/router.py` |
| Control de roles en BD | CheckConstraint + verificación en deps | `usuarios/models.py` |
| Verificación de usuario activo | En cada request autenticado | `deps.py` |
| Sin SQL injection | ORM parametrizado (SQLAlchemy) | Todos los routers |
| Separación Admin/Administradora | Funciones de dep separadas | `deps.py` |

---

## Checklist para paso a producción

- [ ] Deshabilitar `/docs`, `/redoc` y `/openapi.json` (`DEBUG=false` en .env)
- [ ] Rotar `ALEGRA_TOKEN` y verificar que no está en git history
- [ ] Cambiar `SECRET_KEY` a uno generado aleatoriamente en el servidor
- [ ] Reducir `ACCESS_TOKEN_EXPIRE_HOURS` a menos de 1 hora (recomendado: 15 min)
- [ ] Configurar `CORS_ORIGINS` con el dominio exacto del frontend
- [ ] Verificar que `.env` y `.env.produccion` no están en `git log`
- [ ] Configurar `BACKUP_ENCRYPTION_KEY` antes de activar backups
- [ ] Agregar rate limiting en endpoints de cambio de contraseña
- [ ] Revisar API de Alegra y usar PUT para actualizar contactos/productos
- [ ] Reemplazar `datetime.utcnow()` por `datetime.now(timezone.utc)` en todo el codebase

---

## Actualización — 2026-07-02

**Auditor:** Claude Fable 5 · **Método:** pip-audit + npm audit + revisión de código

### Resuelto en esta fecha

| Hallazgo | Fix |
|---|---|
| **14 CVEs en dependencias** (python-multipart 0.0.20 ×6, starlette 0.46.2 ×8) | `python-multipart==0.0.31`, `fastapi==0.139.0` + `starlette==1.3.1` — pip-audit ahora reporta 0 vulnerabilidades |
| **SEC-001** — Swagger expuesto en producción | `/docs`, `/redoc` y `/openapi.json` devuelven 404 con `DEBUG=false` (`app/main.py`) |
| **SEC-003** — `datetime.utcnow()` deprecado | Helper `utcnow()` naive-UTC en `app/core/time.py`, aplicado en todo el codebase |
| **SEC-004** — Access token válido 1h tras logout | `ACCESS_TOKEN_EXPIRE_MINUTES=15` (nueva variable, reemplaza `ACCESS_TOKEN_EXPIRE_HOURS`) |
| **SEC-005** — Sin rate limit en cambio de contraseña | `@limiter.limit` en `reset-password` (5/min) y `me/password` (10/min) |
| **SEC-006** — CORS `*` posible en producción | Validador en `Settings` rechaza `*` con `DEBUG=false` (test incluido) |
| **SEC-007** — Versión y NIT expuestos en `/` | Con `DEBUG=false` el root devuelve solo `{"status": "online"}` |
| **SEC-008** — Cifrado de backups opcional | Ya estaba resuelto: `backup_db.py` aborta sin `BACKUP_ENCRYPTION_KEY` |
| **SEC-009** — POST en updates de Alegra | `alegra_put()` para `/contacts/{id}` y `/items/{id}` |
| **Nuevo** — Sin headers de seguridad HTTP | Middleware ASGI puro: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, HSTS (test incluido) |
| **Nuevo** — Sin auditoría continua de dependencias | Job `security` en CI corre `pip-audit` en cada push/PR; `npm audit` reporta 0 vulnerabilidades |

### Pendiente (aceptado por contexto LAN)

- **SEC-002** — Rotación documentada del token de Alegra: pendiente definir procedimiento con la empresa
- Access token en `localStorage` (exposición ante XSS): mitigado por refresh token en cookie HttpOnly y vida de 15 min; reevaluar si el ERP sale de la LAN
- Blacklist de JTI en Redis para revocación inmediata de access tokens: innecesario con vida de 15 min en LAN cerrada
