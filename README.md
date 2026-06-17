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
| **Reportes & BI** | 🔄 Fase 3 | P&L, Balance General, cartera aging, compras por período |
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
    ├── CarteraView.tsx      # CxC & CxP con abonos, comprobante automático e historial de pagos
    ├── UsuariosView.tsx     # CRUD usuarios (Admin)
    └── LoginView.tsx        # Autenticación
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

El archivo `.env` ya está configurado para desarrollo local con SQLite. Si necesitas personalizarlo:

```bash
# El backend busca backend/.env — ya existe con SQLite por defecto
```

Para producción con PostgreSQL usa `.env.produccion` como plantilla:

```bash
cp .env.produccion .env
# Edita .env con las credenciales reales
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
cd backend
venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend
node node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5173
```

El primer arranque ejecuta automáticamente los seeders con datos base (PUC completo según Decreto 2650, centros de costo por marca, períodos contables, parámetros tributarios y de nómina).

### 6. Acceder

| Servicio | URL |
|----------|-----|
| Aplicación | http://localhost:5173 |
| API Docs (Swagger) | http://localhost:8000/docs |

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
| `SECRET_KEY` | ✅ | Clave JWT — genera con `python -c "import secrets; print(secrets.token_hex(32))"` |
| `POSTGRES_USER` | Docker | Usuario PostgreSQL |
| `POSTGRES_PASSWORD` | Docker | Contraseña PostgreSQL |
| `POSTGRES_DB` | Docker | Nombre de la base de datos |
| `REDIS_URL` | No | `redis://redis:6379/0` |
| `ACCESS_TOKEN_EXPIRE_HOURS` | No | Expiración JWT en horas (default: 8) |
| `DEBUG` | No | `true` en desarrollo, `false` en producción |
| `ALEGRA_EMAIL` | Alegra | Email de la cuenta Alegra |
| `ALEGRA_TOKEN` | Alegra | Token API de Alegra (`Configuración → API`) |

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

# Alegra
GET    /api/v1/alegra/status
GET    /api/v1/alegra/taxes
POST   /api/v1/alegra/sync/cliente/{id}
POST   /api/v1/alegra/sync/producto/{id}
POST   /api/v1/alegra/facturas/{venta_id}
```

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
- [ ] Reportes & BI (P&L, Balance General, aging cartera, compras por período)
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
