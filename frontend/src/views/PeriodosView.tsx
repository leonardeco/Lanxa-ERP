/**
 * Períodos Contables View
 */

const PERIODOS_DATA = Array.from({ length: 12 }, (_, i) => ({
  anio: 2026,
  mes: i + 1,
  periodo: `2026-${String(i + 1).padStart(2, '0')}`,
  estado: 'Abierto',
}))

const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

export default function PeriodosView() {
  return (
    <div className="fade-in">
      <div className="table-container" style={{ maxWidth: '800px' }}>
        <div className="table-header">
          <div className="table-title">📅 Períodos Contables — 2026</div>
          <button className="badge green" style={{ border: 'none', cursor: 'pointer', padding: '6px 12px' }}>
            + Nuevo Año
          </button>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Período</th>
              <th>Mes</th>
              <th>Año</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {PERIODOS_DATA.map((p) => (
              <tr key={p.periodo}>
                <td className="code">{p.periodo}</td>
                <td>{MESES[p.mes - 1]}</td>
                <td>{p.anio}</td>
                <td>
                  <span className="badge green">{p.estado}</span>
                </td>
                <td>
                  <button className="badge neutral" style={{ border: '1px solid var(--neutral-700)', background: 'transparent', cursor: 'pointer' }}>
                    Cerrar mes
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
