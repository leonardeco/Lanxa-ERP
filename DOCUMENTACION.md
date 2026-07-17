# Super Ozono Global — ERP: Documentación Técnica

**Empresa:** TECNOLOGIA E INNOVACION SUPER OZONO S.A.S.
**NIT:** 901841798-5
**Ciudad:** Armenia, Quindío
**Versión ERP (LAN):** 0.3.0 · **Docs:** 0.7.1
**Última actualización:** 2026-07-15

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

ERP interno para la gestión contable y comercial de Super Ozono Global. Diseñado para red local (LAN): un PC servidor corre backend + frontend; el resto abre el navegador.

| Perfil de negocio | Rol en el ERP | Acceso típico |
|---|---|---|
| Dueño técnico del sistema | **Superusuario** | Todo + Usuarios & Accesos |
| Dirección operativa | **Directora** | Contabilidad, ventas, compras, cartera, inventario, reportes |
| Jefe de empresa | **CEO** | Dashboard, reportes y consulta de operación |
| Contador | **Contador** | Área contable, cartera, reportes, ventas/compras |
| Auxiliares (×3) | **Auxiliar Contable** | Contabilidad operativa + ventas/compras/cartera |

**URL LAN actual (PC servidor):** `https://192.168.1.48:5173` · API `https://192.168.1.48:8000`  
**Arranque:** acceso escritorio *Super Ozono ERP* (`start.bat`) / `stop.bat`.  
Detalle ops: `ops/ESTADO-OPERATIVO-PC.md`.

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
| Autenticación | JWT access token (PyJWT) + refresh token opaco (cookie HttpOnly) | 2.13.0 |
| Hashing contraseñas | passlib + bcrypt | 1.7.4 |
| Rate limiting | slowapi | 0.1.9 |
| HTTPS (LAN, sin Docker) | uvicorn `--ssl-keyfile/--ssl-certfile` + CA local autofirmada (`cryptography`) | — |
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
│   │   │   ├── numbering.py         # Numeración robusta unificada (MAX del sufijo, parseo tolerante)
│   │   │   ├── limiter.py           # Instancia slowapi (rate limiting login)
│   │   │   └── security.py          # JWT, hash contraseñas, refresh tokens
│   │   ├── modules/
│   │   │   ├── contabilidad/
│   │   │   │   ├── models.py        # PUC, CentroCosto, Periodos, Terceros, CxC, CxP, etc.
│   │   │   │   ├── schemas.py       # Pydantic schemas
│   │   │   │   └── router.py        # Endpoints contabilidad y cartera
│   │   │   ├── ventas/
│   │   │   │   ├── models.py        # Producto, Cliente, VentaDocumento, VentaDetalle
│   │   │   │   ├── schemas.py       # Pydantic schemas
│   │   │   │   └── router.py        # Endpoints ventas
│   │   │   ├── compras/
│   │   │   │   ├── models.py        # Proveedor, CompraDocumento, CompraDetalle (con producto_id opcional)
│   │   │   │   ├── schemas.py       # Pydantic schemas
│   │   │   │   └── router.py        # CRUD compras/proveedores, confirmar (→ genera CxP + entrada inventario), anular
│   │   │   ├── inventario/
│   │   │   │   ├── models.py        # MovimientoInventario, TipoMovimientoInventario, OrigenMovimiento
│   │   │   │   ├── schemas.py       # MovimientoResponse, AjusteInventarioInput, InventarioDashboard
│   │   │   │   ├── service.py       # registrar_movimiento() — actualiza stock + crea el movimiento (kardex)
│   │   │   │   └── router.py        # dashboard, movimientos (kardex), ajuste manual
│   │   │   ├── reportes/
│   │   │   │   ├── schemas.py       # AgingCarteraResponse, ComprasPeriodoResponse, VentasPeriodoResponse, RetencionesPeriodoResponse
│   │   │   │   └── router.py        # solo lectura, sin modelos propios — agrega sobre contabilidad/compras/ventas
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
│   ├── scripts/
│   │   ├── backup_db.py             # Backup diario cifrado de la BD SQLite (tarea programada Windows)
│   │   ├── restore_db.py            # Descifra y restaura un backup (con copia .bak previa)
│   │   ├── generate_tls_cert.py     # Genera la CA local + certificado de servidor para HTTPS
│   │   ├── migrate_rol_constraint.py      # Agrega el CHECK constraint de rol a una BD ya existente
│   │   └── migrate_cliente_retenciones.py # Agrega las columnas de perfil tributario a `clientes` (BD existente)
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
│   │   │   ├── StatusBar.tsx
│   │   │   ├── Modal.tsx            # Modal accesible compartido (focus-trap, Escape, aria-modal)
│   │   │   ├── Toast.tsx            # Notificación accesible compartida (role=status, aria-live)
│   │   │   └── Skeleton.tsx         # Placeholder shimmer para estados de carga
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx      # Estado global de autenticación
│   │   ├── services/
│   │   │   ├── api.ts               # Instancia Axios con token JWT y URL dinámica
│   │   │   ├── ventasApi.ts
│   │   │   ├── comprasApi.ts        # Proveedores, compras (con producto_id), dashboard compras
│   │   │   ├── inventarioApi.ts     # Dashboard, movimientos (kardex), ajustes manuales
│   │   │   ├── reportesApi.ts       # Aging, compras/ventas por periodo, retenciones
│   │   │   ├── dashboardApi.ts
│   │   │   ├── usuariosApi.ts
│   │   │   ├── carteraApi.ts        # CxC, CxP (incluye compra_id), Pago (comprobantes)
│   │   │   └── contabilidadApi.ts   # PUC, centros, periodos, tributarios, nómina
│   │   ├── utils/
│   │   │   ├── printFactura.ts      # Impresión PDF documentos de venta
│   │   │   ├── printCompra.ts       # Impresión PDF documentos de compra
│   │   │   └── printComprobante.ts  # Impresión Recibo de Caja (CxC) / Comprobante de Egreso (CxP)
│   │   ├── views/
│   │   │   ├── LoginView.tsx
│   │   │   ├── DashboardView.tsx
│   │   │   ├── PucView.tsx
│   │   │   ├── CentrosCostoView.tsx
│   │   │   ├── PeriodosView.tsx
│   │   │   ├── TributariosView.tsx
│   │   │   ├── NominaView.tsx
│   │   │   ├── VentasView.tsx       # 4 pestañas: Dashboard, Productos, Clientes, Facturas
│   │   │   ├── ComprasView.tsx      # 4 pestañas: Dashboard, Proveedores, Compras, Nueva Compra
│   │   │   ├── InventarioView.tsx   # Dashboard, Productos (stock), Movimientos (kardex), Ajuste manual
│   │   │   ├── ReportesView.tsx     # Aging cartera, Compras/Ventas por periodo, Retenciones
│   │   │   ├── CarteraView.tsx      # CxC y CxP con abonos, comprobante automático e historial de pagos
│   │   │   └── UsuariosView.tsx     # Gestión de usuarios (solo Admin)
│   │   ├── App.tsx                  # Enrutador por vistas + control de roles
│   │   └── main.tsx
│   ├── .env                         # VITE_API_URL para desarrollo local
│   └── .env.servidor                # Plantilla con IP del servidor para producción
├── docker-compose.yml               # Backend + Frontend nginx + PostgreSQL + Redis + pgAdmin
├── .env.produccion                  # Template de variables para Docker (copiar a .env)
├── certs/                           # CA local + certificado de servidor (gitignored, generado por PC)
├── start.bat                        # Inicia backend y frontend en Windows (dev/LAN sin Docker), HTTPS
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
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
DEBUG=true

# CORS — orígenes permitidos separados por coma
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Empresa
EMPRESA_NIT=901841798-5
EMPRESA_RAZON_SOCIAL=TECNOLOGIA E INNOVACION SUPER OZONO S.A.S.
EMPRESA_CIUDAD=Armenia, Quindio

# Usuario admin del seed (se crea al iniciar si no existe)
SEED_ADMIN_EMAIL=admin@superozonoglobal.com
SEED_ADMIN_PASSWORD=Admin2026!          # cambiar en producción (hay warning si sigue el de fábrica)

# Retenciones — parámetros tributarios
UVT_VALOR=52374                          # UVT 2026 (DIAN Res. 000238/2025); override por año si cambia
RETEFUENTE_BASE_UVT=27                   # tope en UVT para retefuente de compras generales
# Resolución DIAN (#22) — rellenar cuando la DIAN autorice numeración
DIAN_RESOLUCION_NUMERO=
DIAN_RESOLUCION_FECHA=
DIAN_PREFIJO=
DIAN_RANGO_DESDE=
DIAN_RANGO_HASTA=
DIAN_VIGENCIA_HASTA=
# Habeas Data (#23) — texto en pie de factura / política resumida
HABEAS_DATA_TEXTO=...

# Alegra (opcional — facturación electrónica)
ALEGRA_EMAIL=
ALEGRA_TOKEN=

# Backups (solo SQLite — scripts/backup_db.py)
BACKUP_DIR=C:/SuperOzono-Backups
BACKUP_ENCRYPTION_KEY=<clave-fernet-generada>
BACKUP_RETENTION_DAYS=30
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

Esto abre dos ventanas de cmd (HTTPS, con certificado local — ver sección 6):
- `Backend — FastAPI :8000` → `https://localhost:8000/docs`
- `Frontend — Vite :5173` → `https://localhost:5173`

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
   CORS_ORIGINS=https://192.168.1.10:5173,https://localhost:5173
   ```

3. Editar `frontend/.env`:
   ```env
   VITE_API_URL=https://192.168.1.10:8000/api
   ```

4. Ejecutar `start.bat` en el servidor. La primera vez genera automáticamente un certificado HTTPS local (`certs/`, ver sección siguiente) — las veces siguientes lo reutiliza.

5. (Opcional) Ejecutar `crear-acceso-escritorio.bat` para crear un ícono "Super Ozono ERP" en el escritorio con el logo de la empresa, que ejecuta `start.bat`. El script usa `$PSScriptRoot` (la carpeta donde vive el propio script), así que funciona igual sin importar en qué PC o ruta esté copiado el proyecto — solo hay que ejecutarlo una vez en cada PC servidor nuevo, no se puede copiar el acceso directo ya creado de un PC a otro porque apunta a una ruta absoluta.

### HTTPS — instalar el certificado como confiable (una vez por PC)

El sistema usa HTTPS con una **CA local autofirmada** (no hay dominio público, así que Let's Encrypt no aplica). El navegador no va a confiar en ella automáticamente — hay que instalar `certs\superozono-ca.crt` como certificado raíz de confianza, **una vez en cada PC** (servidor y los 4 clientes). El archivo de certificado de servidor se puede regenerar más adelante (otra IP, etc.) sin tener que repetir este paso, mientras la CA no cambie.

**En el PC servidor**, después de correr `start.bat` por primera vez (ya generó `certs\superozono-ca.crt`):
```powershell
# Sin permisos de administrador (alcanza para el navegador del usuario actual):
certutil -user -addstore -f "ROOT" "C:\ruta\al\proyecto\certs\superozono-ca.crt"

# Con permisos de administrador (confía para todos los usuarios del PC):
certutil -addstore -f "ROOT" "C:\ruta\al\proyecto\certs\superozono-ca.crt"
```

**En los otros 4 PCs (solo navegador, sin clonar el repo):**

1. Copiar el archivo `certs\superozono-ca.crt` del servidor a cada PC cliente (USB, carpeta compartida, correo, etc.) — es solo el certificado público, no la clave privada.
2. Doble clic sobre el archivo → **Instalar certificado** → **Equipo local** (pide admin) o **Usuario actual** → **Colocar todos los certificados en el siguiente almacén** → **Entidades de certificación raíz de confianza**.
3. Reiniciar el navegador.
4. Navegar a `https://192.168.1.10:5173` (la IP del servidor).

> Si el navegador sigue mostrando "conexión no segura" después de instalar el certificado, revisar que la IP del servidor esté en el campo SAN del certificado (`certs\server.crt`) — si la IP del servidor cambió, hay que volver a correr `backend\venv\Scripts\python.exe backend\scripts\generate_tls_cert.py` (no hace falta reinstalar la CA en los clientes, solo el certificado de servidor cambia).

> **Nota:** `start.bat` ya está configurado con `--host 0.0.0.0` tanto para uvicorn como para Vite, por lo que el servidor es visible en toda la red local.

---

## 7. Sistema de roles y permisos

Actualizado **2026-07-15**. Roles válidos en BD (`ROLES_VALIDOS`, CHECK `ck_usuarios_rol`, migración `b1c2d3e4f5a6`):

| Rol | Descripción |
|---|---|
| `Superusuario` | Acceso total. Único que gestiona usuarios, Alegra y onboard multi-tenant. (Antes: `Admin`) |
| `Directora` | Operación: contabilidad, ventas, compras, cartera, inventario, reportes. Puede anular y editar maestros. Sin Usuarios. (Antes: `Administradora`) |
| `CEO` | Visión ejecutiva: dashboard, reportes e inventario/ventas/compras/cartera en consulta (UI). Sin anular ni usuarios |
| `Contador` | Área contable + cartera (abonos) + reportes + ventas/compras. No anula documentos ni gestiona usuarios |
| `Auxiliar Contable` | Contabilidad operativa + ventas/compras/cartera + reportes. No anula ni gestiona usuarios |

Script de estructura en LAN: `backend/scripts/aplicar_estructura_usuarios.py` (7 cuentas típicas).  
Entrega (cuando se decida): Escritorio `Entrega-SuperOzono-v030\` — **entrega de contraseñas aplazada a propósito (2026-07-15).**

### Acceso por módulo (UI — `ROLE_VIEWS` en `App.tsx`)

| Módulo | Superusuario | Directora | CEO | Contador | Auxiliar Contable |
|---|---|---|---|---|---|
| Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ventas | ✅ | ✅ | 👁️ | ✅ | ✅ |
| Compras | ✅ | ✅ | 👁️ | ✅ | ✅ |
| Cartera | ✅ | ✅ | 👁️ | ✅ | ✅ |
| Inventario | ✅ | ✅ | 👁️ | ❌ | ❌ |
| PUC / centros / períodos / tributarios | ✅ | ✅ | ❌ | ✅ | ✅ |
| Nómina (params) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Reportes | ✅ | ✅ | ✅ | ✅ | ✅ |
| Usuarios | ✅ | ❌ | ❌ | ❌ | ❌ |

### Implementación técnica

**Backend (`api/deps.py` + `usuarios/models.py`):**

| Dependencia | Alias | Roles |
|---|---|---|
| `get_current_user` | `CurrentUser` | Cualquier autenticado |
| `get_admin_or_administradora` | `AdminOrAdministradoraDep` | Superusuario, Directora (`ROLES_OPERACION`) |
| `get_area_contable` | `ContableDep` | Superusuario, Directora, Contador, Auxiliar Contable |
| `get_current_active_superuser` | `AdminDep` | Solo Superusuario |

**Reglas por módulo (resumen):**

- **Contabilidad / abonos cartera:** `ContableDep`
- **Anular ventas/compras, maestros productos/clientes/proveedores, ajustes e import inventario:** `AdminOrAdministradoraDep` (Superusuario + Directora)
- **Crear/confirmar venta o compra:** `CurrentUser` (si el rol ve el módulo en UI)
- **Usuarios / Alegra / onboard tenant:** `AdminDep` (Superusuario)

**Frontend (`App.tsx`):**
- `ROLE_VIEWS` por rol; navegación no permitida → dashboard
- Sidebar filtra por `allowedViews`
- Login: mensajes claros si API caída o rate limit (2026-07-15)

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
| `cuentas_por_pagar` | CxP: documentos pendientes de pago. Incluye `compra_id` (FK lógica opcional a `compras_documentos`) para CxP generadas automáticamente al confirmar una compra |
| `pagos` | Comprobante de cada abono a CxC/CxP — numeración separada `RC-XXXX` (Recibo de Caja) / `CE-XXXX` (Comprobante de Egreso), con `saldo_anterior`/`saldo_nuevo` y `usuario_id` |
| `parametros_tributarios` | IVA, retefuente, reteIVA, reteICA, ICA |
| `parametros_nomina` | Salud, pensión, ARL, parafiscales |

### Módulo Ventas (`ventas/models.py`)

| Tabla | Descripción |
|---|---|
| `productos` | Catálogo con SKU, marca, precio, IVA, stock, registro ICA. `stock_actual` es `Numeric(12,3)` (soporta cantidades fraccionarias). `controla_lote` (bool, opt-in): activa la trazabilidad por lote + vencimiento con salidas FEFO para ese producto |
| `clientes` | Clientes B2B con NIT, régimen, contacto, cupo de crédito. **Perfil tributario:** `retiene_fuente`/`retiene_iva`/`retiene_ica` (flags de agente retenedor) y `tarifa_reteica` (por mil) para el cálculo de retenciones en ventas |
| `ventas_documentos` | Cabecera de factura interna (SOG-V-XXXX) con totales y retenciones (calculadas según el perfil tributario del cliente, con override manual por factura) |
| `ventas_detalles` | Líneas de producto con cálculo de descuento e IVA |

### Módulo Compras (`compras/models.py`)

| Tabla | Descripción |
|---|---|
| `proveedores` | Proveedores con NIT, régimen, contacto |
| `compras_documentos` | Cabecera de documento de compra (SOG-CP-XXXX) con estado, estado_pago, totales y retenciones |
| `compras_detalles` | Líneas de producto/concepto de la compra con cálculo de IVA. Incluye `producto_id` opcional (FK a `productos`) para vincular la línea al catálogo y generar entrada de inventario al confirmar. `codigo_lote`/`fecha_vencimiento` (opcionales): capturados en el borrador; al confirmar materializan el `Lote` de los productos con `controla_lote` |

### Módulo Inventario (`inventario/models.py`)

| Tabla | Descripción |
|---|---|
| `movimientos_inventario` | Kardex: un registro por cada movimiento de stock (`tipo`: Entrada/Salida/Ajuste positivo/Ajuste negativo; `origen`: Compra/Venta/Ajuste manual/Reverso/Devolución). Guarda `stock_antes`/`stock_despues` (snapshot `Numeric(12,3)`, sin redondeo), FK lógicas a `compra_id`/`venta_id`, `usuario_id`, y `lote_id` (FK a `lotes`) para la trazabilidad del lote afectado |
| `lotes` | Un lote de un producto con `controla_lote` (opt-in): `codigo_lote` (único por producto), `fecha_vencimiento` (nullable), `cantidad_actual`/`cantidad_inicial`, `costo_unitario`, `origen`, `activo`. **Invariante:** `producto.stock_actual == Σ cantidad_actual de sus lotes`. Las entradas crean/incrementan lotes; las salidas consumen por **FEFO** (primero en vencer, primero en salir; los vencidos no se despachan). El servicio (`inventario/lotes.py`) engancha los 7 puntos de stock: compra confirmar/anular/devolución, venta confirmar/anular/nota crédito, ajuste, e importador |

### Módulo Usuarios (`usuarios/models.py`)

| Tabla | Descripción |
|---|---|
| `usuarios` | Email, nombre, contraseña hasheada, rol (con `CHECK constraint`, `ROLES_VALIDOS`), estado activo |
| `refresh_tokens` | Hash del refresh token (nunca el valor crudo), usuario, expiración. Uno por sesión, se rota en cada uso |

---

## 9. Backend — Endpoints API

Base URL: `http://[host]:8000/api`

### Autenticación

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/login/access-token` | Público | Login. Retorna JWT Bearer token (1h) + cookie `HTTPOnly` con refresh token (30 días). Rate limited: 5 intentos/min por IP (`slowapi`, en memoria) |
| POST | `/login/refresh-token` | Cookie de refresh token | Renueva el access token; rota el refresh token (el usado queda invalido) |
| POST | `/login/logout` | Cookie de refresh token (opcional) | Revoca el refresh token en BD y limpia la cookie |
| GET | `/users/me` | Autenticado | Datos del usuario en sesión |

### Usuarios

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/v1/usuarios` | Admin | Listar todos los usuarios |
| POST | `/v1/usuarios` | Admin | Crear usuario |
| PUT | `/v1/usuarios/{id}` | Admin | Editar nombre y rol |
| PATCH | `/v1/usuarios/{id}/toggle` | Admin | Activar/desactivar usuario |
| PUT | `/v1/usuarios/me/password` | Autenticado | Cambiar contraseña propia (requiere la actual) |
| PUT | `/v1/usuarios/{id}/reset-password` | Admin | Resetear la contraseña de otro usuario sin acceso (sin requerir la actual) |

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
| POST | `/v1/contabilidad/cartera/cxc/{id}/abonar` | Registrar abono a CxC — genera comprobante `RC-XXXX` (Recibo de Caja). Devuelve `{ documento, pago }` |
| PATCH | `/v1/contabilidad/cartera/cxc/{id}/anular` | Anular CxC |
| GET | `/v1/contabilidad/cartera/cxp` | Listar CxP |
| POST | `/v1/contabilidad/cartera/cxp` | Crear CxP |
| PUT | `/v1/contabilidad/cartera/cxp/{id}` | Editar CxP |
| POST | `/v1/contabilidad/cartera/cxp/{id}/abonar` | Registrar abono a CxP — genera comprobante `CE-XXXX` (Comprobante de Egreso); si tiene `compra_id`, sincroniza `estado_pago` de la compra (Pagado/Parcial). Devuelve `{ documento, pago }` |
| PATCH | `/v1/contabilidad/cartera/cxp/{id}/anular` | Anular CxP — si tiene `compra_id`, marca la compra como `estado_pago = Anulado` |
| GET | `/v1/contabilidad/cartera/pagos` | Historial de comprobantes de pago (filtro `cxc_id` / `cxp_id`) — para reimpresión |

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
| POST | `/v1/ventas/` | Crear venta — sugiere retenciones (ReteFuente/ReteIVA/ReteICA) según el perfil tributario del cliente y las tarifas de `ParametroTributario`, con tope en UVT; admite override manual por factura. Valida stock, cantidades y % |
| POST | `/v1/ventas/{id}/confirmar` | Confirmar venta (Borrador → Confirmada) — valida stock disponible (bloquea sobreventa con `400`), genera `MovimientoInventario` tipo Salida por cada línea y una `CuentaPorCobrar` automática vinculada por `numero_factura` (idempotente) |
| POST | `/v1/ventas/{id}/anular` | Anular venta — si estaba Confirmada/Facturada, revierte las salidas de inventario con un movimiento Entrada (Reverso de venta) |

### Compras & Proveedores

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/v1/compras/dashboard` | KPIs: total mes, variación %, CxP pendiente, top proveedores |
| GET | `/v1/compras/proveedores` | Listar proveedores |
| POST | `/v1/compras/proveedores` | Crear proveedor |
| PUT | `/v1/compras/proveedores/{id}` | Editar proveedor |
| DELETE | `/v1/compras/proveedores/{id}` | Desactivar proveedor (soft delete) |
| GET | `/v1/compras/` | Listar documentos de compra |
| GET | `/v1/compras/{id}` | Obtener compra con detalles |
| POST | `/v1/compras/` | Crear compra (Borrador, calcula retenciones) |
| POST | `/v1/compras/{id}/confirmar` | Confirmar compra (Borrador → Confirmada) — genera `CuentaPorPagar` automática vinculada (`compra_id`) + `MovimientoInventario` tipo Entrada por cada línea con `producto_id`. Los productos con `controla_lote` materializan/incrementan su `Lote` (la línea debe traer `codigo_lote`, si no → 400) |
| POST | `/v1/compras/{id}/anular` | Anular compra — si estaba Confirmada, revierte las entradas de inventario con un movimiento Salida (Reverso de compra); en productos con lote descuenta del lote creado (o por FEFO si ya se vendió) |

### Inventario

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/v1/inventario/dashboard` | Valor total de inventario, productos con stock bajo, movimientos del mes, top 5 productos por valor |
| GET | `/v1/inventario/lotes` | Existencias por lote con estado de vencimiento derivado (vigente/por_vencer/vencido/sin_vencimiento); filtros `producto_id`/`estado`/`dias`/`incluir_agotados`, orden FEFO |
| GET | `/v1/inventario/movimientos` | Kardex completo, filtros opcionales `producto_id`/`tipo`/`origen`/`fecha_desde`/`fecha_hasta` |
| GET | `/v1/inventario/movimientos/{producto_id}` | Kardex de un producto específico |
| POST | `/v1/inventario/ajustes` | Ajuste manual de stock (Entrada/Salida) — Admin/Administradora. En productos con `controla_lote`: la Entrada crea/incrementa un lote (requiere `codigo_lote`) y la Salida consume por FEFO |
| GET | `/v1/inventario/plantilla` | Descarga la plantilla `.xlsx` de inventario inicial (incluye columnas opcionales `codigo_lote`/`fecha_vencimiento`) |
| POST | `/v1/inventario/importar` | Importa el inventario inicial desde `.xlsx` (validación fila por fila, atómico). Si la fila trae `codigo_lote`, el producto queda con control de lote y su stock inicial entra como ese lote |

### Reportes

Solo lectura, sin tablas propias — agregan sobre `contabilidad` (CxC/CxP), `compras` y `ventas`.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/v1/reportes/aging-cartera` | CxC y CxP agrupadas por antigüedad de vencimiento: Corriente, 1-30, 31-60, 61-90, +90 días. Excluye documentos Pagado/Anulado |
| GET | `/v1/reportes/compras-periodo` | Total y cantidad de compras en un rango (`fecha_desde`/`fecha_hasta`, default mes actual), agrupado por proveedor |
| GET | `/v1/reportes/ventas-periodo` | Total y cantidad de ventas en un rango, agrupado por cliente y por marca |
| GET | `/v1/reportes/retenciones-periodo` | ReteFuente/ReteIVA/ReteICA acumulados de compras y ventas en un rango, con totales combinados |
| GET | `/v1/reportes/estado-resultados` | P&L del período: ingresos/costos/gastos por cuenta PUC, utilidad bruta y neta (desde el libro diario) |
| GET | `/v1/reportes/balance-general` | Activo/Pasivo/Patrimonio a fecha de corte, con saldos iniciales, resultado del ejercicio y flag `cuadrado` |

### Asientos contables (partida doble — motor en `contabilidad/asientos.py`)

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/v1/contabilidad/asientos` | Libro diario con movimientos y totales; filtros `modulo_origen` y `documento_ref` |
| GET | `/v1/contabilidad/asientos/{id}` | Detalle de un asiento |

Los asientos se generan automáticamente al confirmar ventas/compras y abonar CxC/CxP, con reverso espejo al anular. Terceros vinculados por NIT en cada movimiento. Mapeo PUC: ver `MAPEO-PUC-PARA-CONTADOR.md`.

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
| Compras | `compras` | Completa (CRUD) | 4 pestañas: Dashboard, Proveedores, Compras, Nueva Compra — confirmar/anular, impresión PDF, selector opcional de producto por línea; captura de lote+vencimiento por renglón cuando el producto controla lote |
| Inventario | `inventario` | Completa | Pestañas: Dashboard (con KPIs de lotes por vencer/vencidos), Productos (stock, solo lectura), **Lotes** (existencias por lote con estado de vencimiento y filtros), Movimientos (kardex filtrable), Ajuste manual con captura/FEFO de lote e Importar (Admin/Administradora) |
| Cartera | `cartera` | Completa (CRUD) | CxC y CxP con abonos, anulaciones, origen (compra automática / manual), comprobante de pago impreso automáticamente al abonar e historial de pagos reimprimible |
| Usuarios | `usuarios` | Completa (CRUD) | Solo visible para Admin |
| RRHH | `rrhh` | Fase 2 — 🚧 | Sin implementar |
| Plataformas | `plataformas` | Fase 2 — 🚧 | Sin implementar |
| Reportes | `reportes` | Completa | 3 pestañas: Aging de Cartera, Compras y Ventas por Período (selector de fechas), Retenciones Acumuladas |

### Componentes compartidos y accesibilidad

- **`Modal.tsx`** — modal accesible reutilizable (focus-trap, cierre con `Escape`, `role="dialog"` + `aria-modal`, restauración de foco). Adoptado en las 10 vistas y en los modales de formulario (CentrosCosto, Nómina, PUC, Tributarios).
- **`Toast.tsx`** — notificación accesible (`role="status"`, `aria-live`).
- **`Skeleton.tsx`** — placeholder con animación shimmer para estados de carga (Dashboard y las 5 vistas de lista de contabilidad).
- **Accesibilidad global** (`index.css`): `:focus-visible` y `@media (prefers-reduced-motion: reduce)`.
- **Responsive** (`index.css`): breakpoints 1024/768/480 — sidebar colapsable, grids apilados, tablas con scroll horizontal, botones full-width en móvil.

### Servicios API del frontend

**Utilidades:**

| Archivo | Propósito |
|---|---|
| `utils/printFactura.ts` | Genera HTML autocontenido de la factura y abre la ventana de impresión/PDF del navegador |
| `utils/printCompra.ts` | Genera HTML autocontenido del documento de compra y abre la ventana de impresión/PDF |

**Servicios API:**

| Archivo | Propósito |
|---|---|
| `api.ts` | Instancia Axios base con JWT interceptor y `VITE_API_URL` |
| `ventasApi.ts` | Productos, clientes, documentos de venta |
| `comprasApi.ts` | Proveedores, documentos de compra, dashboard de compras |
| `carteraApi.ts` | CxC, CxP (incluye `compra_id`), abonos, stats de cartera |
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
| Usuario inicial | `admin@superozonoglobal.com` (rol: **Superusuario**). Clave: `SEED_ADMIN_PASSWORD` del `.env` del servidor (no usar `Admin2026!` de fábrica en prod) |

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
| 8 | Módulo de compras/proveedores independiente | ✅ Completado 2026-06-16 |
| 9 | Inventario con movimientos reales (entradas/salidas) | ✅ Completado 2026-06-17 |
| 10 | Comprobante de pago numerado al abonar CxC/CxP | ✅ Completado 2026-06-17 |
| 11 | Reportes — aging cartera, compras/ventas por período, retenciones acumuladas | ✅ Completado 2026-06-17 |
| 12 | Rate limiting en login (mitigar fuerza bruta) | ✅ Completado 2026-06-19 |
| 13 | Refresh tokens con rotación + TTL de access token bajado a 1h | ✅ Completado 2026-06-19 |
| 14 | Backups automatizados de la BD (SQLite, cifrados, tarea diaria) | ✅ Completado 2026-06-19 |
| 15 | HTTPS con CA local autofirmada (uvicorn + Vite), pendiente instalar en los 4 PCs cliente | ✅ Completado 2026-06-19 |
| 16 | Reset de contraseña por Admin para usuarios sin acceso | ✅ Completado 2026-06-19 |
| 17 | CHECK constraint en `usuarios.rol` (BD nuevas y migración para la existente) | ✅ Completado 2026-06-19 |
| 18 | Validación de entradas en schemas (abonos/precios/%/cantidades) + guard de sobreventa | ✅ Completado 2026-07-01 |
| 19 | Eliminación de N+1 en listados de ventas (`selectinload`) + numeración robusta unificada | ✅ Completado 2026-07-01 |
| 20 | Stock fraccionario (`Numeric(12,3)` en producto y kardex, sin redondeo) | ✅ Completado 2026-07-01 |
| 21 | Auto-CxC al confirmar venta (espejo de compras→CxP, idempotente) | ✅ Completado 2026-07-01 |
| 22 | Motor de retenciones híbrido (perfil tributario del cliente + tarifas + tope UVT + override manual) | ✅ Completado 2026-07-01 |
| 23 | Componentes compartidos accesibles (Modal/Toast/Skeleton), responsive y `prefers-reduced-motion` | ✅ Completado 2026-07-01 |
| 24 | Overhaul de calidad: SQLAlchemy 2.0 tipado (mypy 161→0), CI GitHub Actions, Alembic, pre-commit, line endings | ✅ Completado 2026-07-02 |
| 25 | Seguridad: 14 CVEs → 0 (fastapi 0.139/starlette 1.3.1), docs ocultos en prod, token 15 min, rate limits, headers, CORS validator | ✅ Completado 2026-07-02 |
| 26 | Cobertura de tests 95% (198 API) + 25 componentes (Vitest) + 5 E2E (Playwright) | ✅ Completado 2026-07-02 |
| 27 | Motor de asientos (partida doble) + P&L/Balance General/Libro Diario con export a Excel | ✅ Completado 2026-07-02 |
| 28 | Alertas de vencimiento en Dashboard, búsqueda en catálogo, terceros materializados | ✅ Completado 2026-07-02 |
| 29 | Ops: DESPLIEGUE.md, MANUAL-DE-USUARIO.md, fix start/stop.bat, restore de backups **verificado con simulacro** | ✅ Completado 2026-07-02 |
| 30 | GitHub: push inicial, CI verde, Dependabot activo (7 PRs fusionados, bcrypt 5 rechazado con causa) | ✅ Completado 2026-07-02 |
| 31 | Cartera robusta: anulación de abonos con reverso, cierre real de períodos, hora local Colombia | ✅ Completado 2026-07-03 |
| 32 | Auxiliar por tercero (estado de cuenta con saldo corrido) + logs rotados en backend/logs/ | ✅ Completado 2026-07-03 |
| 33 | passlib → bcrypt 5 directo (compat verificada), DV del NIT (algoritmo DIAN), stock decimal y flags visibles | ✅ Completado 2026-07-03 |
| 34 | Devoluciones: nota crédito NC- (full-stack) y devolución a proveedor ND- (API) con cuenta 417501 | ✅ Completado 2026-07-03 |
| 35 | Cotizaciones COT- (full-stack): Borrador→Enviada→Aprobada/Rechazada→Convertida, vigencia, conversión a venta, PDF | ✅ Completado 2026-07-05 |
| 36 | Auditoría de cambios: log con diff campo a campo en maestros/parámetros/usuarios + pestaña en Reportes con export | ✅ Completado 2026-07-05 |
| 37 | UX: confirmación antes de descartar formularios con datos sin guardar (modales, Nueva Compra, cambio de módulo, beforeunload) | ✅ Completado 2026-07-05 |
| 38 | Deuda técnica: revocación de sesiones por Admin (14c), E2E Playwright en CI (14d), EmailStr en cliente/proveedor (13a), `_enrich_cxc/cxp` explícitos (13b) | ✅ Completado 2026-07-05 |
| 39 | Manejo de errores consistente en frontend: `ErrorState` compartido con reintento en 21 sitios que fallaban en silencio | ✅ Completado 2026-07-05 |
| 40 | Release v0.3.0: create_all solo en desarrollo (#11), módulos 🚧 fuera del menú, búsqueda en Cartera, top morosos en Dashboard, auditoría extendida a PUC y Centros de Costo | ✅ Completado 2026-07-05 |
| 41 | BUG-007/008: anular venta/compra ahora anula su CxC/CxP y se bloquea si hay abonos o devoluciones (antes quedaba cartera huérfana y doble reverso de stock) | ✅ Completado 2026-07-05 |
| 42 | BUG-009: el ajuste manual de salida ya no puede dejar stock negativo (era el único camino sin validación) | ✅ Completado 2026-07-05 |
| 43 | Seguridad #29: `esc()` compartido escapa HTML en las 4 utilidades de impresión (evita XSS en la ventana de impresión) | ✅ Completado 2026-07-05 |
| 44 | Seguridad #33: validator bloquea la clave por defecto del admin sembrado con `DEBUG=false` (config.py + .env.servidor + DESPLIEGUE.md) | ✅ Completado 2026-07-05 |
| 45 | #32: IP del request en el log de auditoría (middleware ASGI + ContextVar, migración f1a2b3c4d5e6, columna en UI/CSV) | ✅ Completado 2026-07-06 |
| 46 | #31: aviso al convertir cotización de un cliente retenedor (el total de la venta será menor que el cotizado) | ✅ Completado 2026-07-06 |
| 47 | #26: el logout pasa por el guard de datos sin guardar (`handleLogout` consulta `confirmarDescartar()`, igual que el cambio de módulo de #17) + test `App.test.tsx` | ✅ Completado 2026-07-06 |
| 48 | #25: editar y eliminar cotizaciones en Borrador — `PUT`/`DELETE /cotizaciones/{id}` con guard `409` de estado, borrado real + auditoría (`Eliminar/Cotizacion`), helper `_aplicar_detalles_y_totales` compartido con create; front reutiliza el modal en modo edición + botones ✏️/🗑️. Tests: 5 API + 1 componente | ✅ Completado 2026-07-06 |
| 49 | #28: purga/archivado del log de auditoría — `scripts/purge_auditoria.py` (wrapper CLI para Task Scheduler) + `purgar_auditoria()`; exporta cifrado (Fernet) a `{BACKUP_DIR}/auditoria/`, **verifica** el archivo y solo entonces borra los registros con `fecha < corte`. `AUDITORIA_RETENTION_DAYS=1825` (~5 años, `.env`), la purga se auto-audita (`Purgar/Auditoria`). Tests: 4 async | ✅ Completado 2026-07-09 |
| 50 | #2 (parcial): importador de inventario inicial — `inventario/importador.py` (fuente única `EXPECTED_HEADERS`, `generar_plantilla()`, `validar()` fila-por-fila, `importar()` atómico con entrada en el kardex + auditoría). Endpoints `GET /inventario/plantilla` y `POST /inventario/importar` (preview/commit, Admin/Administradora). Frontend: pestaña **Importar** (descargar/validar/confirmar). `openpyxl` + `types-openpyxl`. Tests: 8 (unit + endpoints). Asiento de apertura queda pendiente (#3) | ✅ Completado 2026-07-09 |
| 51 | Trazabilidad por lote + vencimiento (opt-in `controla_lote`, FEFO) — **Capa 1** modelo `Lote` + `kardex.lote_id` + migración `a1b2c3d4e5f6`; **Capa 2** servicio `entrada_lote`/`consumir_fefo` (invariante `stock == Σ lotes`); **Capa 3** enganche de los 7 puntos de stock (compra/venta confirmar-anular-devolución, ajuste, importador) + helper `revertir_por_lotes` + campos `codigo_lote`/`fecha_vencimiento` (compra-detalle/ajuste/importador) + migración `b2c3d4e5f6a7`; **Capa 4** `GET /inventario/lotes` (existencias + estado de vencimiento) + alertas en el dashboard + UI (pestaña Lotes, captura de lote en Nueva Compra/Ajuste, toggle `controla_lote` en producto). 9 tests API + 2 de componente | ✅ Completado 2026-07-10 |
| 52 | #13 Servicios de dominio de ventas — nuevo `ventas/services.py` (`confirmar_venta`/`anular_venta` + `VentaError`); endpoints delgados que validan la transición y delegan; `create_venta` reutiliza `get_venta` (sin builder duplicado); quitados los `hasattr(estado,'value')` (columna `SAEnum`). Refactor sin cambio funcional, 276 tests verdes | ✅ Completado 2026-07-10 |
| 53 | Nuevo rol **Contador** — `ROLES_VALIDOS += Contador`, permiso `ContableDep` (`get_area_contable`), `contabilidad/router` migrado de `AdminOrAdministradoraDep` a `ContableDep`; ventas/compras *anular* siguen restringidos (Contador solo consulta); migración `c4d5e6f7a8b9` del CHECK; frontend `ROLES`/`ROLE_VIEWS`/`ROL_COLORS`. También se reconcilió el drift de Alembic de la BD local (ver PENDIENTES #10) | ✅ Completado 2026-07-10 |
| 54 | Migración **python-jose → PyJWT 2.13.0** (HS256) — elimina la dep transitiva `ecdsa` y con ella la CVE PYSEC-2026-1325 (antes ignorada en CI con justificación). `security.py`/`deps.py` (`import jwt`, `JWTError`→`PyJWTError`); `pip-audit` corre sin `--ignore-vuln`; test nuevo de token expirado→401. 277 tests verdes, mypy limpio, 0 CVEs. También se cerraron 3 PRs de Dependabot (#13/#14 fusionados, #15 typescript 6→7 bloqueado por peer dep) | ✅ Completado 2026-07-11 |
| 55 | **Tests de los utilitarios de impresión** — 24 tests Vitest para `printFactura`/`printCompra`/`printCotizacion`/`printComprobante`: verifican el HTML generado, el escapado XSS de campos de usuario (`esc`), las filas condicionales de retención/descuento, las ramas CxC (Recibo de Caja) vs CxP (Comprobante de Egreso), el estado Pagado/Parcial y la rama de popup bloqueado. Helper compartido `src/test/printWindow.ts` mockea `window.open`. Frontend: 37→61 tests de componente/util | ✅ Completado 2026-07-11 |
| 56 | **#30 Access token a memoria** — el access token deja de guardarse en `localStorage` y vive solo en memoria (variable de módulo en `frontend/src/services/api.ts` con accesores `getAccessToken`/`setAccessToken`; `AuthContext` arranca sin token y renueva en silencio). Reduce la superficie de XSS: un script inyectado ya no puede leerlo de un almacén persistente; la sesión entre recargas la sostiene el refresh token en cookie HttpOnly. 5 tests Vitest (`api.test.ts`). Frontend: 61→66 tests | ✅ Completado 2026-07-11 |

### Deuda técnica / mejoras pendientes

- ~~Limpieza de refresh tokens expirados; `int(sub)` 500; guard de "último admin"; enumeración en login; paginación~~ → ✅ **todos resueltos el 2026-07-02** (ver BITACORA.md).
- ~~Alembic~~ → ✅ configurado (async) con migración baseline el 2026-07-02; ~~datetime tz-aware~~ → ✅ helper `utcnow()` en `core/time.py`.
- ~~Locks de concurrencia (`with_for_update`) en abonos y stock~~ → ✅ **2026-07-15** (#12 / #12a).
- ~~passlib → bcrypt directo~~ → ✅ **2026-07-03**.
- **Config/negocio (sigue abierto):** flags `retiene_*` en clientes retenedores (Contador) y **validar `MAPEO-PUC-PARA-CONTADOR.md`**. `UVT_VALOR` default = **52374** (DIAN 2026); override por `.env` si aplica.

### Fase 2 — Módulos futuros

- RRHH / Talento Humano
- Plataformas & Marketing
- Nómina electrónica
- ~~P&L y Balance General~~ → ✅ **Completado 2026-07-02**: motor de asientos contables (`contabilidad/asientos.py`, partida doble automática con reverso al anular y terceros vinculados por NIT) + `GET /reportes/estado-resultados` y `/reportes/balance-general` + UI (pestañas P&L, Balance con "✓ Cuadrado" y Libro Diario) + export a Excel. **Mapeo PUC en borrador — validar con la contadora.** Falta el asiento de costo de venta (6135/1435, requiere definir costeo).
- ~~Devoluciones (notas crédito/débito) y cotizaciones~~ → ✅ **Completados** (devoluciones 2026-07-03, cotizaciones 2026-07-05)
- ~~Auditoría de cambios (audit log)~~ → ✅ **Completado 2026-07-05**; Electron — Fase 4
- **Run 1 — Fundación Postgres (2026-07-14, en curso):** primera etapa de la migración a SaaS multi-tenant (ADR 0001). La suite de tests y el CI pasan de SQLite in-memory a **PostgreSQL** (motor de prod/nube, requisito de RLS): `conftest.py` toma `TEST_DATABASE_URL`, el CI levanta un `services: postgres` y valida `alembic upgrade head` + `alembic check` (cierra el drift #10). **SQLite sigue soportado para el despliegue LAN de v0.3.0.** Sin lógica de tenant todavía (Runs 2–5). Verificación por CI. Ver `docs/hydraia/plans/2026-07-14-fundacion-postgres.md`.
- ~~Seeder de datos demo (50 clientes, 200 ventas)~~ → ✅ **Completado 2026-07-14**: CLI independiente `backend/seeds/seed_demo.py` que llena una BD demo dedicada (`superozono_demo.db`, engine propio + guard anti-producción) con ~50 clientes y ~200 ventas mixtas (confirmadas/borrador/anuladas vía los servicios de dominio reales + abono demo para el aging de Cartera). Idempotente con `--clean`, reproducible con `--seed`; 8 tests pytest en `backend/tests/test_seed_demo.py`. Rama `feat/seeder-datos-demo`.
- ~~**#12a Numeración concurrente-safe**~~ → ✅ **Completado 2026-07-15**: `document_sequences` (PK `prefix`, `last_value`) + `next_sequential_numero` con `with_for_update` y reintento por savepoint ante `IntegrityError`; siembra desde MAX de la columna de negocio para no colisionar con documentos legacy. Migración Alembic `d5e6f7a8b9c0`. Tests unitarios en `backend/tests/test_numbering.py`.
- ~~**#12 Locks en stock y abonos**~~ → ✅ **Completado 2026-07-15**: `SELECT … FOR UPDATE` en producto (`registrar_movimiento`), lotes (entrada/FEFO), productos al confirmar venta (orden por id), CxC/CxP al abonar y al anular pagos. Salidas rechazan stock negativo (`StockError`) salvo `permitir_stock_negativo=True`. Tests en `backend/tests/test_locks_stock.py`.
- **Run 2 — Tenancy foundation (2026-07-15):** modelo `Tenant` + mixin `TenantScoped` (`tenant_id`) en tablas de negocio; migración `e6f7a8b9c0d1` (seed empresa #1 `superozono`); JWT con claim `tenant_id`; `get_current_user` fija contextvar; `document_sequences` PK `(tenant_id, prefix)`. Plan: `docs/hydraia/plans/2026-07-15-run2-tenancy-foundation.md`.
- **Run 3 — RLS PostgreSQL (2026-07-15):** migración `f7a8b9c0d1e2` (ENABLE+FORCE RLS + policy `tenant_isolation` solo en PG); `apply_rls_tenant` / `set_config('app.tenant_id')` en `get_db` y post-login; tests de aislamiento en `test_tenancy.py`. SQLite LAN: no-op. Plan: `docs/hydraia/plans/2026-07-15-run3-rls-postgres.md`.
- **Run 4 — Filtros tenant + HTTP (2026-07-15):** helpers `for_tenant` / `get_for_tenant` / stamp `before_insert`; listados/get de productos, clientes, ventas, compras, proveedores, PUC, centros, periodos, CxC/CxP, usuarios, aging; tests `test_tenant_http_isolation.py`. Plan: `docs/hydraia/plans/2026-07-15-run4-tenant-filters.md`.
- **Run 5 — Onboarding + uniques compuestos (2026-07-15):** migración `a0b1c2d3e4f5` UNIQUE(tenant_id, sku/email/nit/numero…); `POST /api/v1/tenants/onboard` (solo Admin tenant #1) crea empresa + Admin; `GET /api/v1/tenants/`; tests `test_tenant_onboard.py`. Plan: `docs/hydraia/plans/2026-07-15-run5-onboarding-uniques.md`.
- **Fase 2 Docker prod (2026-07-15):** backend multi-stage non-root + entrypoint (`alembic upgrade head`); frontend nginx; `docker-compose.prod.yml` + `.env.docker.example`. **Docker Desktop no está instalado en este PC** — falta `compose up` de verificación. Plan: `docs/hydraia/plans/2026-07-15-fase2-docker-prod.md`.
- **Fase 3 AWS Terraform (2026-07-15):** esqueleto `infra/terraform` (VPC 2 AZ, SG ALB/backend/RDS, RDS Postgres 16 privado, Secrets Manager, ECR). Pendiente `terraform apply` con cuenta AWS + tooling. Plan: `docs/hydraia/plans/2026-07-15-fase3-aws-terraform.md`.
- **Fase 4 migración SQLite→PG (2026-07-15):** script `backend/scripts/migrate_sqlite_to_postgres.py` + guía `MIGRATE-SQLITE-POSTGRES.md` (dry-run de 145 filas LAN verificado).
- **Fase 5 ECS borrador (2026-07-15):** `infra/terraform/ecs.tf` (cluster, ALB HTTP, task/service Fargate) detrás de `enable_ecs = false`. Plan: `docs/hydraia/plans/2026-07-15-fase4-migrate-fase5-ecs.md`.
- **HTTPS/ACM + CI ECR (2026-07-15):** `acm.tf` (cert + listener 443 + redirect 80), `iam_github_oidc.tf`, workflow `.github/workflows/ecr-publish.yml`. Flags off por defecto. Plan: `docs/hydraia/plans/2026-07-15-https-acm-ecr-ci.md`.
- **Fase 6 S3+CloudFront (2026-07-15):** `frontend_cdn.tf` (bucket privado, OAC, CF, SPA fallback, `/api`→ALB opcional); workflow `frontend-cdn.yml`. Flag `enable_frontend_cdn=false`. Plan: `docs/hydraia/plans/2026-07-15-fase6-s3-cloudfront.md`.
- ~~**Política de contraseñas**~~ → ✅ **Completado 2026-07-15**: `app/core/passwords.py` (min 8, letra+dígito, denylist fábrica); validadores en schemas de usuarios y onboard tenant; tests `test_password_policy.py`.
- ~~**#14a puente Cliente/Proveedor → Tercero**~~ → ✅ **Completado 2026-07-15** (capa codeable): `sync_tercero_from_cliente` / `sync_tercero_from_proveedor` al crear/editar; Mixto si el NIT es ambos; tests `test_tercero_sync.py`. Unificación de modelo con FK única queda opcional.
- ~~**#21a Staging LAN**~~ → ✅ **Completado 2026-07-15** (docs+script): `ops/STAGING.md`, `ops/setup-staging.ps1` (BD y puertos 8010/5180).
- ~~**Roles Superusuario / Directora / CEO / Auxiliar Contable**~~ → ✅ **Completado 2026-07-15**: migración `b1c2d3e4f5a6` (mapeo Admin→Superusuario, Administradora→Directora, Auxiliar→Auxiliar Contable); deps y `ROLE_VIEWS`; script `aplicar_estructura_usuarios.py` (7 cuentas en LAN); `MANUAL-DE-USUARIO.md` actualizado. Entrega de contraseñas **aplazada** por decisión del Superusuario.
- ~~**Ops PC servidor LAN**~~ → ✅ **2026-07-15**: `ops/ESTADO-OPERATIVO-PC.md`, `ops/HOY-GO-LIVE.md`, `ops/smoke-prod.py`, backups + offsite OneDrive, paquete `Entrega-Contador-PUC`, login UX (API caída / rate limit).
- ~~**#5 resto clave backup**~~ → ✅ **2026-07-17**: offsite OneDrive verificado; `BACKUP_ENCRYPTION_KEY` solo en `backend\.env`; `RECORDATORIO-CLAVE-BACKUP.txt` sin valor en claro; docs ops/README/LEEME actualizados.
- ~~**Docs desfasadas (README lotes/roles, ESTADO-OPERATIVO 4 vs 7 usuarios)**~~ → ✅ **2026-07-17**.
- ~~**#4 UVT 2026 (valor base)**~~ → ✅ **2026-07-17**: `UVT_VALOR` default **52374** (DIAN Res. 000238 de 2025). Queda del Contador: flags `retiene_*` en clientes.
- ~~**#22/#23 infra cumplimiento**~~ → ✅ **2026-07-17**: `DIAN_*` + `HABEAS_DATA_TEXTO` en config; `GET /api/v1/ventas/empresa`; bloque resolución + pie Habeas en `printFactura`; columnas `habeas_data_aceptado/fecha` en clientes (migración `c6d7e8f9a0b1`) + checkbox en UI. Falta resolución real y texto legal final.
- ~~**#24 redondeo retenciones**~~ → ✅ **2026-07-17**: `RETENCION_REDONDEO` (`half_even` \| `half_up`) + `app/core/money.py` + tests `no_db`. Contador elige el modo en `.env`.
- ~~**#4 UX retenedores**~~ → ✅ **2026-07-17**: filtro “Solo retenedores”, export CSV, columna Habeas; **plantilla + import CSV** de flags (`import_retenciones.py`, ContableDep). Queda rellenar con datos reales del Contador.
- ~~**BUG-004/005/006**~~ → ✅ cerrados en código (2026-07-10/15); `REPORTE_BUGS.md` sincronizado 2026-07-17.
- **#27 E2E CI** → timeouts/retry y naming Superusuario (2026-07-17); job sigue informativo (`continue-on-error`).
- ~~**Go-live / tests sin Contador (B+C)**~~ → ✅ **2026-07-17**: `ops/TESTES-LOCAL-POSTGRES.md`, `ops/run-tests.ps1`, `ops/CHECKLIST-GO-LIVE-DIARIO.md`, smoke ampliado, manual (roles/Habeas/import retenciones); tests de locks/password alineados a Postgres y política de claves.
- ~~**#20 checklist Alegra**~~ → ✅ **2026-07-17**: `ops/ACTIVAR-ALEGRA-DIAN.md`; `GET /alegra/status` devuelve pasos si no hay token (sin 400).
- ~~**#21/#21b decisiones propuestas**~~ → ✅ doc `ops/DECISIONES-PRODUCTO-SIN-CONTADOR.md` (descartar Electron; no multi-bodega en v0.3) — pendiente confirmación del dueño.
- **Pendientes vivos:** ver `PENDIENTES.md` (40ª rev) — Contador #1–3/#8; #4 datos; #7 entrega; token Alegra real; confirmación #21/#21b.
