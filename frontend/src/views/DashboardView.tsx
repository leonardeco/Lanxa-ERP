import { useState, useEffect } from 'react';
import { dashboardApi, type ContabilidadStats, type VentasStats } from '../services/dashboardApi';
import { reportesApi, type AgingCarteraResponse, type AgingDetalle } from '../services/reportesApi';
import Skeleton from '../components/Skeleton';

interface AlertaVencimiento extends AgingDetalle {
  tipo: 'CxC' | 'CxP';
  diasParaVencer: number | null; // null si ya está vencido
}

/** Vencidos + los que vencen en los próximos 7 días, ordenados por urgencia. */
function calcularAlertas(aging: AgingCarteraResponse): AlertaVencimiento[] {
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);

  const procesar = (detalle: AgingDetalle[], tipo: 'CxC' | 'CxP'): AlertaVencimiento[] =>
    detalle.flatMap((d): AlertaVencimiento[] => {
      if (d.dias_vencido > 0) return [{ ...d, tipo, diasParaVencer: null }];
      if (!d.fecha_vencimiento) return [];
      const dias = Math.ceil((new Date(d.fecha_vencimiento).getTime() - hoy.getTime()) / 86400000);
      return dias >= 0 && dias <= 7 ? [{ ...d, tipo, diasParaVencer: dias }] : [];
    });

  return [...procesar(aging.cxc.detalle, 'CxC'), ...procesar(aging.cxp.detalle, 'CxP')]
    .sort((a, b) => (b.dias_vencido - a.dias_vencido) || ((a.diasParaVencer ?? 99) - (b.diasParaVencer ?? 99)));
}

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
  const [alertas, setAlertas] = useState<AlertaVencimiento[]>([]);
  const [morosos, setMorosos] = useState<AgingDetalle[]>([]);
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

    // Las alertas cargan aparte: si fallan, el dashboard sigue funcionando
    reportesApi.getAgingCartera()
      .then(aging => {
        setAlertas(calcularAlertas(aging));
        // KPI de negocio: top 5 clientes morosos por saldo vencido
        setMorosos(
          [...aging.cxc.detalle]
            .filter(d => d.dias_vencido > 0)
            .sort((a, b) => b.saldo_pendiente - a.saldo_pendiente)
            .slice(0, 5)
        );
      })
      .catch(() => {});
  }, []);

  if (loading) {
    return (
      <div aria-busy="true" aria-label="Cargando estadísticas">
        <Skeleton variant="text" width={140} style={{ marginBottom: 10 }} />
        <div className="stats-grid">
          <Skeleton variant="card" count={6} />
        </div>
        <Skeleton variant="text" width={200} style={{ margin: '24px 0 10px' }} />
        <div className="stats-grid">
          <Skeleton variant="card" count={6} />
        </div>
        <div className="charts-grid">
          <div className="chart-card"><Skeleton variant="row" count={6} /></div>
          <div className="chart-card"><Skeleton variant="row" count={6} /></div>
        </div>
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
      {/* ── Alertas de vencimiento de cartera ────────── */}
      {alertas.length > 0 && (
        <div className="chart-card fade-in" style={{ marginBottom: 24, borderLeft: '3px solid #f59e0b' }}>
          <div className="chart-card-title">
            🔔 Alertas de cartera — {alertas.filter(a => a.diasParaVencer === null).length} vencida(s),{' '}
            {alertas.filter(a => a.diasParaVencer !== null).length} por vencer esta semana
          </div>
          <div className="table-container" style={{ border: 'none' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Tipo</th><th>Documento</th><th>Tercero</th>
                  <th style={{ textAlign: 'right' }}>Saldo</th><th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {alertas.slice(0, 8).map(a => (
                  <tr key={`${a.tipo}-${a.id}`}>
                    <td>
                      <span className={`badge ${a.tipo === 'CxC' ? 'green' : 'amber'}`}>{a.tipo}</span>
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{a.numero}</td>
                    <td>{a.tercero}</td>
                    <td style={{ textAlign: 'right', fontWeight: 600 }}>{formatCOP(a.saldo_pendiente)}</td>
                    <td>
                      {a.diasParaVencer === null ? (
                        <span className="badge red">Vencida hace {a.dias_vencido} día{a.dias_vencido === 1 ? '' : 's'}</span>
                      ) : a.diasParaVencer === 0 ? (
                        <span className="badge amber">Vence HOY</span>
                      ) : (
                        <span className="badge amber">Vence en {a.diasParaVencer} día{a.diasParaVencer === 1 ? '' : 's'}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {alertas.length > 8 && (
              <div style={{ padding: '8px 12px', fontSize: '0.78rem', color: 'var(--neutral-400)' }}>
                … y {alertas.length - 8} más — ver el detalle completo en Reportes → Aging de Cartera
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Sección Contabilidad ──────────────────────── */}
      <div className="section-label">
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
      <div className="section-label" style={{ marginTop: 24 }}>
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

        {/* Top morosos + Empresa */}
        <div className="chart-card fade-in">
          <div className="chart-card-title">🔴 Top Clientes Morosos (cartera vencida)</div>
          {morosos.length === 0 ? (
            <div className="empty-state" style={{ minHeight: 140 }}>
              <div className="empty-state-icon">🎉</div>
              <div className="empty-state-text">Sin cartera vencida</div>
              <div className="empty-state-sub">Ningún cliente tiene facturas vencidas por cobrar.</div>
            </div>
          ) : (
            <div className="table-container" style={{ border: 'none' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th>Factura</th>
                    <th style={{ textAlign: 'right' }}>Saldo vencido</th>
                    <th style={{ textAlign: 'right' }}>Días</th>
                  </tr>
                </thead>
                <tbody>
                  {morosos.map(m => (
                    <tr key={m.id}>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--neutral-100)' }}>{m.tercero}</div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--neutral-500)' }}>{m.nit}</div>
                      </td>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.78rem' }}>{m.numero}</td>
                      <td style={{ textAlign: 'right', fontWeight: 700, color: 'var(--red-400)' }}>
                        {formatCOP(m.saldo_pendiente)}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <span className="badge red">{m.dias_vencido}d</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div style={{ marginTop: 20, padding: '16px', background: 'var(--neutral-850)', borderRadius: 'var(--radius-md)', border: '1px solid var(--neutral-800)' }}>
            <div className="section-label" style={{ marginBottom: 8 }}>
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
