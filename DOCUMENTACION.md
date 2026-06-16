# Super Ozono Global — ERP: Documentación Técnica

**Empresa:** TECNOLOGIA E INNOVACION SUPER OZONO S.A.S.
**NIT:** 901841798-5
**Ciudad:** Armenia, Quindío
**Versión ERP:** 0.4.0
**Última actualización:** 2026-06-16

---

## Tabla de contenido

1. [Descripción general](#1-descripción-general)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Estructura del proyecto](#3-estructura-del-proyecto)
4. [Configuración y variables de entorno](#4-configuración-y-variables-de-entorno)
5. [Cómo ejecutar el sistema](#5-cómo-ejecutar-el-sistema)
6. [Despliegue en red LAN](#6-despliegue-en-red-lan)
7. [Sistema de roles y permisos](#7-sistema-de-roles-y-permisos)
8. [Base de datos — Modelos](#8-base-de-datos--modelos)
9. [Backend — Endpoints API](#9-backend--endpoints-api)
10. [Frontend — Vistas y módulos](#10-frontend--vistas-y-módulos)
11. [Módulo Alegra (facturación electrónica)](#11-módulo-alegra-facturación-electrónica)
12. [Datos semilla (Seeds)](#12-datos-semilla-seeds)
13. [Pendientes y roadmap](#13-pendientes-y-roadmap)

---

## 1. Descripción general

ERP interno para la gestión contable y comercial de Super Ozono Global. Diseñado para funcionar en red local (LAN) con 5 equipos:

| Equipo | Rol | Acceso |
|---|---|---|
| PC Servidor | Admin | Todo el sistema |
| PC Administradora | Administradora | Módulos contables + ventas + cartera |
| PC Auxiliar 1, 2, 3 | Auxiliar | Ventas y cartera únicamente |

**Arquitectura:** un PC actúa como servidor (corre backend + frontend), los otros 4 solo abren el navegador.

---

## 2. Stack tecnológico

### Backend
| Componente | Tecnología | Versión |
|---|---|---|
| Framework web | FastAPI | 0.115.12 |
| Servidor ASGI | Uvicorn | 0.34.3 |
| ORM | SQLAlchemy (async) | 2.0.41 |
| Base de datos (dev) | SQLite + aiosqlite | 0.20.0 |
| Base de datos (prod) | PostgreSQL 16 | — |
| Migraciones | Alembic | 1.15.2 |
| Validación | Pydantic v2 | 2.11.3 |
| Autenticación | JWT (python-jose) | 3.5.0 |
| Hashing contraseñas | passlib + bcrypt | 1.7.4 |
| Logging | structlog | 25.4.0 |
| HTTP cliente | httpx | 0.28.1 |

### Frontend
| Componente | Tecnología |
|---|---|
| Framework UI | React 18 + TypeScript |
| Build tool | Vite |
| HTTP client | Axios |
| Estilos | CSS custom (variables) |

### Infraestructura (producción)
| Servicio | Imagen Docker |
|---|---|
| Backend API | Python/FastAPI |
| Base de datos | postgres:16-alpine |
| Caché y colas | redis:7-alpine |
| Admin DB | dpage/pgadmin4 |
| Frontend | nginx (pendiente) |

---

## 3. Estructura del proyecto

```
superozono-erp/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── deps.py              # Dependencias: auth, roles, sesión DB
│   │   ├── core/
│   │   │   ├── config.py            # Settings (pydantic-settings, .env)
│   │   │   ├── database.py          # Engine SQLAlchemy async + sesión
│   │   │   └── security.py          # JWT, hash contraseñas
│   │   ├── modules/
│   │   │   ├── contabilidad/
│   │   │   │   ├── models.py        # PUC, CentroCosto, Periodos, Terceros, CxC, CxP, etc.
│   │   │   │   ├── schemas.py       # Pydantic schemas
│   │   │   │   └── router.py        # Endpoints contabilidad y cartera
│   │   │   ├── ventas/
│   │   │   │   ├── models.py        # Producto, Cliente, VentaDocumento, VentaDetalle
│   │   │   │   ├── schemas.py       # Pydantic schemas
│   │   │   │   └── router.py        # Endpoints ventas
│   │   │   ├── usuarios/
│   │   │   │   ├── models.py        # Usuario
│   │   │   │   ├── schemas.py       # Token, UsuarioCreate, UsuarioResponse
│   │   │   │   └── router.py        # Auth + CRUD usuarios
│   │   │   └── alegra/
│   │   │       ├── client.py        # Cliente HTTP para Alegra API
│   │   │       ├── mappers.py       # Conversores ERP → Alegra
│   │   │       └── router.py        # Endpoints sincronización y facturación
│   │   └── main.py                  # App FastAPI, CORS, routers, lifespan
│   ├── seeds/
│   │   └── seed.py                  # Datos iniciales: PUC, centros, períodos, productos, clientes
│   ├── .env                         # Variables de entorno (desarrollo local)
│   ├── .env.servidor                # Plantilla para el PC servidor (copiar a .env)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── Dockerfile               # Multi-stage: Node build → nginx
│   ├── nginx.conf               # SPA fallback + proxy /api → backend:8000
│   ├── .env                     # Dev local (VITE_API_URL=localhost) — gitignored
│   ├── .env.production          # Docker prod (VITE_API_URL=/api) — relativo
│   ├── .env.servidor            # Plantilla para start.bat en servidor (IP fija)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── HeaderBar.tsx
│   │   │   └── StatusBar.tsx
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx      # Estado global de autenticación
│   │   ├── services/
│   │   │   ├── api.ts               # Instancia Axios con token JWT y URL dinámica
│   │   │   ├── ventasApi.ts
│   │   │   ├── dashboardApi.ts
│   │   │   ├── usuariosApi.ts
│   │   │   └── carteraApi.ts
│   │   ├── views/
│   │   │   ├── LoginView.tsx
│   │   │   ├── DashboardView.tsx
│   │   │   ├── PucView.tsx
│   │   │   ├── CentrosCostoView.tsx
│   │   │   ├── PeriodosView.tsx
│   │   │   ├── TributariosView.tsx
│   │   │   ├── NominaView.tsx
│   │   │   ├── VentasView.tsx       # 4 pestañas: Dashboard, Productos, Clientes, Facturas
│   │   │   ├── CarteraView.tsx      # CxC y CxP con abonos y anulaciones
│   │   │   └── UsuariosView.tsx     # Gestión de usuarios (solo Admin)
│   │   ├── App.tsx                  # Enrutador por vistas + control de roles
│   │   └── main.tsx
│   ├── .env                         # VITE_API_URL para desarrollo local
│   └── .env.servidor                # Plantilla con IP del servidor para producción
├── docker-compose.yml               # Backend + Frontend nginx + PostgreSQL + Redis + pgAdmin
├── .env.produccion                  # Template de variables para Docker (copiar a .env)
├── start.bat                        # Inicia backend y frontend en Windows (dev/LAN sin Docker)
├── stop.bat                         # Detiene los procesos
└── DOCUMENTACION.md                 # Este archivo
```

---

## 4. Configuración y variables de entorno

### Backend — `backend/.env`

```env
# Base de datos (dev: SQLite / prod: PostgreSQL)
DATABASE_URL=sqlite+aiosqlite:///./superozono.db
REDIS_URL=redis://localhost:6379/0

# Seguridad
SECRET_KEY=<clave-secreta-larga>
ACCESS_TOKEN_EXPIRE_HOURS=8
REFRESH_TOKEN_EXPIRE_DAYS=30
DEBUG=true

# CORS — orígenes permitidos separados por coma
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Empresa
EMPRESA_NIT=901841798-5
EMPRESA_RAZON_SOCIAL=TECNOLOGIA E INNOVACION SUPER OZONO S.A.S.
EMPRESA_CIUDAD=Armenia, Quindio

# Alegra (opcional — facturación electrónica)
ALEGRA_EMAIL=
ALEGRA_TOKEN=
```

**En el PC servidor (reemplazar IP):**
```env
DATABASE_URL=postgresql+asyncpg://usuario:password@localhost:5432/superozono
CORS_ORIGINS=http://192.168.X.X:5173
```

### Frontend — `frontend/.env`

```env
# Desarrollo local
VITE_API_URL=http://localhost:8000/api
```

**En el PC servidor:**
```env
VITE_API_URL=http://192.168.X.X:8000/api
```

---

## 5. Cómo ejecutar el sistema

### Desarrollo local (este PC)

```bat
start.bat
```

Esto abre dos ventanas de cmd:
- `Backend — FastAPI :8000` → `http://localhost:8000/docs`
- `Frontend — Vite :5173` → `http://localhost:5173`

**Credenciales iniciales:**
```
Email:      admin@superozonoglobal.com
Contraseña: Admin2026!
```

### Con Docker (producción — PC Servidor)

1. Copiar el template de variables:
   ```bash
   cp .env.produccion .env
   ```

2. Editar `.env` y cambiar las contraseñas y `SECRET_KEY`.

3. Levantar todos los servicios:
   ```bash
   docker compose up -d --build
   ```

4. Los otros 4 PCs abren el navegador en `http://192.168.X.X` (puerto 80).

Servicios disponibles:
| Servicio | URL | Descripción |
|---|---|---|
| Frontend (nginx) | http://IP-servidor | App React compilada |
| API docs | http://IP-servidor/docs | Swagger UI |
| Backend directo | http://IP-servidor:8000 | Solo para debug |
| pgAdmin | http://IP-servidor:5050 | Administrador BD |

---

## 6. Despliegue en red LAN

### Configuración en el PC servidor

1. Averiguar la IP del servidor:
   ```cmd
   ipconfig
   ```
   Anotar la IPv4 (ej: `192.168.1.10`)

2. Editar `backend/.env`:
   ```env
   CORS_ORIGINS=http://192.168.1.10:5173
   ```

3. Editar `frontend/.env`:
   ```env
   VITE_API_URL=http://192.168.1.10:8000/api
   ```

4. Ejecutar `start.bat` en el servidor.

### En los otros 4 PCs (solo navegador)

Abrir Chrome/Edge y navegar a:
```
http://192.168.1.10:5173
```

No requieren instalación de ningún software.

> **Nota:** `start.bat` ya está configurado con `--host 0.0.0.0` tanto para uvicorn como para Vite, por lo que el servidor es visible en toda la red local.

---

## 7. Sistema de roles y permisos

### Roles disponibles

| Rol | Descripción |
|---|---|
| `Admin` | Acceso total. Único que puede crear/editar/desactivar usuarios |
| `Administradora` | Módulos contables + ventas + cartera. Sin gestión de usuarios |
| `Auxiliar` | Solo ventas y cartera. Sin acceso a configuración contable |

### Acceso por módulo

| Módulo | Admin | Administradora | Auxiliar |
|---|---|---|---|
| Dashboard | ✅ | ✅ | ✅ |
| Ventas | ✅ | ✅ | ✅ |
| Cartera (CxC/CxP) | ✅ | ✅ | ✅ |
| PUC | ✅ | ✅ | ❌ |
| Centros de Costo | ✅ | ✅ | ❌ |
| Períodos Contables | ✅ | ✅ | ❌ |
| Parámetros Tributarios | ✅ | ✅ | ❌ |
| Parámetros Nómina | ✅ | ✅ | ❌ |
| Gestión de Usuarios | ✅ | ❌ | ❌ |
| Inventario (fase 2) | ✅ | ❌ | ❌ |
| RRHH (fase 2) | ✅ | ❌ | ❌ |
| Reportes (fase 2) | ✅ | ❌ | ❌ |

### Implementación técnica

**Backend (`api/deps.py`):**

| Dependencia | Alias | Roles permitidos |
|---|---|---|
| `get_current_user` | `CurrentUser` | Admin, Administradora, Auxiliar |
| `get_admin_or_administradora` | `AdminOrAdministradoraDep` | Admin, Administradora |
| `get_current_active_superuser` | `AdminDep` | Admin únicamente |

**Reglas aplicadas por módulo:**

- **Contabilidad** (PUC, centros, períodos, terceros, tributarios, nómina): `AdminOrAdministradoraDep`
- **Cartera GET / CREATE / UPDATE**: `CurrentUser` (todos los roles)
- **Cartera abonar / anular**: `AdminOrAdministradoraDep`
- **Ventas GET / crear venta / confirmar venta**: `CurrentUser` (todos los roles)
- **Ventas crear/editar/desactivar productos y clientes**: `AdminOrAdministradoraDep`
- **Ventas anular**: `AdminOrAdministradoraDep`
- **Usuarios CRUD**: `AdminDep`
- **Alegra** (sync y facturación): `AdminDep`

**Frontend (`App.tsx`):**
- `ROLE_VIEWS` mapea cada rol a sus vistas permitidas
- Al navegar a una vista no permitida, redirige al dashboard
- El sidebar filtra los ítems según `allowedViews`

---

## 8. Base de datos — Modelos

### Módulo Contabilidad (`contabilidad/models.py`)

| Tabla | Descripción |
|---|---|
| `plan_cuentas` | PUC colombiano (Decreto 2650). Código, nombre, clase, naturaleza, nivel |
| `centros_costo` | Centros de costo por marca (10 marcas) y área (Administración, Logística) |
| `periodos_contables` | Períodos mensuales con estado Abierto/Cerrado |
| `terceros` | Clientes, proveedores y empleados unificados |
| `asientos_contables` | Cabecera de cada movimiento contable |
| `movimientos_asiento` | Líneas de débito/crédito (partida doble) |
| `saldos_iniciales` | Balance de apertura por cuenta |
| `cuentas_por_cobrar` | CxC: facturas pendientes de cobro |
| `cuentas_por_pagar` | CxP: documentos pendientes de pago |
| `parametros_tributarios` | IVA, retefuente, reteIVA, reteICA, ICA |
| `parametros_nomina` | Salud, pensión, ARL, parafiscales |

### Módulo Ventas (`ventas/models.py`)

| Tabla | Descripción |
|---|---|
| `productos` | Catálogo con SKU, marca, precio, IVA, stock, registro ICA |
| `clientes` | Clientes B2B con NIT, régimen, contacto, cupo de crédito |
| `ventas_documentos` | Cabecera de factura interna (SOG-V-XXXX) con totales y retenciones |
| `ventas_detalles` | Líneas de producto con cálculo de descuento e IVA |

### Módulo Usuarios (`usuarios/models.py`)

| Tabla | Descripción |
|---|---|
| `usuarios` | Email, nombre, contraseña hasheada, rol, estado activo |

---

## 9. Backend — Endpoints API

Base URL: `http://[host]:8000/api`

### Autenticación

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/login/access-token` | Público | Login. Retorna JWT Bearer token |
| GET | `/users/me` | Autenticado | Datos del usuario en sesión |

### Usuarios

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/v1/usuarios` | Admin | Listar todos los usuarios |
| POST | `/v1/usuarios` | Admin | Crear usuario |
| PUT | `/v1/usuarios/{id}` | Admin | Editar nombre y rol |
| PATCH | `/v1/usuarios/{id}/toggle` | Admin | Activar/desactivar usuario |
| PUT | `/v1/usuarios/me/password` | Autenticado | Cambiar contraseña propia |

### Contabilidad

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/v1/contabilidad/dashboard` | Stats generales contables |
| GET | `/v1/contabilidad/puc` | Listar PUC completo |
| GET | `/v1/contabilidad/puc/{codigo}` | Obtener cuenta por código |
| POST | `/v1/contabilidad/puc` | Crear cuenta PUC |
| PUT | `/v1/contabilidad/puc/{id}` | Editar nombre y flags de cuenta PUC |
| PATCH | `/v1/contabilidad/puc/{id}/toggle` | Activar/desactivar cuenta PUC |
| GET | `/v1/contabilidad/centros-costo` | Listar centros de costo |
| POST | `/v1/contabilidad/centros-costo` | Crear centro de costo |
| PUT | `/v1/contabilidad/centros-costo/{id}` | Editar centro de costo |
| PATCH | `/v1/contabilidad/centros-costo/{id}/toggle` | Activar/desactivar centro de costo |
| GET | `/v1/contabilidad/periodos` | Listar períodos contables |
| POST | `/v1/contabilidad/periodos` | Crear período (anio + mes) |
| PATCH | `/v1/contabilidad/periodos/{id}/toggle` | Abrir/cerrar período |
| GET | `/v1/contabilidad/terceros` | Listar terceros |
| GET | `/v1/contabilidad/parametros-tributarios` | Listar parámetros tributarios (activos + inactivos) |
| PUT | `/v1/contabilidad/parametros-tributarios/{id}` | Editar parámetro tributario |
| PATCH | `/v1/contabilidad/parametros-tributarios/{id}/toggle` | Activar/desactivar parámetro tributario |
| GET | `/v1/contabilidad/parametros-nomina` | Listar parámetros de nómina (activos + inactivos) |
| PUT | `/v1/contabilidad/parametros-nomina/{id}` | Editar parámetro de nómina |
| PATCH | `/v1/contabilidad/parametros-nomina/{id}/toggle` | Activar/desactivar parámetro de nómina |

### Cartera

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/v1/contabilidad/cartera/stats` | Resumen CxC y CxP pendiente/vencida |
| GET | `/v1/contabilidad/cartera/cxc` | Listar CxC (filtro por estado) |
| POST | `/v1/contabilidad/cartera/cxc` | Crear CxC |
| PUT | `/v1/contabilidad/cartera/cxc/{id}` | Editar CxC |
| POST | `/v1/contabilidad/cartera/cxc/{id}/abonar` | Registrar abono a CxC |
| PATCH | `/v1/contabilidad/cartera/cxc/{id}/anular` | Anular CxC |
| GET | `/v1/contabilidad/cartera/cxp` | Listar CxP |
| POST | `/v1/contabilidad/cartera/cxp` | Crear CxP |
| PUT | `/v1/contabilidad/cartera/cxp/{id}` | Editar CxP |
| POST | `/v1/contabilidad/cartera/cxp/{id}/abonar` | Registrar abono a CxP |
| PATCH | `/v1/contabilidad/cartera/cxp/{id}/anular` | Anular CxP |

### Ventas

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/v1/ventas/dashboard` | Stats de ventas del mes |
| GET | `/v1/ventas/productos` | Listar productos (filtros: marca, activo) |
| GET | `/v1/ventas/productos/{id}` | Obtener producto |
| POST | `/v1/ventas/productos` | Crear producto |
| PUT | `/v1/ventas/productos/{id}` | Editar producto |
| DELETE | `/v1/ventas/productos/{id}` | Desactivar producto (soft delete) |
| GET | `/v1/ventas/clientes` | Listar clientes |
| GET | `/v1/ventas/clientes/{id}` | Obtener cliente |
| POST | `/v1/ventas/clientes` | Crear cliente |
| PUT | `/v1/ventas/clientes/{id}` | Editar cliente |
| DELETE | `/v1/ventas/clientes/{id}` | Desactivar cliente (soft delete) |
| GET | `/v1/ventas/` | Listar documentos de venta |
| GET | `/v1/ventas/{id}` | Obtener venta con detalles |
| POST | `/v1/ventas/` | Crear venta (calcula retenciones automáticamente) |
| POST | `/v1/ventas/{id}/confirmar` | Confirmar venta (Borrador → Confirmada) |
| POST | `/v1/ventas/{id}/anular` | Anular venta |

### Alegra (Facturación Electrónica)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/v1/alegra/status` | Verificar conexión con Alegra |
| GET | `/v1/alegra/taxes` | Listar impuestos configurados en Alegra |
| POST | `/v1/alegra/sync/cliente/{id}` | Sincronizar cliente al directorio de Alegra |
| POST | `/v1/alegra/sync/producto/{id}` | Sincronizar producto al catálogo de Alegra |
| POST | `/v1/alegra/facturas/{venta_id}` | Enviar venta como factura electrónica a Alegra |
| GET | `/v1/alegra/facturas` | Listar facturas en Alegra |

---

## 10. Frontend — Vistas y módulos

### Vistas implementadas

| Vista | Ruta lógica | Estado | Descripción |
|---|---|---|---|
| Login | — | Completa | Formulario JWT con manejo de errores |
| Dashboard | `dashboard` | Completa | Stats contables y de ventas |
| PUC | `puc` | Completa (CRUD) | PUC con búsqueda, crear cuenta, editar, activar/desactivar |
| Centros de Costo | `centros-costo` | Completa (CRUD) | Marcas y áreas — crear, editar, activar/desactivar |
| Períodos Contables | `periodos` | Completa (CRUD) | Agrupados por año, abrir/cerrar período, crear año completo |
| Parámetros Tributarios | `tributarios` | Completa (CRUD) | IVA, retenciones, ICA — editar tarifa/cuenta PUC, activar/desactivar |
| Parámetros Nómina | `nomina` | Completa (CRUD) | Aportes y parafiscales — editar valor/tipo, activar/desactivar |
| Ventas | `ventas` | Completa (CRUD) | 4 pestañas: Dashboard, Productos, Clientes, Facturas |
| Cartera | `cartera` | Completa (CRUD) | CxC y CxP con abonos y anulaciones |
| Usuarios | `usuarios` | Completa (CRUD) | Solo visible para Admin |
| Inventario | `inventario` | Fase 2 — 🚧 | Sin implementar |
| RRHH | `rrhh` | Fase 2 — 🚧 | Sin implementar |
| Plataformas | `plataformas` | Fase 2 — 🚧 | Sin implementar |
| Reportes | `reportes` | Fase 2 — 🚧 | Sin implementar |

### Servicios API del frontend

**Utilidades:**

| Archivo | Propósito |
|---|---|
| `utils/printFactura.ts` | Genera HTML autocontenido de la factura y abre la ventana de impresión/PDF del navegador |

**Servicios API:**

| Archivo | Propósito |
|---|---|
| `api.ts` | Instancia Axios base con JWT interceptor y `VITE_API_URL` |
| `ventasApi.ts` | Productos, clientes, documentos de venta |
| `carteraApi.ts` | CxC, CxP, abonos, stats de cartera |
| `dashboardApi.ts` | Stats del dashboard principal |
| `usuariosApi.ts` | CRUD usuarios, cambio de contraseña |
| `contabilidadApi.ts` | PUC, Centros de Costo, Períodos, Parámetros Tributarios y Nómina |

---

## 11. Módulo Alegra (facturación electrónica)

Integración con [Alegra](https://alegra.com) para emitir facturas electrónicas colombianas (CUFE).

### Flujo de uso

1. Configurar credenciales en `backend/.env`:
   ```env
   ALEGRA_EMAIL=tu@email.com
   ALEGRA_TOKEN=tu-token-de-alegra
   ```

2. Sincronizar cliente: `POST /api/v1/alegra/sync/cliente/{id}`
3. Sincronizar productos: `POST /api/v1/alegra/sync/producto/{id}`
4. Confirmar la venta en el ERP: `POST /api/v1/ventas/{id}/confirmar`
5. Enviar factura: `POST /api/v1/alegra/facturas/{venta_id}`

La venta queda con `estado = Facturada`, `alegra_id` y `cufe` guardados.

---

## 12. Datos semilla (Seeds)

El seeder (`seeds/seed.py`) se ejecuta automáticamente al iniciar el backend. Es idempotente (no duplica datos si ya existen).

### Datos cargados

| Categoría | Cantidad |
|---|---|
| Cuentas PUC | 33 cuentas base (Decreto 2650) |
| Centros de costo | 12 (10 marcas + Administración + Logística) |
| Períodos contables | 12 (enero a diciembre 2026) |
| Parámetros tributarios | 8 (IVA 19%, IVA 5%, retefuente, reteIVA, reteICA, ICA) |
| Parámetros nómina | 15 conceptos de prestación de servicios |
| Productos | 15 productos de las 10 marcas |
| Clientes | 6 distribuidores B2B de ejemplo |
| Usuario inicial | `admin@superozonoglobal.com` / `Admin2026!` (rol: Admin) |

---

## 13. Pendientes y roadmap

### Fase 1 — Para ser funcional (en progreso)

| # | Tarea | Estado |
|---|---|---|
| 1 | Roles alineados con estructura real (Admin/Administradora/Auxiliar) | ✅ Completado 2026-06-16 |
| 2 | Proteger endpoints de backend por rol | ✅ Completado 2026-06-16 |
| 3 | Frontend y backend funcionales en red LAN | ✅ Completado 2026-06-16 |
| 4 | Docker con servicio frontend (nginx) para producción | ✅ Completado 2026-06-16 |
| 5 | Archivo `.env` para producción con PostgreSQL | ✅ Completado 2026-06-16 |
| 6 | CRUD de PUC, períodos, tributarios y centros de costo desde la UI | ✅ Completado 2026-06-16 |
| 7 | Exportación/impresión de facturas en PDF | ✅ Completado 2026-06-16 |
| 8 | Módulo de compras/proveedores independiente | ⏳ Pendiente |
| 9 | Inventario con movimientos reales (entradas/salidas) | ⏳ Pendiente |

### Fase 2 — Módulos futuros

- RRHH / Talento Humano
- Plataformas & Marketing
- Reportes & BI
- Nómina electrónica
