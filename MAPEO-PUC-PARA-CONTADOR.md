# Mapeo PUC del motor contable — PARA VALIDACIÓN DEL CONTADOR

**Empresa:** TECNOLOGÍA E INNOVACIÓN SUPER OZONO S.A.S. — NIT 901.841.798-5
**Fecha:** 2 de julio de 2026
**Estado:** ⚠️ **BORRADOR** — el ERP ya genera asientos de partida doble automáticamente
con este mapeo, pero los códigos de cuenta deben ser validados por el contador antes
de usar el Estado de Resultados y el Balance General para fines oficiales.

---

## Cómo funciona

Cada vez que en el ERP se **confirma una venta**, se **confirma una compra** o se
**registra un abono** en cartera (CxC/CxP), el sistema genera automáticamente un
asiento contable de partida doble. Al **anular** un documento se genera el asiento
de reverso (espejo), quedando ambos en el libro diario para trazabilidad.

Los asientos se consultan en **Reportes → Libro Diario**, y alimentan el
**Estado de Resultados** y el **Balance General** (mismo módulo).

---

## Mapeo actual (a validar)

### 1. Venta confirmada (factura interna SOG-V-####)

| Cuenta | Nombre en el sistema | Débito | Crédito |
|---|---|---|---|
| **130505** | Clientes nacionales | Total de la factura (neto de retenciones) | |
| **135515** | Retención en la fuente a favor | ReteFuente que nos practicó el cliente | |
| **135517** | ReteIVA a favor | ReteIVA que nos practicó | |
| **135518** | ReteICA a favor | ReteICA que nos practicó | |
| **413595** | Ingresos por ventas de productos | | Base gravable |
| **240801** | IVA generado en ventas | | IVA de la factura |

**Preguntas para el contador:**
- ¿El ingreso va a **4135** (comercio al por mayor/menor) o corresponde otra cuenta
  según la actividad (p. ej. 4120 industria manufacturera si producen los biocidas)?
- ¿Se requiere desglosar el ingreso por marca/centro de costo a nivel de subcuenta?
- ¿Las retenciones a favor van en 1355xx como está, o prefieren auxiliares distintos?

### 2. Compra confirmada (documento SOG-CP-####)

| Cuenta | Nombre en el sistema | Débito | Crédito |
|---|---|---|---|
| **143501** | Inventario de mercancías | Base gravable | |
| **240802** | IVA descontable en compras | IVA de la compra | |
| **220501** | Proveedores nacionales | | Total a pagar (neto de retenciones) |
| **236540** | Retención en la fuente practicada | | ReteFuente que practicamos |
| **236701** | ReteIVA practicado | | ReteIVA que practicamos |
| **236801** | ReteICA practicado | | ReteICA que practicamos |

**Preguntas para el contador:**
- ¿Toda compra va a inventario (**1435**), o hay compras de gasto (servicios,
  papelería) que deberían ir a cuentas 51xx/52xx? *Hoy el sistema manda todo a 143501.*
- ¿El IVA descontable se maneja en 2408 (neto) como está, o prefieren 2408 con
  auxiliares separados para generado/descontable? El sistema usa 240801/240802.
- Confirmar los auxiliares de retenciones practicadas (2365/2367/2368).

### 3. Abono recibido de cliente (Recibo de Caja RC-####)

| Cuenta | Débito | Crédito |
|---|---|---|
| **110505** Caja general | Valor del abono | |
| **130505** Clientes nacionales | | Valor del abono |

**Pregunta:** ¿los recaudos entran a Caja (1105) o a Bancos (**1110**)? Si es
consignación directa, habría que agregar la cuenta de bancos y elegir en cada abono.

### 4. Pago a proveedor (Comprobante de Egreso CE-####)

| Cuenta | Débito | Crédito |
|---|---|---|
| **220501** Proveedores nacionales | Valor del pago | |
| **110505** Caja general | | Valor del pago |

**Pregunta:** misma que la anterior — ¿Caja o Bancos?

---

## Qué NO registra el motor todavía

- **Costo de la mercancía vendida (6135 vs 1435):** al confirmar una venta se descuenta
  el inventario físico (kardex), pero el asiento del costo (DB 6135 / CR 1435) no se
  genera aún — requiere definir el método de costeo (promedio ponderado es lo natural
  con el kardex actual). Sin esto, la utilidad del P&L es utilidad sobre ingresos, no
  sobre margen. **Es la primera extensión recomendada tras validar este mapeo.**
- Nómina, depreciaciones, ajustes manuales y cierres de ejercicio.

---

## Cómo se corrige un código

Cada código vive en **una sola línea** del archivo
`backend/app/modules/contabilidad/asientos.py` (diccionario `CUENTAS_MOTOR` y las
funciones `asiento_*`). Cambiar un código es editar esa línea; los asientos ya
generados no se modifican (si hace falta, se anula el documento y se re-confirma).

Si una cuenta del mapeo no existe en el PUC del sistema, el motor la **crea
automáticamente** con el nombre de la tabla de arriba — el contador puede renombrarla
desde Contabilidad → Plan de Cuentas.
