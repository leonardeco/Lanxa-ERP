# Design — Run 6: tenant Perú + módulo Ventas Diarias

- **Goal:** dar de alta Perú como segunda empresa (tenant) del ERP, con un
  módulo de ventas propio calcado de su flujo real (contraentrega por guía),
  importar su histórico de Excel (Enero–Julio 2026) y habilitar captura en
  vivo desde la UI.
- **Depende de:** Runs 2–5 (tenancy foundation, ya implementados y dormidos
  en producción LAN/SQLite).
- **Contexto:** las auxiliares contables de Colombia, Perú y (a futuro)
  Ecuador comparten oficina y LAN — un solo servidor (`start.bat`, SQLite),
  sin nube. Perú traía su control en `SUPEROZONO PERU DIARIAS.xlsx`
  (Escritorio), con 7 hojas mensuales, ~944 filas de venta reales entre
  Enero y Julio 2026.

## Alcance

1. Alta del tenant Perú vía el endpoint ya existente
   `POST /api/v1/tenants/onboard` (no requiere código nuevo).
2. Módulo nuevo `VentaDiaria` (no reutiliza `VentaDocumento`/`VentaDetalle`
   de Colombia — ese modelo trae IVA, retefuente/reteica y Alegra, que no
   aplican al flujo de Perú).
3. Script de importación única del Excel histórico a la tabla nueva.
4. UI de captura en vivo para que la auxiliar de Perú deje el Excel y
   trabaje directo en el ERP.

## Fuera de alcance (explícitamente, para no mezclar con este Run)

- Tenant Ecuador — se replica este mismo patrón cuando llegue su Excel.
- Dashboard consolidado de KPIs entre Colombia/Perú/Ecuador — pendiente
  definir conversión de moneda (COP/PEN/USD) y de que exista el tenant
  Ecuador.
- Facturación electrónica / IVA / Alegra para Perú.
- RLS de Postgres — sigue siendo no-op en SQLite; el aislamiento real en
  este despliegue es el filtro a nivel de aplicación (`for_tenant`,
  `get_for_tenant`, stamp en insert), que ya funciona igual en SQLite.

## Arquitectura

Se activa la infraestructura de tenancy ya construida (Runs 2–5), sin tocar
el despliegue: sigue siendo un solo proceso `uvicorn` vía `start.bat`,
SQLite, misma LAN. La auxiliar de Perú tiene su propio usuario con
`tenant_id` = Perú; el contextvar de tenant (fijado al autenticar) filtra
automáticamente todas sus consultas. No hay separación de red ni de
servidor entre países — es la misma base de datos, separada por
`tenant_id`.

## Modelo de datos nuevo

Reutiliza `Producto` y `Cliente` (ya son `TenantScoped`) sembrando catálogo
propio de Perú (productos: BIOCIDA, STAR, SUELO, AFILIACIÓN...; clientes
por DNI) bajo su tenant, sin tocar el catálogo de Colombia.

```
VentaDiaria (cabecera, TenantScoped) — una por guía de envío
- fecha: Date
- asesor: str            # vendedor
- guia: str | None        # número de guía del courier
- codigo_guia: str | None  # código corto (ej. "HD3N")
- cliente_id: FK Cliente
- estado: enum (Entregado, Devolucion, EnDestino, ...)
- forma_pago: str | None
- notas: str | None

VentaDiariaDetalle (línea, TenantScoped) — una por producto dentro de la guía
- venta_diaria_id: FK VentaDiaria
- producto_id: FK Producto
- cantidad: Decimal
- venta: Decimal | None
- abono_1: Decimal | None
- abono_2: Decimal | None
- saldo: Decimal            # calculado: venta - abono_1 - abono_2 (nunca None)
```

El abono/saldo se modela por línea (no por cabecera) porque así es como
opera hoy Perú: en el Excel una misma guía con dos productos (ej. BIOCIDA +
AFILIACIÓN) puede traer venta/abono en una sola de las líneas.

## Importación del histórico

Script de un solo uso (mismo patrón que
`backend/scripts/migrate_rol_constraint.py` / el importador de inventario
de `2026-07-09-importador-inventario.md`):

1. Lee las 7 hojas mensuales del `.xlsx`, normalizando la fila de encabezado
   (no está siempre en la misma fila: Enero fila 2, Febrero fila 3, Abril
   en adelante fila 1).
2. Crea/reutiliza `Producto` y `Cliente` bajo el tenant Perú.
3. Convierte cada guía en `VentaDiaria` + sus `VentaDiariaDetalle`.
4. Salta filas vacías y las de total al cierre de cada mes (son sumas, no
   ventas).
5. **Filas de pago suelto** (ej. `PAGO AUGURIO RODRIGUEZ`, sin producto ni
   guía, vinculadas al cliente solo por nombre en texto): se importan como
   un registro de abono aparte, ligado por fecha + nombre de cliente
   (best-effort), marcado explícitamente para revisión manual de la
   auxiliar de Perú — no hay forma confiable de saber a cuál venta exacta
   abonan.
6. **Columna "VALOR FLETE" con valores implausibles** (ej. 296500 en una
   venta de 238): se importa tal cual, sin reinterpretar su significado, y
   queda marcada para preguntarle a la auxiliar de Perú qué representa
   realmente antes de usarla en cualquier reporte.
7. Se corre primero sobre una copia de `superozono.db`, se valida el
   conteo de filas importadas contra el conteo esperado por mes (Enero 120,
   Febrero 123, Marzo 73, Abril 76, Mayo 189, Junio 182, Julio 181), y solo
   entonces se aplica a la base real.

## Captura en vivo (UI)

Sección nueva "Ventas Diarias" en el frontend, mismo patrón visual que el
módulo de Ventas de Colombia:

- Formulario: fecha, asesor, guía, cliente, líneas de producto repetibles.
- Saldo calculado automáticamente (venta − abono_1 − abono_2) — evita el
  error de cálculo manual que tenía el Excel.
- Tabla filtrable por mes/estado/asesor, con totales del mes (venta,
  recaudado, saldo pendiente) — alcance solo del tenant Perú, no el
  dashboard cruzado entre países.
- Rol: `Auxiliar Contable` (ya existe en el sistema de roles), scoped
  automáticamente a su tenant.

## Verificación

- Tests backend: CRUD de `VentaDiaria`/`VentaDiariaDetalle` + aislamiento
  por tenant, siguiendo el patrón de `test_tenant_http_isolation.py`.
- Prueba en navegador real (Chromium): login auxiliar Perú → crear una
  venta diaria → confirmar que no ve nada del tenant Colombia y viceversa.
  Esto no es opcional: cambios de auth/sesión en este proyecto solo se dan
  por verificados tras un paso real en navegador, no solo con pytest.
- Import: correr sobre copia de la BD, validar conteos antes de aplicar a
  producción.

## Preguntas abiertas para la auxiliar de Perú (no bloquean el desarrollo, sí el uso de esos datos en reportes)

- ¿Qué representa realmente la columna "VALOR FLETE" cuando trae valores
  como 296500, 2200903, 601000? No parece ser costo de flete en soles.
- ¿Las filas "PAGO <nombre>" deben quedar vinculadas a una venta específica
  o son abonos generales de cartera del cliente?
- **(Encontrado al correr el importador contra el Excel real, 2026-07-23):**
  Febrero y Marzo usan el encabezado "V. VENTA" en vez de "VENTA" — el
  importador ahora lo trata como el mismo campo (monto de venta). ¿Es
  correcto asumir que son lo mismo, o "V. VENTA" significa otra cosa en
  esos meses?
- Febrero trae una sola columna "RECAUDO" (sin "1"/"2") — el importador la
  mapea a `abono_1`. ¿Confirma la auxiliar que es el mismo concepto que
  "RECAUDO 1" en los demás meses?
- Algunas filas de pago suelto en Febrero tienen `CLIENTE` = "YAPE" (app de
  pagos peruana) o un nombre real, no "PAGO <nombre>" — el importador las
  detecta ahora por `ESTADO == "PAGO"` en vez de por el texto del cliente.
  ¿Es ese el criterio correcto para todos los meses?
