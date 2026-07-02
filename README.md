# Super Ozono ERP

[![CI](https://github.com/leonardeco/superozono-erp/actions/workflows/ci.yml/badge.svg)](https://github.com/leonardeco/superozono-erp/actions/workflows/ci.yml)

Sistema de gestión empresarial (ERP) desarrollado a medida para **TECNOLOGÍA E INNOVACIÓN SUPER OZONO S.A.S.** — empresa colombiana del sector agroindustrial especializada en biocidas naturales con tecnología de ozono.

> **Stack:** FastAPI · React 19 · TypeScript · SQLAlchemy 2.0 async · PostgreSQL / SQLite · Docker Compose

---

## Tabla de contenido

- [Módulos](#módulos)
- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Modelo de datos](#modelo-de-datos)
- [Inicio rápido — Windows](#inicio-rápido--windows)
- [Inicio rápido — Docker](#inicio-rápido--docker)
- [Variables de entorno](#variables-de-entorno)
- [API Reference](#api-reference)
- [Seguridad](#seguridad)
- [Roles y permisos](#roles-y-permisos)
- [Roadmap](#roadmap)

---

## Módulos

| Módulo | Estado | Descripción |
|--------|--------|-------------|
| **Auth & Seguridad** | ✅ Producción | JWT + bcrypt, RBAC con 3 roles, sesión por token |
| **Dashboard** | ✅ Producción | Stats en tiempo real: contabilidad + ventas del mes + cartera |
| **Contabilidad** | ✅ Producción | PUC (Decreto 2650), Centros de Costo, Períodos, Parámetros tributarios y de nómina |
| **Ventas & Comercial** | ✅ Producción | Productos (catálogo multimarca), Clientes B2B, Documentos de venta con retenciones, impresión PDF |
| **Compras & Proveedores** | ✅ Producción | CRUD proveedores, documentos de compra con retenciones, confirmación/anulación, impresión PDF |
| **Cartera CxC & CxP** | ✅ Producción | CxC y CxP con abonos, aging automático, CxP generada automáticamente al confirmar compras, comprobante de pago numerado (Recibo de Caja / Comprobante de Egreso) |
| **Inventario** | ✅ Producción | Kardex de movimientos (Entrada/Salida/Ajuste), entradas automáticas al confirmar compra, salidas automáticas al confirmar venta, reversa al anular, dashboard de valorización |
| **Usuarios** | ✅ Producción | CRUD de usuarios, gestión de roles, cambio de contraseña |
| **Alegra** | ✅ Construido | Integración con API de Alegra para facturación electrónica DIAN Colombia |
| **RRHH & Nómina** | 🔄 Fase 2 | Empleados, contratos, liquidación mensual |
| **Reportes & BI** | ✅ Producción | Aging de cartera (CxC/CxP), compras y ventas por período (proveedor/cliente/marca), retenciones acumuladas. P&L y Balance General requieren motor de asientos contables, ver roadmap |
| **Electron** | 🔄 Fase 4 | Empaquetado como aplicación de escritorio (.exe) |

---

## Arquitectura

```
superozono-erp/
├── backend/              # FastAPI — API REST async
│   └── app/
│       ├── api/          # Dependencias compartidas (auth, sesión DB)
│       ├── core/         # Config, database, security (JWT + bcrypt)
│       ├── modules/      # Módulos de negocio
│       └── main.py       # App factory + lifespan (create_all + seeds)
├── frontend/             # React 19 + TypeScript + Vite
│   └── src/
│       ├── components/   # Sidebar, HeaderBar, StatusBar
│       ├── contexts/     # AuthContext (JWT decode + /users/me)
│       ├── services/     # API clients (axios) por módulo
│       ├── utils/        # printFactura.ts, printCompra.ts
│       └── views/        # Una vista por módulo
├── docker-compose.yml    # PostgreSQL 16 + Redis 7 + pgAdmin 4
├── frontend/Dockerfile   # Nginx + Vite build para producción
├── start.bat             # Inicio local Windows (doble clic)
└── stop.bat              # Parada limpia Windows
```

**Flujo de arquitectura (Docker):**

```
+----------------------------------------------------+
|                      CLIENTE                        |
|       Navegador -- React 19 SPA (build estatico)    |
+------------------------+-----------------------------+
                         |  HTTP (LAN) -- sin TLS en esta version
                         v
+----------------------------------------------------+
|          CONTENEDOR frontend -- nginx:alpine        |
|  - Sirve el build de React (dist/)                  |
|  - Proxy interno: /api, /docs, /redoc -> backend:8000 |
+------------------------+-----------------------------+
                         v
+----------------------------------------------------+
|        CONTENEDOR backend -- FastAPI (Python 3.13)  |
|  +-------------------+   +------------------------+ |
|  | Auth (JWT+bcrypt) |   |  Modulos de negocio    | |
|  | deps.py -> 401/403|   |  Contabilidad/Ventas/..| |
|  +-------------------+   +------------------------+ |
+------------+-------------------------+--------------+
             v                         v
   +-------------------+     +-------------------+
   |   PostgreSQL 16    |     |      Redis 7      |
   |   (datos del ERP)  |     |  (cache, opcional) |
   +-------------------+     +-------------------+

CONTENEDOR pgadmin (puerto 5050) -- administracion de BD, uso interno
Orquestacion: Docker Compose (docker-compose.yml)
```

**Patrón de módulos backend:**

```
modules/<nombre>/
├── models.py     # SQLAlchemy ORM models
├── schemas.py    # Pydantic v2 request/response
└── router.py     # FastAPI APIRouter con endpoints
```

---

## Stack tecnológico

### Backend

| Librería | Versión | Uso |
|----------|---------|-----|
| FastAPI | 0.115 | Framework web async |
| SQLAlchemy | 2.0 | ORM async — PostgreSQL y SQLite |
| Pydantic | 2.11 | Validación y serialización |
| python-jose | 3.5 | Generación y verificación JWT |
| passlib + bcrypt | 1.7 / 4.3 | Hash seguro de contraseñas |
| httpx | 0.28 | Cliente HTTP async (Alegra API) |
| structlog | 25.4 | Logging estructurado JSON |
| aiosqlite | 0.20 | Driver SQLite async (desarrollo local) |
| asyncpg | 0.30 | Driver PostgreSQL async (producción) |
| uvicorn | 0.34 | Servidor ASGI |
| pytest + httpx | 9.1 | Entorno de testing unitario y asíncrono |
| flake8 + mypy | 7.3 / 2.1 | Análisis estático y verificación de tipos (QA) |

### Frontend

| Librería | Versión | Uso |
|----------|---------|-----|
| React | 19 | UI |
| TypeScript | 6.0 | Tipado estático |
| Vite | 8.0 | Bundler y dev server |
| Axios | 1.17 | HTTP client con interceptores JWT |
| jwt-decode | 4.0 | Decodificación de token en cliente |

### Infraestructura (Docker)

| Servicio | Imagen | Puerto |
|----------|--------|--------|
| API Backend | Python 3.13 + uvicorn | 8000 |
| Frontend | nginx + Vite build | 80 |
| PostgreSQL | postgres:16-alpine | 5432 |
| Redis | redis:7-alpine | 6379 |
| pgAdmin | dpage/pgadmin4 | 5050 |

---

## Estructura del proyecto

```
backend/app/modules/
├── contabilidad/
│   ├── models.py    # PlanCuentas, CentroCosto, PeriodoContable,
│   │                # CuentaPorCobrar, CuentaPorPagar (con compra_id),
│   │                # Pago (comprobante RC-/CE- por cada abono),
│   │                # ParametroTributario, ParametroNomina
│   ├── schemas.py   # Pydantic schemas + CarteraStats + PagoResponse
│   └── router.py    # /api/v1/contabilidad/* (PUC, centros, periodos,
│                    # cartera CxC/CxP con sincronización a compras y
│                    # generación de comprobante de pago numerado)
├── ventas/
│   ├── models.py    # Producto, Cliente, VentaDocumento, VentaDetalle
│   ├── schemas.py   # CRUD schemas + VentaDashboard
│   └── router.py    # /api/v1/ventas/*
├── compras/
│   ├── models.py    # Proveedor, CompraDocumento, CompraDetalle (con producto_id opcional)
│   ├── schemas.py   # CRUD schemas + ComprasDashboard
│   └── router.py    # /api/v1/compras/* (al confirmar → crea CxP + entrada de inventario)
├── inventario/
│   ├── models.py    # MovimientoInventario (kardex: Entrada/Salida/Ajuste)
│   ├── schemas.py   # MovimientoResponse, AjusteInventarioInput, InventarioDashboard
│   ├── service.py   # registrar_movimiento() — actualiza stock + crea el movimiento
│   └── router.py    # /api/v1/inventario/* (dashboard, movimientos, ajustes manuales)
├── reportes/
│   ├── schemas.py   # AgingCarteraResponse, ComprasPeriodoResponse, VentasPeriodoResponse, RetencionesPeriodoResponse
│   └── router.py    # /api/v1/reportes/* (solo lectura, sin modelos propios)
├── usuarios/
│   ├── models.py    # Usuario (email, rol, bcrypt hash)
│   ├── schemas.py   # Token, UsuarioCreate/Update/Response
│   └── router.py    # /api/login, /api/users/me, /api/v1/usuarios/*
└── alegra/
    ├── client.py    # HTTP client Basic Auth → api.alegra.com/api/v1
    ├── mappers.py   # ERP models → Alegra JSON format
    └── router.py    # /api/v1/alegra/*

frontend/src/
├── services/
│   ├── api.ts              # Axios base con interceptor JWT
│   ├── dashboardApi.ts     # Stats dashboard
│   ├── ventasApi.ts        # Productos, clientes, ventas
│   ├── comprasApi.ts       # Proveedores, compras (con producto_id), dashboard compras
│   ├── inventarioApi.ts    # Dashboard, movimientos (kardex), ajustes manuales
│   ├── reportesApi.ts      # Aging, compras/ventas por periodo, retenciones
│   ├── carteraApi.ts       # CxC, CxP (con compra_id), Pago, stats
│   ├── contabilidadApi.ts  # PUC, centros, periodos, tributarios, nomina
│   └── usuariosApi.ts      # CRUD usuarios + cambio contraseña
├── utils/
│   ├── printFactura.ts     # Impresión PDF documentos de venta
│   ├── printCompra.ts      # Impresión PDF documentos de compra
│   └── printComprobante.ts # Impresión Recibo de Caja (CxC) / Comprobante de Egreso (CxP)
└── views/
    ├── DashboardView.tsx    # Stats dinámicas + ventas por marca
    ├── PucView.tsx          # Plan Único de Cuentas
    ├── CentrosCostoView.tsx # Centros de costo por marca
    ├── PeriodosView.tsx     # Períodos contables
    ├── TributariosView.tsx  # Parámetros IVA, retenciones
    ├── NominaView.tsx       # Parámetros SMMLV, aportes
    ├── VentasView.tsx       # Dashboard + Productos + Clientes + Facturas
    ├── ComprasView.tsx      # Dashboard + Proveedores + Compras + Nueva Compra
    ├── InventarioView.tsx   # Dashboard + Productos (stock) + Movimientos + Ajuste manual
    ├── ReportesView.tsx     # Aging cartera + Compras/Ventas por periodo + Retenciones
    ├── CarteraView.tsx      # CxC & CxP con abonos, comprobante automático e historial de pagos
    ├── UsuariosView.tsx     # CRUD usuarios (Admin)
    └── LoginView.tsx        # Autenticación
```

---

## Modelo de datos

Tabla de entidades principales con campos sensibles, tipos y restricciones de seguridad. El detalle completo de todas las tablas está en [`DOCUMENTACION.md`](./DOCUMENTACION.md#8-base-de-datos--modelos).

| Entidad | Campo | Tipo | Restricción de seguridad |
|---|---|---|---|
| `usuarios` | `id` | `Integer` autoincrement | **No es UUID** — ID secuencial. Ver nota abajo |
| `usuarios` | `email` | `String(255)` | `UNIQUE`, `NOT NULL` |
| `usuarios` | `hashed_password` | `String(255)` | Hash **bcrypt** (passlib, cost factor 12 por defecto). Nunca se almacena ni se loguea texto plano |
| `usuarios` | `rol` | `String(50)` | Valores válidos: `Admin`, `Administradora`, `Auxiliar`. **No es un ENUM de BD**, pero tiene `CHECK constraint` (`ROLES_VALIDOS` en `models.py`) — un `INSERT`/`UPDATE` directo con otro valor lo rechaza la propia BD |
| `usuarios` | `is_active` | `Boolean` | Controla acceso; verificado en cada request autenticado (`get_current_user`) |
| `*` (todas las tablas) | `id` | `Integer` autoincrement | Mismo patrón en todos los módulos (Contabilidad, Ventas, Compras, Inventario) |

> **Nota — IDs secuenciales:** todos los modelos del proyecto usan `Integer, primary_key=True, autoincrement=True` (no UUID). Esto es simple y suficiente para una red LAN cerrada de 5 PCs, pero implica que los IDs son adivinables/enumerables. Si en el futuro se expone la API fuera de la LAN, se recomienda migrar a UUID o agregar control de autorización por objeto (verificar que el recurso pertenece/es visible para el rol del usuario, no solo el rol global).

> **Nota — `rol` sin ENUM real:** el campo se valida solo en la capa de aplicación (Pydantic/lógica de negocio), no en la base de datos. Se recomienda agregar un `CHECK` constraint o usar `Enum` de SQLAlchemy para que un valor de rol inválido no pueda insertarse directamente en la BD.

---

## Testing & Quality Assurance

El proyecto cuenta con una infraestructura automatizada para asegurar su integridad y reducir bugs:

- **Pruebas Unitarias y de Integración (Backend)**: Usando `pytest`, `pytest-asyncio` y `httpx`. Las pruebas levantan automáticamente una base de datos `SQLite` en memoria que se crea y destruye limpiamente con cada ejecución, validando el correcto funcionamiento de la API, la inyección de JWT, y los dashboards de módulos como Inventario.
- **Análisis Estático Continuo (Linter & Type Checking)**: `flake8` y `mypy` se encargan de detectar errores de código, dependencias sin uso, o violaciones lógicas de Python (como `E712`). En el frontend, `ESLint` protege las reglas de hooks de React y la sintaxis de TypeScript.

Las herramientas de QA se instalan aparte de las dependencias de runtime:

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
```

La configuración vive en `backend/.flake8` (línea máx. 120), `backend/mypy.ini` y `backend/pytest.ini`. Además, `.github/workflows/ci.yml` corre lint + tipos + tests (backend) y ESLint + tsc + build (frontend) en cada push/PR a `main`.

**Para correr las pruebas:**

```bash
# Ejecutar Tests del Backend (Unitarios)
cd backend
pytest -v

# Analizadores Estáticos (Backend)
cd backend
flake8 app/
mypy app/

# Analizadores Estáticos (Frontend)
cd frontend
npm run lint
```

---

## Inicio rápido — Windows

### Prerequisitos

- Python 3.11+
- Node.js 18+
- Git

### 1. Clonar el repositorio

```bash
git clone https://github.com/leonardeco/superozono-erp.git
cd superozono-erp
```

### 2. Configurar variables de entorno

El archivo `.env` ya está configurado para desarrollo local con SQLite. Si necesitas personalizarlo, usa `.env.example` como referencia de todas las variables disponibles:

```bash
cp .env.example .env
# Edita .env con tus valores — el backend busca backend/.env
```

Para producción con PostgreSQL usa `.env.produccion` como plantilla:

```bash
cp .env.produccion .env
# Edita .env con las credenciales reales
```

> **Nota — migraciones de base de datos:** el proyecto usa **Alembic** (configuración async en `backend/alembic/`, URL tomada del `.env` de la app). Existe una migración *baseline* con el esquema completo; las BD creadas antes de Alembic ya están marcadas con `alembic stamp head`. El `create_all()` del lifespan (`app/main.py`) se mantiene como red de seguridad en desarrollo, pero **todo cambio de esquema nuevo debe hacerse por migración**:
>
> ```bash
> cd backend
> alembic revision --autogenerate -m "descripcion del cambio"   # generar
> alembic upgrade head                                          # aplicar
> alembic check                                                 # verificar que modelos y BD están en sync
> ```

### 3. Instalar dependencias backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Instalar dependencias frontend

```bash
cd frontend
npm install
```

### 5. Arrancar el sistema

**Opción A — Doble clic (recomendado):**
```
start.bat
```

**Opción B — Manual (dos terminales):**

```bash
# Una sola vez: genera certs/ (CA local + certificado de servidor para HTTPS)
cd backend
venv\Scripts\python.exe scripts\generate_tls_cert.py

# Terminal 1 — Backend
venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile ..\certs\server.key --ssl-certfile ..\certs\server.crt

# Terminal 2 — Frontend (toma el certificado solo automaticamente desde vite.config.ts)
cd frontend
node node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5173
```

El primer arranque ejecuta automáticamente los seeders con datos base (PUC completo según Decreto 2650, centros de costo por marca, períodos contables, parámetros tributarios y de nómina).

**Acceso directo de escritorio (opcional, una sola vez):**

Ejecuta `crear-acceso-escritorio.bat` (doble clic) para crear un ícono **"Super Ozono ERP"** en el escritorio con el logo de la empresa, que al abrirlo ejecuta `start.bat`. Usa la carpeta donde está el proyecto en *ese* PC — funciona igual si copias el proyecto a otra máquina, solo hay que volver a ejecutarlo ahí (no se puede copiar el `.lnk` directamente porque apunta a una ruta absoluta).

### 6. Acceder

| Servicio | URL |
|----------|-----|
| Aplicación | https://localhost:5173 |
| API Docs (Swagger) | https://localhost:8000/docs |

El navegador va a marcar la conexión como no segura hasta que se instale `certs/superozono-ca.crt` como certificado raíz de confianza (una vez por PC) — ver `DOCUMENTACION.md`, sección 6, para el detalle multi-PC.

**Credenciales por defecto:**

```
Email:      admin@superozonoglobal.com
Contraseña: Admin2026!
```

> Cambia la contraseña desde **Usuarios & Accesos → Cambiar mi contraseña** en el primer inicio.

---

## Inicio rápido — Docker

### Prerequisitos

- Docker Desktop

### 1. Configurar entorno

```bash
cp .env.produccion .env
# Edita .env con SECRET_KEY y credenciales PostgreSQL reales
```

### 2. Levantar servicios

```bash
docker-compose up -d
```

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost |
| API | http://localhost:8000 |
| pgAdmin | http://localhost:5050 |

---

## Variables de entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://...` (prod) o `sqlite+aiosqlite:///./superozono.db` (dev) |
| `SECRET_KEY` | ✅ | Clave JWT, **mínimo 32 caracteres** (recomendado 64) — genera con `python -c "import secrets; print(secrets.token_hex(32))"` |
| `POSTGRES_USER` | Docker | Usuario PostgreSQL |
| `POSTGRES_PASSWORD` | Docker | Contraseña PostgreSQL |
| `POSTGRES_DB` | Docker | Nombre de la base de datos |
| `REDIS_URL` | No | `redis://redis:6379/0` |
| `ACCESS_TOKEN_EXPIRE_HOURS` | No | Expiración JWT en horas (default: 8) |
| `CORS_ORIGINS` | No | Orígenes permitidos separados por coma (default: `http://localhost:5173,http://127.0.0.1:5173`). **En producción nunca usar `*`** — listar explícitamente los orígenes reales |
| `DEBUG` | No | `true` en desarrollo, `false` en producción |
| `ALEGRA_EMAIL` | Alegra | Email de la cuenta Alegra |
| `ALEGRA_TOKEN` | Alegra | Token API de Alegra (`Configuración → API`) |

> **Nota:** el backend no expone una variable `PORT`/`NODE_ENV` (no aplica al stack FastAPI/Vite). El puerto del backend (8000) y del frontend (5173 en dev, 80 en Docker) se fija directamente en los comandos de arranque y en `docker-compose.yml`.

---

## API Reference

Documentación interactiva completa en `/docs` cuando el backend está corriendo.

### Endpoints principales

```
# Auth
POST   /api/login/access-token            Login → JWT
GET    /api/users/me                      Usuario actual

# Dashboard
GET    /api/v1/contabilidad/dashboard     Stats contabilidad
GET    /api/v1/ventas/dashboard           Stats ventas del mes

# Contabilidad
GET    /api/v1/contabilidad/puc
GET    /api/v1/contabilidad/centros-costo
GET    /api/v1/contabilidad/periodos
GET    /api/v1/contabilidad/parametros-tributarios
GET    /api/v1/contabilidad/parametros-nomina

# Cartera
GET    /api/v1/contabilidad/cartera/stats
GET    /api/v1/contabilidad/cartera/cxc
POST   /api/v1/contabilidad/cartera/cxc/{id}/abonar   # genera Recibo de Caja (RC-0001...)
PATCH  /api/v1/contabilidad/cartera/cxc/{id}/anular
GET    /api/v1/contabilidad/cartera/cxp
POST   /api/v1/contabilidad/cartera/cxp/{id}/abonar   # genera Comprobante de Egreso (CE-0001...), sincroniza estado_pago en compra
PATCH  /api/v1/contabilidad/cartera/cxp/{id}/anular
GET    /api/v1/contabilidad/cartera/pagos             # historial de comprobantes (filtro cxc_id / cxp_id)

# Inventario
GET    /api/v1/inventario/dashboard
GET    /api/v1/inventario/movimientos                 # kardex completo (filtros producto/tipo/origen/fecha)
GET    /api/v1/inventario/movimientos/{producto_id}
POST   /api/v1/inventario/ajustes                     # ajuste manual de stock (Admin/Administradora)

# Reportes
GET    /api/v1/reportes/aging-cartera                 # CxC y CxP por buckets de vencimiento
GET    /api/v1/reportes/compras-periodo               # ?fecha_desde=&fecha_hasta= (default: mes actual)
GET    /api/v1/reportes/ventas-periodo                # idem, agrupado por cliente y por marca
GET    /api/v1/reportes/retenciones-periodo           # retefuente/reteIVA/reteICA de compras + ventas

# Ventas
GET    /api/v1/ventas/productos
POST   /api/v1/ventas/productos
GET    /api/v1/ventas/clientes
POST   /api/v1/ventas/clientes
GET    /api/v1/ventas/documentos
POST   /api/v1/ventas/documentos

# Compras & Proveedores
GET    /api/v1/compras/dashboard
GET    /api/v1/compras/proveedores
POST   /api/v1/compras/proveedores
PUT    /api/v1/compras/proveedores/{id}
DELETE /api/v1/compras/proveedores/{id}
GET    /api/v1/compras/
POST   /api/v1/compras/                   # crea en borrador
POST   /api/v1/compras/{id}/confirmar     # confirma + genera CxP automática + entradas de inventario
POST   /api/v1/compras/{id}/anular

# Usuarios
GET    /api/v1/usuarios
POST   /api/v1/usuarios
PUT    /api/v1/usuarios/{id}
PATCH  /api/v1/usuarios/{id}/toggle
PUT    /api/v1/usuarios/me/password
PUT    /api/v1/usuarios/{id}/reset-password    # solo Admin, para usuarios sin acceso

# Alegra
GET    /api/v1/alegra/status
GET    /api/v1/alegra/taxes
POST   /api/v1/alegra/sync/cliente/{id}
POST   /api/v1/alegra/sync/producto/{id}
POST   /api/v1/alegra/facturas/{venta_id}
```

> **Sin registro público:** este ERP es un sistema interno (no SaaS), por lo que **no existe** un endpoint de auto-registro (`POST /auth/register`). Los usuarios se crean exclusivamente por un Admin vía `POST /api/v1/usuarios`. Esto es intencional, no un gap.

### Niveles de acceso

| Método | Endpoint (ejemplo) | Nivel de acceso | Mecanismo de seguridad |
|--------|---------------------|------------------|--------------------------|
| `POST` | `/api/login/access-token` | Público | Validación de credenciales (bcrypt) → emisión de JWT |
| `GET` | `/api/users/me` | Autenticado | Bearer JWT → `get_current_user` → 401 si inválido/expirado |
| `GET`/`POST` | `/api/v1/ventas/*`, `/api/v1/compras/*`, `/api/v1/inventario/*` | Autenticado | Bearer JWT (cualquier rol activo) → 401 si falla |
| `POST` | `/api/v1/inventario/ajustes` | Admin / Administradora | JWT + `get_admin_or_administradora` → 403 si el rol no aplica |
| `POST`/`PUT`/`PATCH` | `/api/v1/usuarios/*` | Admin | JWT + `get_current_active_superuser` → 403 si no es Admin |

---

## Seguridad

Estado real de las prácticas de seguridad del proyecto — qué está implementado y qué queda pendiente antes de exponerlo fuera de la LAN interna.

### Implementado

| Práctica | Detalle |
|---|---|
| **CORS restrictivo** | Orígenes configurables vía `CORS_ORIGINS`, sin wildcard `*` (`app/main.py`) |
| **Hash de contraseñas** | bcrypt vía `passlib` (`app/core/security.py`), cost factor 12 (default) |
| **Middleware de autenticación** | Todo endpoint protegido valida el JWT vía `get_current_user`; responde `401` si falta o es inválido (`app/api/deps.py`) |
| **RBAC con Guards** | Backend valida rol con `get_admin_or_administradora` / `get_current_active_superuser` → `403` si no aplica. Frontend oculta opciones de menú/acciones según `rol` del usuario en `AuthContext` |
| **Protección contra SQL Injection** | 100% de las consultas usan el ORM de SQLAlchemy (`select()`/queries parametrizadas) — no hay SQL crudo concatenado en el proyecto |
| **Secretos fuera de código** | Credenciales y `SECRET_KEY` viven en archivos `.env` excluidos de git (`.gitignore`); solo se versionan plantillas (`.env.example`, `.env.produccion`) sin valores reales |
| **Rate limiting en login** | `slowapi`, 5 intentos/min por IP, storage en memoria (`app/core/limiter.py`) — mitiga fuerza bruta en `POST /api/login/access-token`; responde `429` al superarse |
| **Refresh tokens con rotación** | Access token bajado a `ACCESS_TOKEN_EXPIRE_HOURS=1`. Refresh token opaco (no JWT) en cookie `HTTPOnly` + `SameSite=Strict`, hash en BD (tabla `refresh_tokens`), rotado en cada uso (`POST /api/login/refresh-token`) y revocable de verdad (`POST /api/login/logout`) — ya no depende solo de borrar el token del navegador |
| **Backups automatizados (SQLite)** | `backend/scripts/backup_db.py`, tarea diaria en el Programador de tareas de Windows (`SuperOzonoERP-BackupDB`, 2:00am). Copia consistente vía la API de backup de `sqlite3`, cifrada con Fernet (`cryptography`), retención 30 días. Restauración con `backend/scripts/restore_db.py` (guarda una copia `.bak` antes de sobreescribir) |
| **HTTPS con CA local** | `nginx.conf` no aplica (es del stack Docker, no del modo `start.bat` real). `uvicorn` y Vite sirven TLS directo con un certificado de servidor firmado por una CA local autofirmada (`backend/scripts/generate_tls_cert.py`, librería `cryptography`) — no hay dominio público, así que Let's Encrypt no es viable. La cookie del refresh token ya va con `Secure=True`. Pendiente manual: instalar `certs/superozono-ca.crt` como confiable en los 4 PCs cliente (ver `DOCUMENTACION.md`, sección 6) |
| **Reset de contraseña por Admin** | `PUT /api/v1/usuarios/{id}/reset-password` (solo Admin) — un usuario sin acceso ya no depende de conocer su contraseña actual para recuperarla. Sin flujo de email/token: el proyecto no tiene infraestructura de correo, el Admin comunica la contraseña nueva por fuera del sistema |
| **`rol` con CHECK constraint en BD** | `usuarios.rol` ya no depende solo de la validación de la API — la BD rechaza un `INSERT`/`UPDATE` directo con un rol fuera de `Admin`/`Administradora`/`Auxiliar` (`ROLES_VALIDOS` en `models.py`, una sola fuente de verdad). Migración para la BD existente en `backend/scripts/migrate_rol_constraint.py` (SQLite no soporta `ALTER TABLE ADD CONSTRAINT`, recrea la tabla) |

### Pendiente / riesgos conocidos

| Ítem | Riesgo | Recomendación |
|---|---|---|
| **Backups guardados en el mismo PC** | `C:/SuperOzono-Backups` está en el mismo disco que la BD real — si el PC servidor falla por completo (disco, robo, incendio), se pierden la BD, los backups y la clave de cifrado (`BACKUP_ENCRYPTION_KEY` en `backend/.env`) al mismo tiempo | Copiar periódicamente la carpeta de backups (y la clave, en un gestor de contraseñas) a un destino fuera de este PC: red local, NAS o nube |
| **IDs secuenciales** | Todas las tablas usan `Integer autoincrement` — los IDs son adivinables/enumerables | Aceptable en LAN cerrada; si se expone la API públicamente, migrar a UUID o reforzar autorización por objeto |

---

## Roles y permisos

El sistema tiene 3 roles, diseñados para una red LAN de 5 PCs:

| Rol | Descripción | Módulos accesibles |
|-----|-------------|-------------------|
| **Admin** | PC servidor — acceso total | Todo el sistema |
| **Administradora** | PC administrativo | Dashboard, Contabilidad, Ventas, Compras, Cartera |
| **Auxiliar** | 3 PCs operativos | Dashboard, Ventas, Compras, Cartera |

---

## Roadmap

### Fase 1 — Completada
- [x] Auth JWT + RBAC (3 roles)
- [x] Módulo Contabilidad (PUC, períodos, parámetros tributarios y nómina)
- [x] Módulo Ventas (productos, clientes, facturas, impresión PDF)
- [x] Módulo Compras & Proveedores (CRUD, documentos, impresión PDF)
- [x] Cartera CxC & CxP (abonos, aging, CxP automática desde compras)
- [x] Gestión de Usuarios
- [x] Dashboard dinámico
- [x] Integración Alegra (base construida)

### Fase 2
- [x] Inventario — entradas automáticas al confirmar compra, salidas al confirmar venta, reversa al anular (2026-06-17)
- [x] Comprobante de pago numerado al registrar abono en CxC/CxP (2026-06-17)
- [ ] Módulo RRHH (empleados, contratos)
- [ ] Liquidación de nómina mensual
- [ ] Activación Alegra con facturación electrónica DIAN

### Fase 3
- [x] Reportes & BI — aging cartera, compras/ventas por período, retenciones acumuladas (2026-06-17)
- [ ] P&L y Balance General — requieren motor de asientos contables automáticos (partida doble al confirmar venta/compra/abono), que hoy no existe. Proyecto separado, pendiente de planear
- [ ] Devoluciones en ventas y compras
- [ ] Notificaciones y alertas de vencimiento CxP

### Fase 4
- [ ] Empaquetado Electron (app de escritorio .exe)
- [ ] Auditoría completa (log de cambios por usuario)

---

## Empresa

**TECNOLOGÍA E INNOVACIÓN SUPER OZONO S.A.S.**
NIT: 901.841.798-5
Armenia, Quindío — Colombia
Sector: Agroindustria / Biocidas naturales con tecnología de ozono

---

*Desarrollado a medida para Super Ozono Global — 2026*
