import { useState, useEffect } from 'react';
import { dashboardApi, type ContabilidadStats, type VentasStats } from '../services/dashboardApi';

const PHASES = [
  { fase: 'Fase 1', desc: 'Setup, RBAC, Contabilidad, Ventas, Inventario', estado: 'En progreso', color: 'green' },
  { fase: 'Fase 2', desc: 'Finanzas, RRHH, Nómina, Alegra sandbox', estado: 'Pendiente', color: 'neutral' },
  { fase: 'Fase 3', desc: 'Mercado Libre, Devoluciones, Proveedores', estado: 'Pendiente', color: 'neutral' },
  { fase: 'Fase 4', desc: 'Reportes BI, Electron, Auditoría final', estado: 'Pendiente', color: 'neutral' },
];

const MARCA_COLORS = ['green', 'blue', 'amber', 'purple', 'cyan', 'red', 'green', 'blue', 'amber', 'purple'];

function formatCOP(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(value);
}

function StatCard({ icon, label, value, color, delay }: {
  icon: string; label: string; value: string | number; color: string; delay: number;
}) {
  return (
    <div className={`stat-card fade-in fade-in-delay-${delay}`}>
      <div className="stat-card-header">
        <div className={`stat-card-icon ${color}`}>{icon}</div>
      </div>
      <div className="stat-card-value">{value}</div>
      <div className="stat-card-label">{label}</div>
    </div>
  );
}

export default function DashboardView() {
  const [contab, setContab] = useState<ContabilidadStats | null>(null);
  const [ventas, setVentas] = useState<VentasStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      dashboardApi.getContabilidadStats(),
      dashboardApi.getVentasStats(),
    ])
      .then(([c, v]) => { setContab(c); setVentas(v); })
      .catch(() => setError('No se pudo conectar con el servidor. Verifica que el backend esté corriendo.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="loading-screen" style={{ minHeight: 300 }}>
        <div className="loading-spinner" />
        <div className="loading-sub">Cargando estadísticas...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠️</div>
        <div className="empty-state-text">{error}</div>
      </div>
    );
  }

  const marcas = ventas?.ventas_por_marca ?? [];
  const maxMarcaTotal = Math.max(...marcas.map(m => m.total), 1);
  const hayVentasMarca = marcas.some(m => m.total > 0);

  const variacion = ventas && ventas.ventas_mes_anterior > 0
    ? (((ventas.ventas_mes_actual - ventas.ventas_mes_anterior) / ventas.ventas_mes_anterior) * 100).toFixed(1)
    : null;

  const mesActual = new Date().toLocaleString('es-CO', { month: 'long', year: 'numeric' });

  return (
    <div>
      {/* ── Sección Contabilidad ──────────────────────── */}
      <div style={{ fontSize: '0.7rem', color: 'var(--neutral-500)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
        Módulo Contabilidad
      </div>
      <div className="stats-grid">
        <StatCard icon="📋" label="Cuentas PUC" value={contab?.total_cuentas_puc ?? '—'} color="green" delay={1} />
        <StatCard icon="🏷️" label="Centros de Costo" value={contab?.total_centros_costo ?? '—'} color="blue" delay={2} />
        <StatCard icon="📅" label="Períodos 2026" value={contab?.total_periodos ?? '—'} color="amber" delay={3} />
        <StatCard icon="🏛️" label="Params. Tributarios" value={contab?.total_parametros_tributarios ?? '—'} color="purple" delay={4} />
        <StatCard icon="💰" label="Params. Nómina" value={contab?.total_parametros_nomina ?? '—'} color="cyan" delay={5} />
        <StatCard icon="👥" label="Terceros" value={contab?.total_terceros ?? '—'} color="neutral" delay={6} />
      </div>

      {/* ── Sección Ventas ───────────────────────────── */}
      <div style={{ fontSize: '0.7rem', color: 'var(--neutral-500)', textTransform: 'uppercase', letterSpacing: '0.08em', margin: '24px 0 10px' }}>
        Módulo Ventas — {mesActual}
      </div>
      <div className="stats-grid">
        <StatCard
          icon="💵"
          label={variacion ? `Ventas (${variacion}% vs mes ant.)` : 'Ventas del mes'}
          value={formatCOP(ventas?.ventas_mes_actual ?? 0)}
          color="green"
          delay={1}
        />
        <StatCard icon="🧾" label="Facturas del mes" value={ventas?.cantidad_ventas_mes ?? 0} color="blue" delay={2} />
        <StatCard icon="🏢" label="Clientes activos" value={ventas?.total_clientes_activos ?? 0} color="amber" delay={3} />
        <StatCard icon="📦" label="Productos activos" value={ventas?.total_productos_activos ?? 0} color="purple" delay={4} />
        <StatCard icon="🎯" label="Ticket promedio" value={formatCOP(ventas?.ticket_promedio ?? 0)} color="cyan" delay={5} />
        <StatCard
          icon="⚠️"
          label="Stock bajo"
          value={ventas?.productos_stock_bajo ?? 0}
          color={ventas && ventas.productos_stock_bajo > 0 ? 'red' : 'neutral'}
          delay={6}
        />
      </div>

      {/* ── Charts ──────────────────────────────────── */}
      <div className="charts-grid">
        {/* Ventas por Marca */}
        <div className="chart-card fade-in">
          <div className="chart-card-title">
            📊 Ventas por Marca — {mesActual}
          </div>
          {hayVentasMarca ? (
            <div className="bar-chart">
              {marcas.map((marca, i) => {
                const pct = Math.round((marca.total / maxMarcaTotal) * 100);
                return (
                  <div className="bar-item" key={marca.marca}>
                    <div className="bar-label">{marca.marca}</div>
                    <div className="bar-track">
                      <div
                        className={`bar-fill ${MARCA_COLORS[i % MARCA_COLORS.length]}`}
                        style={{ width: `${Math.max(pct * 3, 4)}%` }}
                      >
                        <span>{pct}%</span>
                      </div>
                    </div>
                    <div className="bar-value">{formatCOP(marca.total)}</div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty-state" style={{ minHeight: 180 }}>
              <div className="empty-state-icon">📭</div>
              <div className="empty-state-text">Sin ventas registradas este mes</div>
              <div className="empty-state-sub">Las ventas por marca aparecerán aquí al registrar facturas.</div>
            </div>
          )}
        </div>

        {/* Plan de Desarrollo + Empresa */}
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
                    <td><strong style={{ color: 'var(--neutral-100)' }}>{p.fase}</strong></td>
                    <td>{p.desc}</td>
                    <td><span className={`badge ${p.color}`}>{p.estado}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: 20, padding: '16px', background: 'var(--neutral-850)', borderRadius: 'var(--radius-md)', border: '1px solid var(--neutral-800)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--neutral-500)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
              Empresa
            </div>
            <div style={{ fontSize: '0.9rem', color: 'var(--neutral-100)', fontWeight: 600, marginBottom: 4 }}>
              {contab?.empresa_razon_social ?? 'TECNOLOGÍA E INNOVACIÓN SUPER OZONO S.A.S.'}
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--neutral-400)' }}>
              NIT: {contab?.empresa_nit ?? '901841798-5'} · Armenia, Quindío · Colombia
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--neutral-400)', marginTop: 2 }}>
              Sector: Agroindustria / Biocidas naturales con tecnología de ozono
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
