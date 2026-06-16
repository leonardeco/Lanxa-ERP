/**
 * Parámetros Tributarios View
 */

const TRIBUTARIOS_DATA = [
  { concepto: 'IVA general', tarifa: '19.000%', base: 'Ventas gravadas', puc: '2408', notas: 'Tarifa general vigente' },
  { concepto: 'IVA tarifa reducida', tarifa: '5.000%', base: 'Productos tarifa 5%', puc: '2408', notas: 'Confirmar productos aplicables' },
  { concepto: 'Retención en la fuente - compras', tarifa: '2.500%', base: 'Compras a declarantes', puc: '2365', notas: 'Confirmar tarifa por concepto' },
  { concepto: 'Retención en la fuente - servicios', tarifa: '4.000%', base: 'Servicios', puc: '2365', notas: 'Confirmar tarifa por concepto' },
  { concepto: 'Retención en la fuente - honorarios', tarifa: '11.000%', base: 'Honorarios', puc: '2365', notas: 'Confirmar tarifa por concepto' },
  { concepto: 'ReteIVA', tarifa: '15.000%', base: '% del IVA en compras', puc: '2367', notas: 'Sobre el valor del IVA' },
  { concepto: 'ReteICA', tarifa: '—', base: 'Según municipio (por mil)', puc: '2368', notas: '⚠️ Depende del municipio' },
  { concepto: 'ICA (industria y comercio)', tarifa: '—', base: 'Tarifa municipal (por mil)', puc: '2412', notas: '⚠️ Tarifa de Armenia/Quindío' },
]

export default function TributariosView() {
  return (
    <div className="fade-in">
      <div className="table-container">
        <div className="table-header">
          <div className="table-title">🏛️ Parámetros Tributarios e Impuestos</div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Concepto</th>
              <th>Tarifa / Valor</th>
              <th>Base de Aplicación</th>
              <th>Cuenta PUC</th>
              <th>Notas</th>
            </tr>
          </thead>
          <tbody>
            {TRIBUTARIOS_DATA.map((t) => (
              <tr key={t.concepto}>
                <td style={{ fontWeight: 500 }}>{t.concepto}</td>
                <td className="code" style={{ color: t.tarifa === '—' ? 'var(--neutral-500)' : 'var(--blue-400)' }}>
                  {t.tarifa}
                </td>
                <td>{t.base}</td>
                <td className="code">{t.puc}</td>
                <td>
                  {t.notas.includes('⚠️') ? (
                    <span style={{ color: 'var(--amber-400)', fontSize: '0.75rem' }}>{t.notas}</span>
                  ) : (
                    <span style={{ color: 'var(--neutral-500)', fontSize: '0.75rem' }}>{t.notas}</span>
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
