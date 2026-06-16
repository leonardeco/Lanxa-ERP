/**
 * Parámetros de Nómina View
 */

const NOMINA_DATA = [
  { concepto: 'Salario / Honorarios', valor: '—', tipo: '$', notas: 'Pago por prestación de servicios' },
  { concepto: 'Auxilio de transporte', valor: '0.000%', tipo: '%', notas: 'No aplica (Prestación de servicios)' },
  { concepto: 'Tope auxilio transporte', valor: '0.000%', tipo: '%', notas: 'No aplica (Prestación de servicios)' },
  { concepto: 'Salud - aporte empleado', valor: '—', tipo: '%', notas: 'El contratista aporta como independiente' },
  { concepto: 'Pensión - aporte empleado', valor: '0.000%', tipo: '%', notas: 'No aplica (Prestación de servicios)' },
  { concepto: 'Salud - aporte empresa', valor: '0.000%', tipo: '%', notas: 'No aplica (Prestación de servicios)' },
  { concepto: 'Pensión - aporte empresa', valor: '0.000%', tipo: '%', notas: 'No aplica (Prestación de servicios)' },
  { concepto: 'ARL', valor: '—', tipo: '%', notas: 'Según nivel de riesgo acordado' },
  { concepto: 'Caja de compensación', valor: '0.000%', tipo: '%', notas: 'No aplica (Prestación de servicios)' },
  { concepto: 'SENA', valor: '0.000%', tipo: '%', notas: 'No aplica (Prestación de servicios)' },
  { concepto: 'ICBF', valor: '0.000%', tipo: '%', notas: 'No aplica (Prestación de servicios)' },
  { concepto: 'Cesantías', valor: '0.000%', tipo: '%', notas: 'No aplica (Prestación de servicios)' },
  { concepto: 'Intereses sobre cesantías', valor: '0.000%', tipo: '%', notas: 'No aplica (Prestación de servicios)' },
  { concepto: 'Prima de servicios', valor: '0.000%', tipo: '%', notas: 'No aplica (Prestación de servicios)' },
  { concepto: 'Vacaciones', valor: '0.000%', tipo: '%', notas: 'No aplica (Prestación de servicios)' },
]

export default function NominaView() {
  return (
    <div className="fade-in">
      <div className="table-container">
        <div className="table-header">
          <div className="table-title">💰 Parámetros de Nómina y Laborales</div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Concepto</th>
              <th>Valor / Porcentaje</th>
              <th>Tipo</th>
              <th>Notas</th>
            </tr>
          </thead>
          <tbody>
            {NOMINA_DATA.map((n) => (
              <tr key={n.concepto}>
                <td style={{ fontWeight: 500 }}>{n.concepto}</td>
                <td className="code" style={{ color: n.valor === '—' ? 'var(--neutral-500)' : 'var(--purple-400)' }}>
                  {n.valor}
                </td>
                <td>
                  <span className={`badge ${n.tipo === '%' ? 'neutral' : 'blue'}`}>
                    {n.tipo}
                  </span>
                </td>
                <td>
                  {n.notas.includes('⚠️') ? (
                    <span style={{ color: 'var(--amber-400)', fontSize: '0.75rem' }}>{n.notas}</span>
                  ) : (
                    <span style={{ color: 'var(--neutral-500)', fontSize: '0.75rem' }}>{n.notas}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
