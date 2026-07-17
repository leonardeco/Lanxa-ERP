# Instrucciones — reunión Contador (#1 validar PUC)

**Empresa:** TECNOLOGÍA E INNOVACIÓN SUPER OZONO S.A.S.  
**ERP:** Super Ozono v0.3.0 (LAN)  
**URL:** https://192.168.1.131:5173  
**Usuario Contador:** `contador@superozonoglobal.com` (clave temporal en entrega)

---

## 1. Antes de la reunión (Superusuario)

- [ ] ERP encendido (`start.bat`)
- [ ] Contador puede entrar y ve módulos contables
- [ ] Entregado el archivo `MAPEO-PUC-PARA-CONTADOR.md`
- [ ] Ideal: tener 1 venta confirmada de prueba y 1 compra de prueba (o datos reales)

---

## 2. Qué debe revisar el Contador en el ERP

| Paso | Dónde | Qué mirar |
|---|---|---|
| 1 | Contabilidad → Plan de Cuentas | ¿Los códigos del PUC coinciden con el plan oficial de la empresa? |
| 2 | Reportes → Libro Diario | Asientos de una venta confirmada y una compra confirmada |
| 3 | Reportes → Estado de Resultados / Balance | Si las cuentas “cuadran” con su práctica |
| 4 | Cartera → abono de prueba | ¿El recaudo va a **Caja 1105** o debería ir a **Bancos 1110**? |

---

## 3. Decisiones que necesitamos por escrito

Responder en el propio `MAPEO-PUC-PARA-CONTADOR.md` o en un correo/nota:

1. **Ingresos por venta:** ¿4135 (comercio) u otra (p. ej. 4120 manufactura)?
2. **Compras:** ¿todo a inventario 1435, o separar gastos 51xx/52xx?
3. **Caja vs Bancos** en abonos CxC y pagos CxP.
4. **Retenciones:** ¿auxiliares 1355xx / 2365xx correctos?
5. **Clientes retenedores** (ítem #4 resto): marcar flags `retiene_*` en maestros. UVT default ya es **52374** (DIAN 2026).
6. **Método de costeo** (ítem #3): promedio ponderado ¿OK con el kardex actual?
7. **Costo de venta** (ítem #8): ¿confirmar asiento DB 6135 / CR 1435 al confirmar venta?

---

## 4. Después de la reunión (dev)

Con las respuestas firmadas o anotadas:

1. Ajustar mapeo en `backend/app/modules/contabilidad/asientos.py` (y PUC seed si aplica).
2. Actualizar `MAPEO-PUC-PARA-CONTADOR.md` a estado **VALIDADO**.
3. Si aprueban costeo → implementar **#8 asiento de costo de venta**.
4. Cargar inventario real (#2) con el importador ya listo.

---

## 5. Alcance del rol Contador en el ERP

Puede ver/usar: dashboard, PUC, centros de costo, períodos, tributarios, cartera, reportes, ventas y compras.  
**No** gestiona usuarios ni anula facturas/compras (eso es Superusuario o Directora).
