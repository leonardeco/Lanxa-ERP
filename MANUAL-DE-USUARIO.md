# Manual de Usuario — Super Ozono ERP

Guía práctica para el uso diario del sistema. No necesitas conocimientos técnicos.

---

## 1. Entrar al sistema

1. Abre el acceso directo **"Super Ozono ERP"** del escritorio, o el navegador en la
   dirección que te indicó el administrador (en la red local suele ser
   `https://192.168.1.48:5173` — el admin te confirma si la IP cambió).
2. Escribe tu **correo** y **contraseña** y pulsa **Acceder al Sistema**.
3. **Primera vez:** el admin te da una contraseña temporal. Entra y **cámbiala de
   inmediato** (Usuarios & Accesos → cambiar contraseña, o pide al Superusuario).
   Requisitos: mínimo **8 caracteres**, al menos **una letra y un dígito**. No
   compartas tu clave.
4. Si olvidaste tu contraseña, pídele al **Superusuario** que te la restablezca
   (Usuarios & Accesos → Restablecer contraseña). El sistema no envía correos.

> 🔒 La sesión se mantiene sola mientras trabajas. Si dejas el sistema abierto sin
> usar por mucho tiempo, puede pedirte entrar de nuevo — es normal, es por seguridad.
>
> Si el navegador avisa de “conexión no segura”, el admin debe instalar el
> certificado de la empresa (`certs\superozono-ca.crt`) una sola vez en ese PC.
>
> Si dice que **no puede conectar al servidor**, en el PC servidor hay que ejecutar
> `start.bat` (o el acceso de escritorio) y esperar a que Backend y Frontend estén abiertos.
> Si pide “espera 1 minuto”, son demasiados intentos fallidos de login (protección).

**Qué ves según tu perfil:**

| Perfil | Módulos disponibles |
|---|---|
| Superusuario | Todo el sistema (incluye Usuarios & Accesos) |
| Directora | Dashboard, contabilidad, ventas, compras, cartera, inventario, reportes |
| CEO | Dashboard, reportes e inventario/ventas/compras/cartera en consulta |
| Contador | Área contable, cartera, reportes; ventas/compras |
| Auxiliar Contable | Contabilidad operativa, ventas, compras, cartera y reportes |

---

## 2. El Dashboard (pantalla de inicio)

Al entrar ves:
- **🔔 Alertas de cartera** (si las hay): facturas **vencidas** y las que **vencen
  esta semana**, tanto por cobrar como por pagar. Revísalas a diario.
- Estadísticas del mes: ventas, facturas, clientes, productos con stock bajo.
- Ventas por marca.

---

## 3. Vender (módulo Ventas & Comercial)

### 3.1 Registrar un cliente nuevo
1. **Ventas & Comercial → pestaña Clientes → + Nuevo Cliente**.
2. Llena NIT, razón social y datos de contacto.
3. **Importante (sección "Perfil tributario")**: si el cliente es agente retenedor,
   marca las casillas ReteFuente / ReteIVA / ReteICA — el sistema calculará las
   retenciones automáticamente en sus facturas. Si tienes dudas, pregunta a la contadora.
4. **Persona natural:** puedes marcar la casilla de **Habeas Data** (autorización de
   tratamiento de datos). Queda registrada la fecha.
5. **Varios clientes a la vez (Superusuario / área contable):** en Clientes usa
   **Plantilla** (baja un CSV), edita Sí/No de retenciones en Excel e **Importar**.
   También puedes filtrar “Solo retenedores” y exportar CSV de la vista.

### 3.2 Hacer una factura
1. **Ventas & Comercial → pestaña Nueva Venta**.
2. Elige el cliente y agrega los productos con cantidad y precio.
3. El sistema calcula subtotal, IVA, retenciones y total solo.
4. Guarda — la factura queda en estado **Borrador** (todavía se puede corregir).

### 3.3 Confirmar la factura
1. En la pestaña **Facturas**, busca la factura y pulsa **Confirmar**.
2. Al confirmar, el sistema hace 3 cosas automáticamente:
   - **Descuenta el inventario** (si no hay stock suficiente, no deja confirmar).
   - Crea la **cuenta por cobrar** en Cartera.
   - Registra el **asiento contable**.
3. Puedes **imprimir** la factura en PDF con el botón de impresión.

### 3.4 Anular una factura
- Botón **Anular** (solo **Superusuario** o **Directora**). El inventario y la
  contabilidad se reversan solos. La factura anulada queda visible para trazabilidad.

### 3.5 Imprimir factura
- Botón de impresión/PDF. Si aún no hay resolución DIAN configurada, el pie indica
  que es **documento interno** del ERP (no factura electrónica).

---

## 4. Cobrar (módulo Cartera — CxC)

1. **Cartera → pestaña CxC**: ves todas las facturas pendientes de cobro con sus días
   de vencimiento.
2. Cuando el cliente pague (total o parcial): botón **Abonar**, escribe el valor.
3. El sistema genera un **Recibo de Caja numerado (RC-0001, RC-0002…)** que puedes
   imprimir y entregarle al cliente.
4. Cuando el saldo llegue a cero, la factura pasa a **Pagado** automáticamente.

> ⚠️ El sistema no deja abonar más del saldo pendiente.

---

## 5. Comprar (módulo Compras & Proveedores)

### 5.1 Registrar la factura de un proveedor
1. **Compras → Nueva Compra**: elige el proveedor, agrega los ítems.
   - Si el ítem es un producto del inventario, selecciónalo en la lista — así la
     compra alimentará el stock.
2. Guarda (queda en **Borrador**) y luego **Confirma**.
3. Al confirmar, automáticamente:
   - **Entra la mercancía al inventario**.
   - Se crea la **cuenta por pagar** en Cartera.
   - Se registra el **asiento contable**.

### 5.2 Pagar al proveedor
1. **Cartera → pestaña CxP** → botón **Pagar/Abonar** sobre el documento.
2. Se genera el **Comprobante de Egreso (CE-0001…)** imprimible.
3. El estado de pago de la compra se actualiza solo (Parcial → Pagado).

---

## 6. Inventario

- **Inventario → Dashboard**: valor total del inventario y productos con stock bajo.
- **Movimientos (Kardex)**: historial completo de entradas y salidas — cada movimiento
  dice de qué compra/venta vino, quién lo hizo y cómo quedó el stock.
- **Ajuste manual** (solo Admin/Administradora): para correcciones físicas
  (conteo, daños, muestras). Siempre escribe el motivo.

---

## 7. Reportes

**Reportes & BI** (solo Admin) tiene 6 pestañas:

| Pestaña | Para qué sirve |
|---|---|
| ⏰ Aging de Cartera | Cuánto te deben y cuánto debes, por antigüedad |
| 📦 Compras y Ventas por Período | Totales por proveedor, cliente y marca |
| 🧾 Retenciones Acumuladas | Lo retenido y lo que te retuvieron (para declaraciones) |
| 📈 Estado de Resultados | Ingresos, costos y gastos del período |
| ⚖️ Balance General | Activos, pasivos y patrimonio a una fecha |
| 📖 Libro Diario | Todos los asientos contables (clic en uno para ver el detalle) |

> 💡 Todos tienen el botón **⬇ Exportar Excel** — el archivo se descarga y se abre
> directo en Excel, listo para enviarle a la contadora.

---

## 8. Preguntas frecuentes

**"No me deja confirmar una venta"** → Casi siempre es falta de stock. Revisa el
mensaje: te dice qué producto falta y cuánto hay disponible.

**"Me equivoqué en una factura ya confirmada"** → No se edita: se **anula** (Admin/
Administradora) y se hace de nuevo. Todo el reverso es automático.

**"No veo un módulo que antes veía"** → Tu perfil define qué ves. Habla con el Admin.

**"El navegador dice que la conexión no es segura"** → Falta instalar el certificado
de confianza en ese PC (una sola vez). Pide al administrador que siga la guía de
`DOCUMENTACION.md` sección 6.

**"¿Cada cuánto se hace copia de seguridad?"** → Automática todos los días a las
2:00 am en el PC servidor. Además, el administrador debe copiarla periódicamente
fuera de ese PC.

---

## 9. Buenas prácticas

- **Cambia tu contraseña** el primer día (Usuarios & Accesos → Cambiar mi contraseña).
- **No compartas tu usuario** — cada movimiento queda registrado a nombre de quien lo hizo.
- Revisa las **alertas del Dashboard** al empezar el día.
- Ante cualquier duda contable (retenciones, cuentas), consulta a la contadora antes
  de confirmar el documento — confirmar genera asientos contables.
