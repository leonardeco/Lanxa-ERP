/**
 * Dashboard View — Resumen general del ERP
 * Muestra estadísticas, gráfico de rentabilidad por marca y estado general
 */

const MARCAS = [
  { nombre: 'Superozono', porcentaje: 28, color: 'green' },
  { nombre: 'Ecoozono', porcentaje: 18, color: 'blue' },
  { nombre: 'Agroking', porcentaje: 15, color: 'amber' },
  { nombre: 'Ozono Evolution', porcentaje: 12, color: 'purple' },
  { nombre: 'Agro Vital', porcentaje: 9, color: 'cyan' },
  { nombre: 'Agro Fusion', porcentaje: 7, color: 'green' },
  { nombre: 'Hiper Ozono', porcentaje: 5, color: 'blue' },
  { nombre: 'Ozono Pro', porcentaje: 3, color: 'amber' },
  { nombre: 'Ozomax', porcentaje: 2, color: 'red' },
  { nombre: 'Biozono', porcentaje: 1, color: 'purple' },
]

const STATS = [
  { icon: '📋', label: 'Cuentas PUC', value: '34', color: 'green' },
  { icon: '🏷️', label: 'Centros de Costo', value: '12', color: 'blue' },
  { icon: '📅', label: 'Períodos 2026', value: '12', color: 'amber' },
  { icon: '🏛️', label: 'Params. Tributarios', value: '8', color: 'purple' },
  { icon: '💰', label: 'Params. Nómina', value: '15', color: 'cyan' },
  { icon: '👥', label: 'Terceros', value: '0', color: 'neutral' },
]

const PHASES = [
  { fase: 'Fase 1', desc: 'Setup, RBAC, Contabilidad, Ventas, Inventario', estado: 'En progreso', color: 'green' },
  { fase: 'Fase 2', desc: 'Finanzas, RRHH, Nómina, Alegra sandbox', estado: 'Pendiente', color: 'neutral' },
  { fase: 'Fase 3', desc: 'Mercado Libre, Devoluciones, Proveedores', estado: 'Pendiente', color: 'neutral' },
  { fase: 'Fase 4', desc: 'Reportes BI, Electron, Auditoría final', estado: 'Pendiente', color: 'neutral' },
]

export default function DashboardView() {
  return (
    <div>
      {/* ── Stats Grid ──────────────────────────────── */}
      <div className="stats-grid">
        {STATS.map((stat, i) => (
          <div
            key={stat.label}
            className={`stat-card fade-in fade-in-delay-${i + 1}`}
          >
            <div className="stat-card-header">
              <div className={`stat-card-icon ${stat.color}`}>{stat.icon}</div>
            </div>
            <div className="stat-card-value">{stat.value}</div>
            <div className="stat-card-label">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* ── Charts ──────────────────────────────────── */}
      <div className="charts-grid">
        {/* Rentabilidad por Marca */}
        <div className="chart-card fade-in">
          <div className="chart-card-title">
            📊 Rentabilidad por Marca (simulación)
          </div>
          <div className="bar-chart">
            {MARCAS.map((marca) => (
              <div className="bar-item" key={marca.nombre}>
                <div className="bar-label">{marca.nombre}</div>
                <div className="bar-track">
                  <div
                    className={`bar-fill ${marca.color}`}
                    style={{ width: `${marca.porcentaje * 3}%` }}
                  >
                    <span>{marca.porcentaje}%</span>
                  </div>
                </div>
                <div className="bar-value">
                  ${(marca.porcentaje * 420000).toLocaleString('es-CO')}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Plan de Desarrollo */}
        <div className="chart-card fade-in">
          <div className="chart-card-title">🗓️ Plan de Desarrollo por Fases</div>
          <div className="table-container" style={{ border: 'none' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Fase</th>
                  <th>Módulos</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {PHASES.map((p) => (
                  <tr key={p.fase}>
                    <td>
                      <strong style={{ color: 'var(--neutral-100)' }}>{p.fase}</strong>
                    </td>
                    <td>{p.desc}</td>
                    <td>
                      <span className={`badge ${p.color}`}>{p.estado}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Empresa Info */}
          <div style={{ marginTop: 20, padding: '16px', background: 'var(--neutral-850)', borderRadius: 'var(--radius-md)', border: '1px solid var(--neutral-800)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--neutral-500)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
              Empresa
            </div>
            <div style={{ fontSize: '0.9rem', color: 'var(--neutral-100)', fontWeight: 600, marginBottom: 4 }}>
              TECNOLOGÍA E INNOVACIÓN SUPER OZONO S.A.S.
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--neutral-400)' }}>
              NIT: 901841798-5 · Armenia, Quindío · Colombia
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--neutral-400)', marginTop: 2 }}>
              Sector: Agroindustria / Biocidas naturales con tecnología de ozono
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
