/**
 * Centros de Costo View — Marcas y Áreas
 */

const CENTROS_COSTO_DATA = [
  { codigo: 'CC-01', nombre: 'Superozono', tipo: 'Marca', marca: 'Superozono', notas: '', activo: true },
  { codigo: 'CC-02', nombre: 'Biozono', tipo: 'Marca', marca: 'Biozono', notas: '⚠️ Pendiente confirmar', activo: true },
  { codigo: 'CC-03', nombre: 'Ecoozono', tipo: 'Marca', marca: 'Ecoozono', notas: '', activo: true },
  { codigo: 'CC-04', nombre: 'Agroking', tipo: 'Marca', marca: 'Agroking', notas: '', activo: true },
  { codigo: 'CC-05', nombre: 'Ozono Evolution', tipo: 'Marca', marca: 'Ozono Evolution', notas: '', activo: true },
  { codigo: 'CC-06', nombre: 'Agro Vital', tipo: 'Marca', marca: 'Agro Vital', notas: '', activo: true },
  { codigo: 'CC-07', nombre: 'Agro Fusion', tipo: 'Marca', marca: 'Agro Fusion', notas: '', activo: true },
  { codigo: 'CC-08', nombre: 'Hiper Ozono', tipo: 'Marca', marca: 'Hiper Ozono', notas: '', activo: true },
  { codigo: 'CC-09', nombre: 'Ozono Pro', tipo: 'Marca', marca: 'Ozono Pro', notas: '', activo: true },
  { codigo: 'CC-10', nombre: 'Ozomax', tipo: 'Marca', marca: 'Ozomax', notas: '', activo: true },
  { codigo: 'CC-ADM', nombre: 'Administración', tipo: 'Área', marca: '—', notas: '', activo: true },
  { codigo: 'CC-LOG', nombre: 'Logística y bodega', tipo: 'Área', marca: '—', notas: '', activo: true },
]

export default function CentrosCostoView() {
  return (
    <div className="fade-in">
      <div className="table-container">
        <div className="table-header">
          <div className="table-title">🏷️ Centros de Costo — Marcas y Áreas</div>
          <div className="table-count">{CENTROS_COSTO_DATA.length} centros</div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Código</th>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Marca Asociada</th>
              <th>Notas / Estado</th>
            </tr>
          </thead>
          <tbody>
            {CENTROS_COSTO_DATA.map((cc) => (
              <tr key={cc.codigo}>
                <td className="code">{cc.codigo}</td>
                <td style={{ fontWeight: 600 }}>{cc.nombre}</td>
                <td>
                  <span className={`badge ${cc.tipo === 'Marca' ? 'blue' : 'purple'}`}>
                    {cc.tipo}
                  </span>
                </td>
                <td>{cc.marca}</td>
                <td>
                  {cc.notas ? (
                    <span style={{ color: 'var(--amber-400)', fontSize: '0.75rem' }}>{cc.notas}</span>
                  ) : (
                    <span className="badge green">Activo</span>
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
