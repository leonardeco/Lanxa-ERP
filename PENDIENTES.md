# Pendientes — Super Ozono ERP

Backlog vivo del proyecto. Actualizado: **2 de julio de 2026**.
Estado general: 198 tests API (95% cobertura) + 25 componentes + 5 E2E, CI verde, 0 CVEs.

---

## 🔴 Bloqueados por el negocio (no son de código)

| # | Pendiente | Quién | Notas |
|---|---|---|---|
| 1 | **Validar el mapeo PUC** del motor contable | Contadora | Documento listo: [`MAPEO-PUC-PARA-CONTADOR.md`](./MAPEO-PUC-PARA-CONTADOR.md) — tiene las preguntas concretas (4135 vs 4120, Caja vs Bancos, compras de gasto) |
| 2 | **Datos maestros reales**: PUC definitivo, inventario inicial, saldos de apertura | Contadora + empresa | Las tablas ya existen (`SaldoInicial`, seeds); solo falta la información |
| 3 | Definir **método de costeo** (promedio ponderado recomendado con el kardex actual) | Contadora | Prerequisito del ítem 7 |
| 4 | Confirmar **`UVT_VALOR` 2026** y activar flags `retiene_*` en clientes retenedores | Contadora | Hoy placeholder = 49799; afecta el umbral de retefuente en ventas |

## 🟠 Operativo (administrador del PC servidor)

| # | Pendiente | Notas |
|---|---|---|
| 5 | **Copiar backups fuera del PC servidor** (NAS/nube/otro PC) + guardar `BACKUP_ENCRYPTION_KEY` en un gestor de contraseñas | Riesgo #1: hoy BD, backups y clave viven en el mismo disco. El restore ya está verificado con simulacro (2026-07-02) |
| 6 | Desplegar la actualización al servidor siguiendo [`DESPLIEGUE.md`](./DESPLIEGUE.md) | Incluye: `pip install`, rename `ACCESS_TOKEN_EXPIRE_HOURS`→`ACCESS_TOKEN_EXPIRE_MINUTES=15`, `alembic stamp` (una vez), instalar CA en PCs cliente nuevos |
| 7 | Entregar [`MANUAL-DE-USUARIO.md`](./MANUAL-DE-USUARIO.md) a los 4 usuarios y que cambien su contraseña inicial | |

## 🟡 Técnico — deuda puntual (dev)

| # | Pendiente | Notas |
|---|---|---|
| 8 | **Asiento de costo de venta** (DB 6135 / CR 1435 al confirmar venta) | Depende del ítem 3. Sin esto el P&L muestra ingresos, no margen |
| 9 | **Migrar `security.py` de passlib a bcrypt directo** | passlib 1.7.4 (sin mantenimiento) bloquea bcrypt ≥ 4.1 — PR #7 de Dependabot rechazado con evidencia de CI. Probar login con hashes existentes al migrar |
| 10 | Migración Alembic de **nulabilidad legacy** (BD creadas pre-tipado vs modelos 2.0) | Drift documentado en `alembic/versions/72f7b9fae762`. Requiere backfill revisado contra la BD real del servidor |
| 11 | Quitar `create_all` del lifespan en producción (dejar solo `alembic upgrade head`) | Hoy conviven; el día que discrepen gana el que corra primero |
| 12 | Locks de concurrencia (`with_for_update`) en abonos y stock | **Solo si** el despliegue pasa a multi-worker; con uvicorn single-worker en LAN no aplica |
| 13 | Extraer servicios de dominio (`confirmar_venta` orquesta stock+CxC+asiento inline en el router) | Refactor de mantenibilidad, sin urgencia |
| 14 | Manejo de errores consistente en frontend (varios `.catch(() => {})` silenciosos) | El usuario no se entera si un panel falló al cargar |

## 🟢 Funcional — siguientes features (por prioridad de negocio)

| # | Feature | Alcance |
|---|---|---|
| 15 | **Devoluciones** (notas crédito/débito) | Devolución parcial sin anular la factura completa; reverso parcial de inventario, cartera y asientos |
| 16 | **Cotizaciones** | Flujo cotización → aprobación → conversión a venta (típico B2B) |
| 17 | Confirmación al cerrar formularios con datos sin guardar | UX: el modal de Nueva Compra pierde 10 líneas digitadas sin preguntar |
| 18 | **RRHH y nómina** (Fase 2) | Empleados, contratos, liquidación — requiere definiciones de negocio propias |
| 19 | **Auditoría de cambios** (audit log) | Quién modificó qué en productos/clientes/parámetros (los asientos ya guardan usuario) |
| 20 | Activación Alegra con facturación electrónica DIAN | La integración está construida y testeada con mocks; falta cuenta/token real y rotación documentada (SEC-002) |
| 21 | Empaquetado Electron (Fase 4) | App de escritorio .exe |

## 🔵 Nice-to-have

- Seeder de datos demo (50 clientes, 200 ventas) para probar rendimiento de UI
- Tests de los utilitarios de impresión (`printFactura.ts`, etc.)
- Tags de release (`v0.3.0`) y `APP_VERSION` desde el tag
- Reemplazar el panel "Plan de Desarrollo por Fases" del Dashboard por un KPI de negocio (margen del mes / top morosos)
- Ocultar del menú los módulos "🚧 en desarrollo" (RRHH, Plataformas) hasta que existan

---

**Regla de mantenimiento:** al completar un ítem, moverlo a la tabla de completados de
`DOCUMENTACION.md` (sección 13) con fecha, y registrar la sesión en `BITACORA.md`.
