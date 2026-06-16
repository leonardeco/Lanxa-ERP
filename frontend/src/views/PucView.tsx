/**
 * PUC View — Plan Único de Cuentas (Decreto 2650)
 * Datos precargados del Excel de carga inicial contable
 */

const PUC_DATA = [
  { codigo: '1105', nombre: 'Caja', clase: 'Activo', naturaleza: 'Débito', tercero: false, cc: true },
  { codigo: '1110', nombre: 'Bancos', clase: 'Activo', naturaleza: 'Débito', tercero: true, cc: true },
  { codigo: '1305', nombre: 'Clientes', clase: 'Activo', naturaleza: 'Débito', tercero: true, cc: false },
  { codigo: '1355', nombre: 'Anticipo de impuestos y contribuciones', clase: 'Activo', naturaleza: 'Débito', tercero: false, cc: true },
  { codigo: '1435', nombre: 'Mercancías no fabricadas por la empresa', clase: 'Activo', naturaleza: 'Débito', tercero: false, cc: true },
  { codigo: '1455', nombre: 'Materias primas', clase: 'Activo', naturaleza: 'Débito', tercero: false, cc: true },
  { codigo: '1524', nombre: 'Equipo de oficina', clase: 'Activo', naturaleza: 'Débito', tercero: false, cc: true },
  { codigo: '1528', nombre: 'Equipo de cómputo y comunicación', clase: 'Activo', naturaleza: 'Débito', tercero: false, cc: true },
  { codigo: '2205', nombre: 'Proveedores nacionales', clase: 'Pasivo', naturaleza: 'Crédito', tercero: true, cc: true },
  { codigo: '2335', nombre: 'Costos y gastos por pagar', clase: 'Pasivo', naturaleza: 'Crédito', tercero: true, cc: true },
  { codigo: '2365', nombre: 'Retención en la fuente', clase: 'Pasivo', naturaleza: 'Crédito', tercero: false, cc: true },
  { codigo: '2367', nombre: 'Impuesto a las ventas retenido', clase: 'Pasivo', naturaleza: 'Crédito', tercero: false, cc: true },
  { codigo: '2368', nombre: 'Imp. industria y comercio retenido', clase: 'Pasivo', naturaleza: 'Crédito', tercero: false, cc: true },
  { codigo: '2370', nombre: 'Retenciones y aportes de nómina', clase: 'Pasivo', naturaleza: 'Crédito', tercero: false, cc: false },
  { codigo: '2380', nombre: 'Acreedores varios', clase: 'Pasivo', naturaleza: 'Crédito', tercero: true, cc: false },
  { codigo: '2404', nombre: 'IVA por pagar (generado)', clase: 'Pasivo', naturaleza: 'Crédito', tercero: false, cc: false },
  { codigo: '2408', nombre: 'IVA descontable (compras)', clase: 'Pasivo', naturaleza: 'Crédito', tercero: false, cc: false },
  { codigo: '2412', nombre: 'ICA por pagar', clase: 'Pasivo', naturaleza: 'Crédito', tercero: false, cc: false },
  { codigo: '3105', nombre: 'Capital suscrito y pagado', clase: 'Patrimonio', naturaleza: 'Crédito', tercero: false, cc: false },
  { codigo: '3115', nombre: 'Aportes sociales', clase: 'Patrimonio', naturaleza: 'Crédito', tercero: false, cc: false },
  { codigo: '3605', nombre: 'Utilidad del ejercicio', clase: 'Patrimonio', naturaleza: 'Crédito', tercero: false, cc: false },
  { codigo: '3705', nombre: 'Pérdidas acumuladas', clase: 'Patrimonio', naturaleza: 'Débito', tercero: false, cc: false },
  { codigo: '4135', nombre: 'Comercio al por mayor y al por menor', clase: 'Ingreso', naturaleza: 'Crédito', tercero: false, cc: true },
  { codigo: '4175', nombre: 'Devoluciones en ventas (DB)', clase: 'Ingreso', naturaleza: 'Débito', tercero: false, cc: true },
  { codigo: '5105', nombre: 'Gastos de personal', clase: 'Gasto', naturaleza: 'Débito', tercero: false, cc: true },
  { codigo: '5110', nombre: 'Honorarios', clase: 'Gasto', naturaleza: 'Débito', tercero: true, cc: true },
  { codigo: '5115', nombre: 'Impuestos', clase: 'Gasto', naturaleza: 'Débito', tercero: false, cc: false },
  { codigo: '5120', nombre: 'Arrendamientos', clase: 'Gasto', naturaleza: 'Débito', tercero: true, cc: true },
  { codigo: '5135', nombre: 'Servicios', clase: 'Gasto', naturaleza: 'Débito', tercero: false, cc: true },
  { codigo: '5195', nombre: 'Diversos', clase: 'Gasto', naturaleza: 'Débito', tercero: false, cc: true },
  { codigo: '5199', nombre: 'Provisiones', clase: 'Gasto', naturaleza: 'Débito', tercero: false, cc: false },
  { codigo: '6135', nombre: 'Comercio al por mayor (costo)', clase: 'Costo', naturaleza: 'Débito', tercero: false, cc: true },
  { codigo: '6205', nombre: 'Compras de mercancías', clase: 'Costo', naturaleza: 'Débito', tercero: true, cc: true },
  { codigo: '6225', nombre: 'Devoluciones en compras (CR)', clase: 'Costo', naturaleza: 'Crédito', tercero: true, cc: true },
]

const CLASE_COLORS: Record<string, string> = {
  Activo: 'green',
  Pasivo: 'blue',
  Patrimonio: 'purple',
  Ingreso: 'amber',
  Gasto: 'red',
  Costo: 'cyan',
}

export default function PucView() {
  return (
    <div className="fade-in">
      <div className="table-container">
        <div className="table-header">
          <div className="table-title">📋 Plan Único de Cuentas — PUC Colombiano (Decreto 2650)</div>
          <div className="table-count">{PUC_DATA.length} cuentas</div>
        </div>
        <div style={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Código PUC</th>
                <th>Nombre de la Cuenta</th>
                <th>Clase</th>
                <th>Naturaleza</th>
                <th>Req. Tercero</th>
                <th>Req. Centro Costo</th>
              </tr>
            </thead>
            <tbody>
              {PUC_DATA.map((cuenta) => (
                <tr key={cuenta.codigo}>
                  <td className="code">{cuenta.codigo}</td>
                  <td>{cuenta.nombre}</td>
                  <td>
                    <span className={`badge ${CLASE_COLORS[cuenta.clase] || 'neutral'}`}>
                      {cuenta.clase}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${cuenta.naturaleza === 'Débito' ? 'green' : 'blue'}`}>
                      {cuenta.naturaleza}
                    </span>
                  </td>
                  <td style={{ textAlign: 'center' }}>{cuenta.tercero ? '✅' : '—'}</td>
                  <td style={{ textAlign: 'center' }}>{cuenta.cc ? '✅' : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
