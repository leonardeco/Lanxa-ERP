# Lanxa ERP

[![CI](https://github.com/leonardeco/Lanxa-ERP/actions/workflows/ci.yml/badge.svg)](https://github.com/leonardeco/Lanxa-ERP/actions/workflows/ci.yml)
[![Versión](https://img.shields.io/badge/version-0.3.0-6c47ff?style=flat)](https://github.com/leonardeco/Lanxa-ERP/releases)
[![Python](https://img.shields.io/badge/python-3.13-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-20%2B-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![Licencia](https://img.shields.io/badge/licencia-privado%20%2F%20propietario-lightgrey)](LICENSE)

> Sistema de gestión empresarial (ERP) multi-tenant desarrollado para **LANXA S.A.S.** — cubre contabilidad, ventas, compras, cartera, inventario y reportes financieros en un solo sistema.

**Stack:** FastAPI · React 19 · TypeScript · SQLAlchemy 2.0 async · PostgreSQL / SQLite · Docker Compose

---

## Tabla de contenido

- [Características](#características)
- [Módulos](#módulos)
- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Inicio rápido — Windows](#inicio-rápido--windows)
- [Inicio rápido — Docker](#inicio-rápido--docker)
- [Variables de entorno](#variables-de-entorno)
- [Testing & QA](#testing--qa)
- [API Reference](#api-reference)
- [Seguridad](#seguridad)
- [Roles y permisos](#roles-y-permisos)
- [Documentos del proyecto](#documentos-del-proyecto)
- [Roadmap](#roadmap)

---

## Características

- **Multi-tenant** — aislamiento completo por empresa con `tenant_id` en toda tabla de negocio y RLS en PostgreSQL
- **Motor contable** — asientos de partida doble automáticos al confirmar ventas, compras y abonos; reverso al anular
- **Inventario FEFO** — control de lotes y vencimientos, kardex completo, entradas/salidas automáticas
- **Cartera completa** — CxC y CxP con comprobantes numerados (RC- / CE-), aging automático y anulación con reverso
- **Reportes financieros** — P&L, Balance General, Libro Diario, aging de cartera, retenciones; todos exportables a Excel
- **Seguridad por capas** — JWT con rotación de refresh tokens, bcrypt, rate limiting, CORS restrictivo, HTTPS con CA local
- **394 tests de API** + 25 de componentes + 5 flujos E2E en navegador real
- **Despliegue sencillo** — `start.bat` en Windows (doble clic) o `docker-compose up` para producción

---

## Módulos

| Módulo | Estado | Descripción |
|--------|:------:|-------------|
| Auth & Seguridad | ✅ | JWT + bcrypt, RBAC con 5 roles, refresh token rotativo (HttpOnly) |
| Dashboard | ✅ | Stats en tiempo real: contabilidad + ventas del mes + alertas de cartera |
| Contabilidad | ✅ | PUC (Decreto 2650), Centros de Costo, Períodos, Parámetros tributarios y de nómina |
| Ventas & Comercial | ✅ | Catálogo multimarca, Clientes B2B, Facturas con retenciones e impresión PDF |
| Compras & Proveedores | ✅ | CRUD proveedores, documentos con retenciones, confirmación/anulación, impresión PDF |
| Cartera CxC & CxP | ✅ | Abonos con comprobante numerado, **anulación con reverso contable**, aging automático |
| Devoluciones | ✅ | Nota crédito NC- (ventas) y devolución ND- (compras): reverso parcial de inventario, cartera y contabilidad |
| Inventario | ✅ | Kardex (Entrada/Salida/Ajuste), entradas/salidas automáticas al confirmar, importador .xlsx |
| Lote & Vencimiento | ✅ | `controla_lote` opt-in, consumo FEFO, alertas de vencimiento en Dashboard |
| Motor de Asientos | ✅ | Partida doble automática al confirmar/abonar/anular. **Mapeo PUC borrador — validar con contador** |
| P&L / Balance / Libro | ✅ | Estado de Resultados, Balance General con ecuación contable, Libro Diario exportable |
| Auditoría | ✅ | Log inmutable de cambios con diff, filtrado por tenant |
| Multi-tenancy | ✅ | Onboarding de nuevas empresas vía `POST /api/v1/tenants/onboard` |
| Ventas Diarias (Perú) | ✅ | Registro diario + pagos sueltos + resumen mensual — módulo específico del tenant Perú |
| Usuarios | ✅ | CRUD, gestión de roles, reset de contraseña por Admin |
| Alegra | 🔌 | Integración API Alegra para facturación electrónica DIAN (construido, pendiente activación) |
| RRHH & Nómina | 🔄 | Empleados, contratos, liquidación mensual — Fase 2 |

---

## Arquitectura

### Estructura de carpetas

```
Lanxa-ERP/
├── backend/                    # FastAPI — API REST async
│   ├── app/
│   │   ├── api/                # Dependencias compartidas (auth, sesión DB)
│   │   ├── core/               # Config, database, security (JWT + bcrypt)
│   │   ├── modules/            # Módulos de negocio (ventas, compras, ...)
│   │   └── main.py             # App factory + lifespan (create_all + seeds)
│   ├── seeds/                  # Seeders de datos base (PUC, parámetros, admin)
│   ├── scripts/                # Utilidades: backup, restore, purga auditoría, TLS
│   ├── tests/                  # 394 pruebas de API con pytest + httpx
│   └── alembic/                # Migraciones de esquema async
├── frontend/                   # React 19 + TypeScript + Vite
│   ├── src/
│   │   ├── components/         # Sidebar, HeaderBar, StatusBar
│   │   ├── contexts/           # AuthContext (JWT decode + /users/me)
│   │   ├── services/           # API clients (axios) por módulo
│   │   ├── utils/              # printFactura.ts, printCompra.ts, printComprobante.ts
│   │   └── views/              # Una vista por módulo
│   └── tests/                  # 25 tests Vitest + 5 flujos Playwright E2E
├── docker-compose.yml          # PostgreSQL 16 + Redis 7 + pgAdmin 4
├── frontend/Dockerfile         # Nginx + Vite build para producción
├── start.bat                   # Inicio local Windows (doble clic)
└── stop.bat                    # Parada limpia Windows
```

### Flujo de capas (Docker)

```
┌──────────────────────────────────────────────────┐
│  CLIENTE — Navegador (React 19 SPA, build estático) │
└────────────────────┬─────────────────────────────┘
                     │ HTTP/HTTPS (LAN)
                     ▼
┌──────────────────────────────────────────────────┐
│  FRONTEND — nginx:alpine                          │
│  · Sirve el build de React (dist/)                │
│  · Proxy: /api  /docs  /redoc  → backend:8000     │
└────────────────────┬─────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────┐
│  BACKEND — FastAPI (Python 3.13)                  │
│  ┌────────────────┐  ┌─────────────────────────┐ │
│  │ Auth JWT+bcrypt │  │ Módulos de negocio      │ │
│  │ Rate limiting   │  │ Ventas / Compras /      │ │
│  │ RBAC 5 roles    │  │ Cartera / Inventario    │ │
│  └────────────────┘  └─────────────────────────┘ │
└──────────┬──────────────────────────┬────────────┘
           ▼                          ▼
  ┌─────────────────┐      ┌─────────────────┐
  │  PostgreSQL 16   │      │    Redis 7       │
  │  (datos del ERP) │      │ (caché, opcional)│
  └─────────────────┘      └─────────────────┘

pgAdmin (puerto 5050) — administración interna de BD
```

### Patrón de módulos backend

```
modules/<nombre>/
├── models.py     # SQLAlchemy ORM models (con tenant_id)
├── schemas.py    # Pydantic v2 — request / response
└── router.py     # FastAPI APIRouter — endpoints REST
```

---

## Stack tecnológico

### Backend

| Librería | Versión | Rol |
|----------|:-------:|-----|
| FastAPI | 0.139 | Framework web async |
| SQLAlchemy | 2.0 | ORM async — PostgreSQL y SQLite |
| Pydantic | 2.13 | Validación y serialización |
| PyJWT | 2.13 | Generación y verificación JWT (HS256) |
| bcrypt | 5.0 | Hash de contraseñas (cost factor 12) |
| httpx | 0.28 | Cliente HTTP async (Alegra API) |
| structlog | 26.1 | Logging estructurado JSON |
| aiosqlite | 0.22 | Driver SQLite async (desarrollo local) |
| asyncpg | 0.31 | Driver PostgreSQL async (producción) |
| uvicorn | 0.51 | Servidor ASGI |
| Alembic | 1.18 | Migraciones de esquema async |
| pytest + httpx | 9.1 | 394 tests de API (+1 xfailed documentado) |
| flake8 + mypy | 7.3 / 2.1 | Análisis estático y verificación de tipos |

### Frontend

| Librería | Versión | Rol |
|----------|:-------:|-----|
| React | 19 | UI |
| TypeScript | 6.0 | Tipado estático |
| Vite | 8.1 | Bundler y dev server |
| Axios | 1.18 | HTTP client con interceptores JWT |
| jwt-decode | 4.0 | Decodificación de token en cliente |
| Vitest + Testing Library | 4.1 | 25 tests de componentes |
| Playwright | 1.61 | 5 flujos E2E en navegador real |

### Infraestructura (Docker)

| Servicio | Imagen | Puerto |
|----------|--------|:------:|
| Backend | Python 3.13 + uvicorn | 8000 |
| Frontend | nginx + Vite build | 80 |
| PostgreSQL | postgres:16-alpine | 5432 |
| Redis | redis:7-alpine | 6379 |
| pgAdmin | dpage/pgadmin4 | 5050 |

---

## Estructura del proyecto

```
backend/app/modules/
├── contabilidad/      # PUC, Centros de Costo, Períodos, Cartera CxC/CxP,
│                      # Comprobantes RC-/CE-, Parámetros tributarios/nómina,
│                      # Motor de asientos (partida doble)
├── ventas/            # Productos, Clientes, VentaDocumento, VentaDetalle
├── compras/           # Proveedor, CompraDocumento, CompraDetalle
├── inventario/        # MovimientoInventario (kardex), AjusteInventario
├── reportes/          # Aging, P&L, Balance General, Libro Diario, Retenciones
├── usuarios/          # Usuario, RefreshToken
├── tenancy/           # Tenant, onboarding multi-empresa
├── ventas_diarias/    # VentaDiaria, PagoSueltoDiario (tenant Perú)
├── auditoria/         # Log inmutable de cambios con diff
└── alegra/            # Cliente HTTP + mappers para API Alegra

frontend/src/
├── services/          # ventasApi, comprasApi, carteraApi, inventarioApi, ...
├── utils/             # printFactura, printCompra, printComprobante, printCotizacion
└── views/             # DashboardView, VentasView, ComprasView, CarteraView,
                       # InventarioView, ReportesView, PucView, UsuariosView, ...
```

---

## Inicio rápido — Windows

### Prerequisitos

- Python 3.11 o superior
- Node.js 18 o superior
- Git

### 1. Clonar el repositorio

```bash
git clone https://github.com/leonardeco/Lanxa-ERP.git
cd Lanxa-ERP
```

### 2. Configurar variables de entorno

El archivo `.env` ya está preconfigurado para desarrollo local con SQLite. Para personalizarlo usa `.env.example` como referencia:

```bash
cp .env.example .env
# Edita .env con tus valores
```

Para producción con PostgreSQL:

```bash
cp .env.produccion .env
# Edita con las credenciales reales
```

> **Migraciones:** el proyecto usa **Alembic** (config async en `backend/alembic/`). El `create_all()` del lifespan actúa como red de seguridad en desarrollo, pero **todo cambio de esquema nuevo debe ir por migración**:
>
> ```bash
> cd backend
> alembic revision --autogenerate -m "descripcion"
> alembic upgrade head
> alembic check
> ```

### 3. Instalar dependencias

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 4. Arrancar el sistema

**Opción A — Doble clic (recomendado):**

```
start.bat
```

**Opción B — Manual (dos terminales):**

```bash
# Una sola vez: genera certs/ (CA local + cert de servidor para HTTPS)
cd backend
venv\Scripts\python.exe scripts\generate_tls_cert.py

# Terminal 1 — Backend
venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  --ssl-keyfile ..\certs\server.key --ssl-certfile ..\certs\server.crt

# Terminal 2 — Frontend
cd frontend
node node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5173
```

El primer arranque ejecuta automáticamente los seeders: PUC completo (Decreto 2650), centros de costo, períodos contables, parámetros tributarios y de nómina, y usuario administrador.

### 5. Acceder

| Servicio | URL |
|----------|-----|
| Aplicación | https://localhost:5173 |
| API Docs (Swagger) | https://localhost:8000/docs |

**Credenciales por defecto:**

```
Email:      admin@lanxa.local
Contraseña: Admin2026!
```

> Cambia la contraseña desde **Usuarios & Accesos → Cambiar mi contraseña** en el primer inicio.

El navegador marcará la conexión como no segura hasta que instales `certs/lanxa-ca.crt` como certificado raíz de confianza (una vez por PC). Ver `DOCUMENTACION.md`, sección 6.

### Acceso directo de escritorio (opcional)

Ejecuta `crear-acceso-escritorio.bat` (doble clic) para crear un ícono **"Lanxa ERP"** en el escritorio que abre `start.bat` directamente.

### Base de datos demo (pruebas de UI)

Para probar la interfaz con volumen realista (~50 clientes, ~200 ventas):

```bash
cd backend
python -m seeds.seed_demo --clean --clientes 50 --ventas 200
```

- `--clean` borra y recrea la BD demo (idempotente). Sin `--clean`, el script se niega a correr si ya hay datos.
- El script **aborta** si la URL demo coincide con la de producción.

---

## Inicio rápido — Docker

### Prerequisitos

- Docker Desktop

### 1. Configurar entorno

```bash
cp .env.produccion .env
# Edita .env — SECRET_KEY y credenciales PostgreSQL obligatorios
```

### 2. Levantar servicios

```bash
docker-compose up -d
```

| Servicio | URL |
|----------|-----|
| Aplicación | http://localhost |
| API | http://localhost:8000/docs |
| pgAdmin | http://localhost:5050 |

---

## Variables de entorno

| Variable | Req. | Descripción |
|----------|:----:|-------------|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://...` (prod) · `sqlite+aiosqlite:///./lanxa.db` (dev) |
| `SECRET_KEY` | ✅ | Clave JWT — mínimo 32 chars, recomendado 64. Genera: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `POSTGRES_USER` | Docker | Usuario PostgreSQL |
| `POSTGRES_PASSWORD` | Docker | Contraseña PostgreSQL |
| `POSTGRES_DB` | Docker | Nombre de la base de datos |
| `REDIS_URL` | — | `redis://redis:6379/0` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | Expiración del access token (default: 15) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | — | Expiración del refresh token (default: 30) |
| `CORS_ORIGINS` | — | Orígenes permitidos (coma). **Nunca `*` en producción** |
| `DEBUG` | — | `true` en desarrollo · `false` en producción |
| `EMPRESA_RAZON_SOCIAL` | — | Nombre de la empresa (default: `LANXA S.A.S.`) |
| `EMPRESA_NIT` | — | NIT de la empresa |
| `EMPRESA_CIUDAD` | — | Ciudad de la empresa |
| `SEED_DEMO` | — | `false` (default): solo datos base · `true`: agrega productos/clientes de ejemplo |
| `AUDITORIA_RETENTION_DAYS` | — | Días de retención en log de auditoría (default: 1825 ≈ 5 años) |
| `ALEGRA_EMAIL` | Alegra | Email de la cuenta Alegra |
| `ALEGRA_TOKEN` | Alegra | Token API Alegra (`Configuración → API`) |

---

## Testing & QA

El proyecto tiene **tres capas de cobertura**:

| Capa | Herramienta | Cantidad |
|------|-------------|:--------:|
| API backend | pytest + httpx | 394 tests (+1 xfailed documentado) |
| Componentes frontend | Vitest + Testing Library | 25 tests |
| Flujos E2E | Playwright | 5 flujos en navegador real |

### Instalar dependencias de desarrollo

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
```

### Correr las pruebas

```bash
# Backend — requiere PostgreSQL
docker run -d --name pg-test -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=superozono_test postgres:16-alpine

cd backend
export TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/superozono_test
pytest -v

# Análisis estático backend
flake8 app/
mypy app/

# Frontend
cd frontend
npm run lint          # ESLint + TypeScript
npm run test          # Vitest
npm run test:e2e      # Playwright (levanta backend + frontend automáticamente)
```

### CI/CD

`.github/workflows/ci.yml` ejecuta en cada push/PR a `main`:
- Lint + tipos + tests con cobertura (backend)
- ESLint + tsc + Vitest + build (frontend)
- `pip-audit` (seguridad de dependencias)

Dependabot propone actualizaciones semanales de dependencias.

Configura hooks de pre-commit (opcional):

```bash
pip install pre-commit
pre-commit install
```

---

## API Reference

Documentación interactiva completa en `/docs` (Swagger UI) y `/redoc` cuando el backend está corriendo.

### Endpoints principales

```
# Auth
POST   /api/login/access-token            Login → JWT (access + refresh cookie)
POST   /api/login/refresh-token           Rota el refresh token
POST   /api/login/logout                  Revoca el refresh token
GET    /api/users/me                      Usuario autenticado actual

# Dashboard
GET    /api/v1/contabilidad/dashboard     Stats contabilidad
GET    /api/v1/ventas/dashboard           Stats ventas del mes

# Contabilidad
GET    /api/v1/contabilidad/puc
GET    /api/v1/contabilidad/centros-costo
GET    /api/v1/contabilidad/periodos
GET    /api/v1/contabilidad/parametros-tributarios
GET    /api/v1/contabilidad/parametros-nomina
GET    /api/v1/contabilidad/asientos
GET    /api/v1/contabilidad/terceros/{id}/auxiliar

# Cartera
GET    /api/v1/contabilidad/cartera/stats
GET    /api/v1/contabilidad/cartera/cxc
POST   /api/v1/contabilidad/cartera/cxc/{id}/abonar   # genera RC-0001…
PATCH  /api/v1/contabilidad/cartera/cxc/{id}/anular
GET    /api/v1/contabilidad/cartera/cxp
POST   /api/v1/contabilidad/cartera/cxp/{id}/abonar   # genera CE-0001…
PATCH  /api/v1/contabilidad/cartera/cxp/{id}/anular
GET    /api/v1/contabilidad/cartera/pagos
POST   /api/v1/contabilidad/cartera/pagos/{id}/anular  # reverso contable

# Ventas
GET    /api/v1/ventas/productos
POST   /api/v1/ventas/productos
GET    /api/v1/ventas/clientes
POST   /api/v1/ventas/clientes
GET    /api/v1/ventas/documentos
POST   /api/v1/ventas/documentos
POST   /api/v1/ventas/{id}/devoluciones   # nota crédito NC-

# Compras
GET    /api/v1/compras/dashboard
GET    /api/v1/compras/proveedores
POST   /api/v1/compras/proveedores
GET    /api/v1/compras/
POST   /api/v1/compras/                   # crea en borrador
POST   /api/v1/compras/{id}/confirmar     # CxP automática + entradas de inventario
POST   /api/v1/compras/{id}/anular
POST   /api/v1/compras/{id}/devoluciones  # devolución a proveedor ND-

# Inventario
GET    /api/v1/inventario/dashboard
GET    /api/v1/inventario/movimientos     # kardex completo
POST   /api/v1/inventario/ajustes         # ajuste manual (Admin/Administradora)

# Reportes
GET    /api/v1/reportes/aging-cartera
GET    /api/v1/reportes/compras-periodo
GET    /api/v1/reportes/ventas-periodo
GET    /api/v1/reportes/retenciones-periodo
GET    /api/v1/reportes/estado-resultados
GET    /api/v1/reportes/balance-general

# Usuarios
GET    /api/v1/usuarios
POST   /api/v1/usuarios
PUT    /api/v1/usuarios/{id}
PATCH  /api/v1/usuarios/{id}/toggle
PUT    /api/v1/usuarios/me/password
PUT    /api/v1/usuarios/{id}/reset-password

# Multi-tenancy
GET    /api/v1/tenants/
POST   /api/v1/tenants/onboard

# Alegra
GET    /api/v1/alegra/status
POST   /api/v1/alegra/facturas/{venta_id}
```

> **Sin registro público:** este ERP es un sistema interno. Los usuarios se crean exclusivamente por un Admin vía `POST /api/v1/usuarios`. Esto es intencional, no un gap.

### Niveles de acceso

| Nivel | Ejemplo | Mecanismo |
|-------|---------|-----------|
| Público | `POST /api/login/access-token` | Validación bcrypt → JWT |
| Autenticado | `GET /api/users/me` | Bearer JWT → `get_current_user` → 401 |
| Cualquier rol | `GET /api/v1/ventas/*` | JWT válido (cualquier rol activo) |
| Admin / Administradora | `POST /api/v1/inventario/ajustes` | JWT + guard de rol → 403 |
| Solo Admin | `POST /api/v1/usuarios/*` | JWT + `get_current_active_superuser` → 403 |

---

## Seguridad

### Implementado

| Práctica | Detalle |
|----------|---------|
| **CORS restrictivo** | Orígenes configurables vía `CORS_ORIGINS`, sin wildcard `*` |
| **Hash de contraseñas** | bcrypt cost factor 12 (`app/core/security.py`) |
| **Middleware de autenticación** | Todo endpoint protegido valida JWT → 401 si falta o expirado |
| **RBAC con Guards** | Backend valida rol → 403 si no aplica. Frontend oculta opciones según rol |
| **Protección SQL Injection** | 100% ORM SQLAlchemy — cero SQL crudo concatenado |
| **Secretos fuera de código** | `.env` excluido de git; solo se versionan plantillas `.env.example` |
| **Rate limiting en login** | `slowapi`, 5 intentos/min por IP → 429 al superarse |
| **Refresh tokens con rotación** | Access token 15min. Refresh opaco en cookie `HttpOnly + SameSite=Strict`, hash en BD, rotado en cada uso y revocable |
| **HTTPS con CA local** | Uvicorn + Vite sirven TLS con cert firmado por CA local (`scripts/generate_tls_cert.py`) |
| **Backups cifrados** | `scripts/backup_db.py` — copia consistente cifrada con Fernet, retención 30 días |
| **Reset de contraseña por Admin** | `PUT /api/v1/usuarios/{id}/reset-password` — sin email, el Admin comunica la nueva clave |
| **`rol` con CHECK constraint en BD** | La BD rechaza roles fuera de `Admin/Administradora/Auxiliar` directamente |

### Riesgos conocidos / pendientes

| Ítem | Riesgo | Recomendación |
|------|--------|---------------|
| **Clave de cifrado de backups** | Sin `BACKUP_ENCRYPTION_KEY` los `.enc` no se pueden restaurar | Guardar en gestor de contraseñas. Offsite diario: OneDrive `Lanxa-Backups-Offsite` |
| **IDs secuenciales** | `Integer autoincrement` — IDs adivinables | Aceptable en LAN cerrada; migrar a UUID si se expone la API públicamente |

---

## Roles y permisos

El sistema tiene **5 roles**. Detalle canónico en `DOCUMENTACION.md` §7:

| Rol | Descripción | Acceso principal |
|-----|-------------|-----------------|
| **Admin** | Dueño técnico del sistema | Todo + Usuarios + Alegra + onboard tenant |
| **Directora** | Operación y dirección administrativa | Contabilidad, ventas, compras, cartera, inventario, reportes (puede anular) |
| **CEO** | Visión ejecutiva | Dashboard, reportes y consulta de operación |
| **Contador** | Área contable | Contabilidad, cartera, reportes, ventas/compras (sin anular) |
| **Auxiliar Contable** | Operación contable | Contabilidad, ventas, compras, cartera, reportes (sin anular) |

---

## Documentos del proyecto

| Documento | Destinatario |
|-----------|-------------|
| [`MANUAL-DE-USUARIO.md`](./MANUAL-DE-USUARIO.md) | Usuarios finales — guía por flujos (vender, cobrar, comprar, pagar) |
| [`DESPLIEGUE.md`](./DESPLIEGUE.md) | Administrador — checklist de actualización y rollback con backups |
| [`MAPEO-PUC-PARA-CONTADOR.md`](./MAPEO-PUC-PARA-CONTADOR.md) | Contador(a) — validación del mapeo contable del motor de asientos |
| [`BITACORA.md`](./BITACORA.md) | Desarrollo — registro de sesiones |
| [`PENDIENTES.md`](./PENDIENTES.md) | Todos — backlog priorizado: qué falta y de quién depende |
| [`DOCUMENTACION.md`](./DOCUMENTACION.md) | Técnico — arquitectura, modelos, seguridad, multi-PC |

---

## Roadmap

### Fase 1 — Completada
- [x] Auth JWT + RBAC (5 roles)
- [x] Módulo Contabilidad (PUC, períodos, parámetros tributarios y nómina)
- [x] Módulo Ventas (productos, clientes, facturas, impresión PDF)
- [x] Módulo Compras & Proveedores (CRUD, documentos, impresión PDF)
- [x] Cartera CxC & CxP (abonos, aging, CxP automática desde compras)
- [x] Gestión de Usuarios
- [x] Dashboard dinámico
- [x] Integración Alegra (base construida)

### Fase 2 — Completada
- [x] Inventario — entradas/salidas automáticas, reversa al anular (2026-06-17)
- [x] Comprobante de pago numerado al registrar abono CxC/CxP (2026-06-17)
- [x] Lote & vencimiento FEFO, UI, enganche stock (2026-07-10)
- [x] Devoluciones NC- y ND- con reverso parcial (2026-07-03)
- [x] Alertas de vencimiento CxC/CxP en Dashboard (2026-07-02)

### Fase 3 — Completada
- [x] Reportes & BI — aging, compras/ventas por período, retenciones (2026-06-17)
- [x] Motor de asientos partida doble + reverso al anular (2026-07-02)
- [x] P&L y Balance General con verificación de ecuación contable (2026-07-02)
- [x] Libro Diario consultable con asientos expandibles y export Excel (2026-07-02)

### Fase 4 — Multi-tenancy (Completada)
- [x] Modelo `Tenant`, `tenant_id` en toda tabla de negocio, RLS PostgreSQL (2026-07-15)
- [x] Onboarding de empresas nuevas `POST /api/v1/tenants/onboard` (2026-07-15)
- [x] Tenant Perú + módulo Ventas Diarias (2026-07-24)
- [x] Auditoría de aislamiento cross-tenant — 8 módulos corregidos con TDD (2026-07-27)

### Fase 5 — En curso
- [ ] RRHH — Empleados y contratos
- [ ] Liquidación de nómina mensual
- [ ] Activación Alegra con facturación electrónica DIAN
- [ ] Login por dominio de email (multi-tenant)
- [ ] Migración `UniqueConstraint`s globales → compuestos por `tenant_id`

---

*LANXA S.A.S. — 2026*
