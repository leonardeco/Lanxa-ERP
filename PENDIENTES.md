# Pendientes — Super Ozono ERP

Backlog vivo del proyecto. Actualizado: **2 de julio de 2026** (7ª revisión — ✅ #15 Devoluciones: NC ventas full-stack y ND compras por API; Sprints 1-3 completados: ✅ 15a/b/c/d cartera+períodos+hora local+auxiliar; ✅ 14b logs; ✅ 9 passlib→bcrypt 5; ✅ 13c/13d/14e stock decimal, flags visibles, DV del NIT). **Este archivo es la fuente única de pendientes.**.
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
| 7a | **Drill de restore trimestral** (calendarizarlo) | El procedimiento se verificó una vez (2026-07-02); un backup solo es confiable si se prueba periódicamente |
| 7b | Documentar la vigencia del certificado TLS local y cuándo regenerarlo | `scripts/generate_tls_cert.py` — nadie sabe hoy la fecha de expiración |

## 🟡 Técnico — deuda puntual (dev)

| # | Pendiente | Notas |
|---|---|---|
| 8 | **Asiento de costo de venta** (DB 6135 / CR 1435 al confirmar venta) | Depende del ítem 3. Sin esto el P&L muestra ingresos, no margen |
| 10 | Migración Alembic de **nulabilidad legacy** (BD creadas pre-tipado vs modelos 2.0) | Drift documentado en `alembic/versions/72f7b9fae762`. Requiere backfill revisado contra la BD real del servidor |
| 11 | Quitar `create_all` del lifespan en producción (dejar solo `alembic upgrade head`) | Hoy conviven; el día que discrepen gana el que corra primero |
| 12 | Locks de concurrencia (`with_for_update`) en abonos y stock | **Solo si** el despliegue pasa a multi-worker; con uvicorn single-worker en LAN no aplica |
| 12a | Race en numeración de documentos (BUG-004/005: `MAX+1` sin lock en SOG-V/SOG-CP/RC/CE) | Mismo escenario que #12: solo aplica multi-worker. Resolver junto con #12 (lock o secuencia de BD) |
| 13 | Extraer servicios de dominio (`confirmar_venta` orquesta stock+CxC+asiento inline en el router) | Incluye unificar el patrón commit/flush entre módulos (BUG-006) y `estado` Enum vs String (ventas usa SAEnum, compras string) |
| 13a | `EmailStr` en schemas de cliente/proveedor + validaciones de formato | Hoy el email es texto libre (bitácora 2026-07-01 #7) |
| 13b | `_enrich_cxc/cxp` usan `{**obj.__dict__}` | Frágil ante cambios de modelo; pasar a construcción explícita (bitácora 2026-07-01 #8) |
| 14 | Manejo de errores consistente en frontend (varios `.catch(() => {})` silenciosos) | El usuario no se entera si un panel falló al cargar |
| 14a | Unificar Cliente/Proveedor/Tercero a nivel de modelo | CxC guarda `cliente_nit` como texto sin FK; la materialización por NIT (2026-07-02) es el puente, falta la FK real |
| 14c | Revocación de sesiones por Admin | Poder cerrar la sesión remota de un usuario (borrar sus refresh tokens) — hoy solo desactivándolo |
| 14d | Playwright en el CI (job opcional) | El smoke E2E corre solo local |

## 🟢 Funcional — siguientes features (por prioridad de negocio)

| # | Feature | Alcance |
|---|---|---|
| 15-ui | Botón de devolución en la vista de Compras | El backend de devolución a proveedor (ND-####) está completo y testeado; ventas ya tiene su modal — falta replicarlo en ComprasView |
| 16 | **Cotizaciones** | Flujo cotización → aprobación → conversión a venta (típico B2B) |
| 17 | Confirmación al cerrar formularios con datos sin guardar | UX: el modal de Nueva Compra pierde 10 líneas digitadas sin preguntar |
| 18 | **RRHH y nómina** (Fase 2) | Empleados, contratos, liquidación — requiere definiciones de negocio propias |
| 19 | **Auditoría de cambios** (audit log) | Quién modificó qué en productos/clientes/parámetros (los asientos ya guardan usuario) |
| 20 | Activación Alegra con facturación electrónica DIAN | La integración está construida y testeada con mocks; falta cuenta/token real y rotación documentada (SEC-002) |
| 21 | Empaquetado Electron (Fase 4) | App de escritorio .exe |
| 21a | Entorno de staging (aunque sea una carpeta paralela con BD copia en el mismo servidor) | Hoy todo cambio va directo a producción — riesgo de proceso, no de código |
| 21b | ¿Multi-bodega? — **pregunta de negocio** | El inventario es global; si Super Ozono maneja planta + punto de venta separados, el kardex actual no lo distingue. Confirmar con la empresa antes de diseñar |

## ⚖️ Cumplimiento Colombia (activar junto con la facturación electrónica)

| # | Pendiente | Notas |
|---|---|---|
| 22 | Requisitos DIAN en la factura impresa | Verificar razón social, régimen, y **resolución de numeración autorizada** (el consecutivo SOG-V-#### es interno) |
| 23 | Habeas Data (Ley 1581 de 2012) | Clientes persona natural: aviso de privacidad y política de tratamiento de datos |
| 24 | Política de redondeo de retenciones validada con la contadora | Hoy `round()` half-even de Python; confirmar contra la práctica DIAN |

## 🔵 Nice-to-have

- Seeder de datos demo (50 clientes, 200 ventas) para probar rendimiento de UI
- Tests de los utilitarios de impresión (`printFactura.ts`, etc.)
- Tags de release (`v0.3.0`) y `APP_VERSION` desde el tag
- Reemplazar el panel "Plan de Desarrollo por Fases" del Dashboard por un KPI de negocio (margen del mes / top morosos)
- Ocultar del menú los módulos "🚧 en desarrollo" (RRHH, Plataformas) hasta que existan
- Búsqueda por texto también en tablas de Cartera e Inventario (productos/clientes/proveedores ya la tienen)
- Política de contraseñas (complejidad/expiración) — hoy solo mínimo 8 caracteres; aceptable en LAN
- Blacklist de JTI en Redis para revocación inmediata de access tokens — innecesario con vida de 15 min (REPORTE_SEGURIDAD)

---

**Regla de mantenimiento:** al completar un ítem, moverlo a la tabla de completados de
`DOCUMENTACION.md` (sección 13) con fecha, y registrar la sesión en `BITACORA.md`.
