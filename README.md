# Super Ozono ERP

Sistema de gestión empresarial (ERP) desarrollado a medida para **TECNOLOGÍA E INNOVACIÓN SUPER OZONO S.A.S.** — empresa colombiana del sector agroindustrial especializada en biocidas naturales con tecnología de ozono.

> **Stack:** FastAPI · React 19 · TypeScript · SQLAlchemy 2.0 async · PostgreSQL / SQLite · Docker Compose

---

## Tabla de contenido

- [Módulos](#módulos)
- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Inicio rápido — Windows](#inicio-rápido--windows)
- [Inicio rápido — Docker](#inicio-rápido--docker)
- [Variables de entorno](#variables-de-entorno)
- [API Reference](#api-reference)
- [Roles y permisos](#roles-y-permisos)
- [Roadmap](#roadmap)

---

## Módulos

| Módulo | Estado | Descripción |
|--------|--------|-------------|
| **Auth & Seguridad** | ✅ Producción | JWT RS256, RBAC con 6 roles, refresh token |
| **Contabilidad** | ✅ Producción | PUC (Decreto 2650), Centros de Costo, Períodos, Parámetros tributarios y de nómina |
| **Ventas & Comercial** | ✅ Producción | Productos (catálogo multimarca), Clientes B2B, Documentos de venta con retenciones |
| **Cartera** | ✅ Producción | Cuentas por cobrar (CxC) y por pagar (CxP), abonos, aging automático |
| **Usuarios** | ✅ Producción | CRUD de usuarios, gestión de roles, cambio de contraseña |
| **Dashboard** | ✅ Producción | Stats en tiempo real desde la API: contabilidad + ventas del mes + cartera |
| **Alegra** | ✅ Construido | Integración con API de Alegra para facturación electrónica DIAN Colombia |
| **Inventario** | 🔄 Fase 1 | Entradas/salidas, ajustes, valorización por marca |
| **Proveedores** | 🔄 Fase 2 | CRUD proveedores, órdenes de compra |
| **RRHH & Nómina** | 🔄 Fase 2 | Empleados, contratos, liquidación mensual |
| **Reportes & BI** | 🔄 Fase 4 | P&L, Balance General, cartera aging, ventas por período |
| **Electron** | 🔄 Fase 4 | Empaquetado como aplicación de escritorio (.exe) |

---

## Arquitectura

```
superozono-erp/
├── backend/          # FastAPI — API REST async
│   └── app/
│       ├── api/      # Dependencias compartidas (auth, sesión DB)
│       ├── core/     # Config, database, security (JWT + bcrypt)
│       ├── modules/  # Módulos de negocio (contabilidad, ventas, alegra...)
│       └── main.py   # App factory + lifespan (migrations + seeds)
├── frontend/         # React 19 + TypeScript + Vite
│   └── src/
│       ├── components/   # Sidebar, HeaderBar, StatusBar
│       ├── contexts/     # AuthContext (JWT decode + /users/me)
│       ├── services/     # API clients (axios) por módulo
│       └── views/        # Una vista por módulo
├── docker-compose.yml    # PostgreSQL 16 + Redis 7 + pgAdmin 4
├── start.bat             # Inicio local Windows (doble clic)
├── stop.bat              # Parada limpia Windows
└── .env.example          # Plantilla de variables de entorno
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
| SQLAlchemy | 2.0 | ORM async con soporte PostgreSQL y SQLite |
| Pydantic | 2.11 | Validación y serialización |
| python-jose | 3.5 | Generación y verificación JWT |
| passlib + bcrypt | 1.7 / 4.3 | Hash seguro de contraseñas |
| httpx | 0.28 | Cliente HTTP async (Alegra API) |
| structlog | 25.4 | Logging estructurado JSON |
| aiosqlite | 0.20 | Driver SQLite async (desarrollo local) |
| asyncpg | 0.30 | Driver PostgreSQL async (producción) |
| uvicorn | 0.34 | Servidor ASGI |

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
| PostgreSQL | postgres:16-alpine | 5432 |
| Redis | redis:7-alpine | 6379 |
| pgAdmin | dpage/pgadmin4 | 5050 |

---

## Estructura del proyecto

```
backend/app/modules/
├── contabilidad/
│   ├── models.py    # PlanCuentas, CentroCosto, PeriodoContable, Tercero,
│   │                # CuentaPorCobrar, CuentaPorPagar, ParametroTributario,
│   │                # ParametroNomina
│   ├── schemas.py   # Pydantic schemas + DashboardStats + CarteraStats
│   └── router.py    # /api/v1/contabilidad/* (PUC, centros, periodos, cartera)
├── ventas/
│   ├── models.py    # Producto, Cliente, VentaDocumento, VentaDetalle
│   ├── schemas.py   # CRUD schemas + VentaDashboardStats
│   └── router.py    # /api/v1/ventas/* (productos, clientes, facturas, dashboard)
├── usuarios/
│   ├── models.py    # Usuario (email, rol, bcrypt hash)
│   ├── schemas.py   # Token, UsuarioCreate/Update/Response
│   └── router.py    # /api/login, /api/users/me, /api/v1/usuarios/*
└── alegra/
    ├── client.py    # HTTP client Basic Auth → api.alegra.com/api/v1
    ├── mappers.py   # ERP models → Alegra JSON format
    └── router.py    # /api/v1/alegra/* (status, taxes, sync, facturas)

frontend/src/
├── services/
│   ├── api.ts          # Axios base con interceptor JWT
│   ├── dashboardApi.ts # /contabilidad/dashboard + /ventas/dashboard
│   ├── ventasApi.ts    # Productos, clientes, ventas
│   ├── carteraApi.ts   # CxC, CxP, stats
│   └── usuariosApi.ts  # CRUD usuarios + cambio contraseña
└── views/
    ├── DashboardView.tsx    # Stats dinámicas + ventas por marca
    ├── PucView.tsx          # Plan Único de Cuentas
    ├── CentrosCostoView.tsx # Centros de costo por marca
    ├── PeriodosView.tsx     # Períodos contables 2026
    ├── TributariosView.tsx  # Parámetros IVA, retenciones
    ├── NominaView.tsx       # Parámetros SMMLV, aportes
    ├── VentasView.tsx       # Dashboard + Productos + Clientes + Facturas
    ├── CarteraView.tsx      # CxC & CxP con abonos y aging
    ├── UsuariosView.tsx     # CRUD usuarios (Superadmin)
    └── LoginView.tsx        # Autenticación OAuth2
```

---

## Inicio rápido — Windows

### Prerequisitos

- Python 3.11+
- Node.js 18+

### 1. Clonar el repositorio

```bash
git clone https://github.com/leonardeco/superozono-erp.git
cd superozono-erp
```

### 2. Configurar variables de entorno

```bash
# Backend (desarrollo local con SQLite)
cp .env.example backend/.env
```

Edita `backend/.env` y completa al menos:

```env
DATABASE_URL=sqlite+aiosqlite:///./superozono.db
SECRET_KEY=genera-una-clave-con-python-secrets-token-hex-32
```

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
# Terminal 1 — Backend
cd backend && venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
node node_modules/vite/bin/vite.js --port 5173
```

El primer arranque ejecuta automáticamente los seeders con datos base (PUC, centros de costo, períodos contables, parámetros tributarios, productos de ejemplo, clientes de ejemplo).

### 6. Acceder

| Servicio | URL |
|----------|-----|
| Aplicación | http://localhost:5173 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

**Credenciales por defecto:**

```
Email:      admin@superozonoglobal.com
Contraseña: Admin2026!
```

> ⚠️ Cambia la contraseña del administrador en el primer inicio desde **Usuarios & Accesos → Cambiar mi contraseña**.

---

## Inicio rápido — Docker

### Prerequisitos

- Docker Desktop

### 1. Configurar entorno

```bash
cp .env.example .env
```

Edita `.env` con las credenciales de PostgreSQL y la `SECRET_KEY`.

### 2. Levantar servicios

```bash
docker-compose up -d
```

| Servicio | URL |
|----------|-----|
| API | http://localhost:8000 |
| pgAdmin | http://localhost:5050 |

> El frontend en Docker requiere un contenedor adicional (nginx). Por ahora corre localmente con `npm run dev` apuntando al backend en `localhost:8000`.

---

## Variables de entorno

Copia `.env.example` como `.env` (raíz para Docker, `backend/.env` para desarrollo local).

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://...` (prod) o `sqlite+aiosqlite:///./superozono.db` (dev) |
| `SECRET_KEY` | ✅ | Clave secreta JWT — genera con `python -c "import secrets; print(secrets.token_hex(32))"` |
| `POSTGRES_USER` | Docker | Usuario PostgreSQL |
| `POSTGRES_PASSWORD` | Docker | Contraseña PostgreSQL |
| `POSTGRES_DB` | Docker | Nombre de la base de datos |
| `REDIS_URL` | No | `redis://redis:6379/0` (por defecto) |
| `ACCESS_TOKEN_EXPIRE_HOURS` | No | Expiración JWT en horas (default: 8) |
| `DEBUG` | No | `true` en desarrollo, `false` en producción |
| `ALEGRA_EMAIL` | Alegra | Email de la cuenta Alegra |
| `ALEGRA_TOKEN` | Alegra | Token de API de Alegra (`Configuración → API`) |
| `PGADMIN_EMAIL` | Docker | Email de acceso a pgAdmin |
| `PGADMIN_PASSWORD` | Docker | Contraseña de pgAdmin |

---

## API Reference

La documentación interactiva completa está disponible en `/docs` (Swagger UI) o `/redoc` cuando el backend está corriendo.

### Endpoints principales

```
# Auth
POST   /api/login/access-token          Login → JWT
GET    /api/users/me                    Usuario actual

# Dashboard
GET    /api/v1/contabilidad/dashboard   Stats contabilidad
GET    /api/v1/ventas/dashboard         Stats ventas del mes

# Contabilidad
GET    /api/v1/contabilidad/puc         Plan de Cuentas
GET    /api/v1/contabilidad/centros-costo
GET    /api/v1/contabilidad/periodos
GET    /api/v1/contabilidad/parametros-tributarios
GET    /api/v1/contabilidad/parametros-nomina

# Cartera
GET    /api/v1/contabilidad/cartera/stats
GET    /api/v1/contabilidad/cartera/cxc
POST   /api/v1/contabilidad/cartera/cxc
POST   /api/v1/contabilidad/cartera/cxc/{id}/abonar
PATCH  /api/v1/contabilidad/cartera/cxc/{id}/anular
GET    /api/v1/contabilidad/cartera/cxp
POST   /api/v1/contabilidad/cartera/cxp
POST   /api/v1/contabilidad/cartera/cxp/{id}/abonar

# Ventas
GET    /api/v1/ventas/productos
POST   /api/v1/ventas/productos
GET    /api/v1/ventas/clientes
POST   /api/v1/ventas/clientes
GET    /api/v1/ventas/documentos
POST   /api/v1/ventas/documentos

# Usuarios (Superadmin)
GET    /api/v1/usuarios
POST   /api/v1/usuarios
PUT    /api/v1/usuarios/{id}
PATCH  /api/v1/usuarios/{id}/toggle
PUT    /api/v1/usuarios/me/password

# Alegra
GET    /api/v1/alegra/status
GET    /api/v1/alegra/taxes
POST   /api/v1/alegra/sync/cliente/{id}
POST   /api/v1/alegra/sync/producto/{id}
POST   /api/v1/alegra/facturas/{venta_id}
```

---

## Roles y permisos

| Rol | Módulos accesibles |
|-----|--------------------|
| **Superadmin** | Todo — incluyendo usuarios y configuración |
| **Contabilidad** | Dashboard, PUC, Centros de Costo, Períodos, Tributarios, Nómina, Cartera |
| **Ventas** | Dashboard, Ventas & Comercial |
| **Bodega** | Dashboard, Inventario |
| **RRHH** | Dashboard, Nómina, Talento Humano |
| **Solo lectura** | Dashboard, Reportes |

---

## Roadmap

### Fase 1 — En progreso
- [x] Auth JWT + RBAC
- [x] Módulo Contabilidad (PUC, períodos, parámetros)
- [x] Módulo Ventas (productos, clientes, documentos)
- [x] Cartera CxC & CxP
- [x] Gestión de Usuarios
- [x] Dashboard dinámico
- [x] Integración Alegra (base construida)
- [ ] Inventario (pendiente datos)

### Fase 2
- [ ] Proveedores y órdenes de compra
- [ ] Módulo RRHH (empleados, contratos)
- [ ] Liquidación de nómina
- [ ] Activación Alegra con facturación electrónica DIAN

### Fase 3
- [ ] Devoluciones en ventas
- [ ] Integración Mercado Libre
- [ ] Notificaciones y alertas

### Fase 4
- [ ] Reportes & BI (P&L, Balance General, aging cartera)
- [ ] Empaquetado Electron (app de escritorio .exe)
- [ ] Auditoría completa (log de cambios por usuario)

---

## Empresa

**TECNOLOGÍA E INNOVACIÓN SUPER OZONO S.A.S.**  
NIT: 901841798-5  
Armenia, Quindío — Colombia  
Sector: Agroindustria / Biocidas naturales con tecnología de ozono

---

*Desarrollado con ❤️ para Super Ozono Global — 2026*
