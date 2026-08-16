import { useState, useEffect } from 'react';
import { dashboardApi, type ContabilidadStats } from '../services/dashboardApi';
import { ventasDiariasApi, type ResumenGlobal } from '../services/ventasDiariasApi';
import Skeleton from '../components/Skeleton';

const MESES_LABEL = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
const PAIS_BANDERA: Record<string, string> = { Colombia: '🇨🇴', Perú: '🇵🇪', Ecuador: '🇪🇨' };
const PAIS_COLOR: Record<string, string> = {
  Colombia: 'var(--oz-green-400)',
  Perú: '#f59e0b',
  Ecuador: '#60a5fa',
};

function fmt(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(value);
}

type MesPais = { mes: number; pais: string; tenant_id: number; total_venta: string; total_abonado: string; total_saldo: string; cantidad_ventas: number };

export default function DashboardView() {
  const [contab, setContab] = useState<ContabilidadStats | null>(null);
  const [resumenGlobal, setResumenGlobal] = useState<ResumenGlobal | null>(null);
  const [tendencia, setTendencia] = useState<MesPais[]>([]);
  const [anioGlobal, setAnioGlobal] = useState(new Date().getFullYear());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    dashboardApi.getContabilidadStats()
      .then(c => setContab(c))
      .catch(() => {});

    Promise.all([
      ventasDiariasApi.resumenGlobal(anioGlobal),
      ventasDiariasApi.tendencia(anioGlobal),
    ])
      .then(([g, t]) => {
        setResumenGlobal(g.data);
        setTendencia(t.data.meses);
      })
      .catch(() => setError('No se pudo cargar el resumen global. Verifica que el backend esté corriendo.'))
      .finally(() => setLoading(false));
  }, [anioGlobal]);

  const cambiarAnio = (a: number) => {
    setAnioGlobal(a);
  };

  if (loading) {
    return (
      <div aria-busy="true">
        <Skeleton variant="text" width={200} style={{ marginBottom: 16 }} />
        <div className="stats-grid"><Skeleton variant="card" count={3} /></div>
        <Skeleton variant="text" width={160} style={{ margin: '24px 0 10px' }} />
        <div className="charts-grid"><div className="chart-card"><Skeleton variant="row" count={7} /></div></div>
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

  // Calcular tendencia por mes (suma todos los países)
  const mesesConDatos = Array.from(new Set(tendencia.map(t => t.mes))).sort((a, b) => a - b);
  const maxVenta = Math.max(...mesesConDatos.map(m =>
    tendencia.filter(t => t.mes === m).reduce((s, t) => s + Number(t.total_venta), 0)
  ), 1);

  const paises = resumenGlobal?.paises ?? [];
  const totalVentaGlobal = Number(resumenGlobal?.total_venta_global ?? 0);
  const totalSaldoGlobal = Number(resumenGlobal?.total_saldo_global ?? 0);
  const totalAbonadoGlobal = Number(resumenGlobal?.total_abonado_global ?? 0);
  const totalGuias = paises.reduce((s, p) => s + p.cantidad_ventas, 0);
  const totalEntregados = paises.reduce((s, p) => s + p.cantidad_entregado, 0);
  const totalDevoluciones = paises.reduce((s, p) => s + p.cantidad_devolucion, 0);
  const pctCobrado = totalVentaGlobal > 0 ? Math.round((totalAbonadoGlobal / totalVentaGlobal) * 100) : 0;

  return (
    <div>
      {/* ── Header selector de año ─── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--neutral-100)' }}>
            📊 Resumen Global Lanxa
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--neutral-400)', marginTop: 2 }}>
            Consolidado de Colombia, Perú y Ecuador — ventas diarias
          </div>
        </div>
        <div style={{ display: 'flex', gap: 4, background: 'rgba(0,0,0,0.3)', borderRadius: 8, padding: 4 }}>
          {[2024, 2025, 2026].map(a => (
            <button key={a} onClick={() => cambiarAnio(a)} style={{
              padding: '5px 14px', borderRadius: 6, border: 'none', cursor: 'pointer',
              fontSize: '0.82rem', fontWeight: 700, fontFamily: 'inherit',
              background: anioGlobal === a ? 'var(--oz-green-600)' : 'transparent',
              color: anioGlobal === a ? 'white' : 'var(--neutral-400)',
              transition: 'all 150ms',
            }}>{a}</button>
          ))}
        </div>
      </div>

      {/* ── KPIs Globales ─── */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 8 }}>
        <div className="stat-card fade-in">
          <div className="stat-card-header"><div className="stat-card-icon green">💵</div></div>
          <div className="stat-card-value">{fmt(totalVentaGlobal)}</div>
          <div className="stat-card-label">Venta total {anioGlobal}</div>
        </div>
        <div className="stat-card fade-in fade-in-delay-1">
          <div className="stat-card-header"><div className="stat-card-icon blue">✅</div></div>
          <div className="stat-card-value">{fmt(totalAbonadoGlobal)}</div>
          <div className="stat-card-label">Recaudado ({pctCobrado}%)</div>
        </div>
        <div className="stat-card fade-in fade-in-delay-2">
          <div className="stat-card-header"><div className="stat-card-icon amber">⏳</div></div>
          <div className="stat-card-value" style={{ color: totalSaldoGlobal > 0 ? 'var(--amber-400)' : undefined }}>
            {fmt(totalSaldoGlobal)}
          </div>
          <div className="stat-card-label">Saldo por cobrar</div>
        </div>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 24 }}>
        <div className="stat-card fade-in">
          <div className="stat-card-header"><div className="stat-card-icon purple">📦</div></div>
          <div className="stat-card-value">{totalGuias.toLocaleString()}</div>
          <div className="stat-card-label">Guías registradas</div>
        </div>
        <div className="stat-card fade-in fade-in-delay-1">
          <div className="stat-card-header"><div className="stat-card-icon green">🚚</div></div>
          <div className="stat-card-value" style={{ color: 'var(--oz-green-400)' }}>{totalEntregados.toLocaleString()}</div>
          <div className="stat-card-label">Entregados</div>
        </div>
        <div className="stat-card fade-in fade-in-delay-2">
          <div className="stat-card-header"><div className="stat-card-icon red">↩</div></div>
          <div className="stat-card-value" style={{ color: 'var(--red-400)' }}>{totalDevoluciones.toLocaleString()}</div>
          <div className="stat-card-label">Devoluciones</div>
        </div>
      </div>

      {/* ── Por País ─── */}
      <div className="section-label" style={{ marginBottom: 12 }}>Por País</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 24 }}>
        {paises.map(p => {
          const pct = Number(p.total_venta) > 0 ? Math.round((Number(p.total_abonado) / Number(p.total_venta)) * 100) : 0;
          return (
            <div key={p.tenant_id} className="chart-card fade-in" style={{ padding: '18px 20px' }}>
              <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: 14, color: PAIS_COLOR[p.pais] }}>
                {PAIS_BANDERA[p.pais]} {p.pais}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--neutral-400)', textTransform: 'uppercase', letterSpacing:'0.05em' }}>Venta</div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--neutral-100)' }}>{fmt(Number(p.total_venta))}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--neutral-400)', textTransform: 'uppercase', letterSpacing:'0.05em' }}>Saldo</div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: Number(p.total_saldo) > 0 ? 'var(--amber-400)' : 'var(--neutral-400)' }}>{fmt(Number(p.total_saldo))}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--neutral-400)', textTransform: 'uppercase', letterSpacing:'0.05em' }}>Guías</div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--neutral-100)' }}>{p.cantidad_ventas}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--neutral-400)', textTransform: 'uppercase', letterSpacing:'0.05em' }}>% Cobrado</div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: pct >= 80 ? 'var(--oz-green-400)' : pct >= 50 ? 'var(--amber-400)' : 'var(--red-400)' }}>{pct}%</div>
                </div>
              </div>
              {/* Barra de progreso cobro */}
              <div style={{ marginTop: 14, height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3 }}>
                <div style={{ height: '100%', width: `${pct}%`, background: PAIS_COLOR[p.pais], borderRadius: 3, transition: 'width 0.6s ease' }} />
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--neutral-500)', marginTop: 4 }}>
                {fmt(Number(p.total_abonado))} recaudados de {fmt(Number(p.total_venta))}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Tendencia mensual ─── */}
      {mesesConDatos.length > 0 && (
        <>
          <div className="section-label" style={{ marginBottom: 12 }}>Tendencia Mensual {anioGlobal}</div>
          <div className="chart-card fade-in" style={{ marginBottom: 24 }}>
            <div className="bar-chart">
              {mesesConDatos.map(m => {
                const filasPais = tendencia.filter(t => t.mes === m);
                const totalMes = filasPais.reduce((s, t) => s + Number(t.total_venta), 0);
                const pct = Math.round((totalMes / maxVenta) * 100);
                return (
                  <div className="bar-item" key={m}>
                    <div className="bar-label">{MESES_LABEL[m - 1]}</div>
                    <div className="bar-track" style={{ flex: 1, position: 'relative' }}>
                      <div style={{ display: 'flex', height: 20, borderRadius: 4, overflow: 'hidden', width: `${Math.max(pct * 3, 4)}%` }}>
                        {filasPais.map(fp => {
                          const fpPct = totalMes > 0 ? (Number(fp.total_venta) / totalMes) * 100 : 0;
                          return (
                            <div key={fp.pais} title={`${fp.pais}: ${fmt(Number(fp.total_venta))}`}
                              style={{ width: `${fpPct}%`, background: PAIS_COLOR[fp.pais], minWidth: fpPct > 0 ? 4 : 0 }} />
                          );
                        })}
                      </div>
                    </div>
                    <div className="bar-value">{fmt(totalMes)}</div>
                  </div>
                );
              })}
            </div>
            {/* Leyenda */}
            <div style={{ display: 'flex', gap: 20, marginTop: 12, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
              {Object.entries(PAIS_BANDERA).map(([pais, bandera]) => (
                <div key={pais} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', color: 'var(--neutral-400)' }}>
                  <div style={{ width: 10, height: 10, borderRadius: 2, background: PAIS_COLOR[pais] }} />
                  {bandera} {pais}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* ── Tabla de análisis mensual ─── */}
      {mesesConDatos.length > 0 && (
        <>
          <div className="section-label" style={{ marginBottom: 12 }}>Análisis Detallado por Mes</div>
          <div className="table-container" style={{ marginBottom: 24 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Mes</th>
                  <th>País</th>
                  <th style={{ textAlign: 'right' }}>Guías</th>
                  <th style={{ textAlign: 'right' }}>Venta</th>
                  <th style={{ textAlign: 'right' }}>Recaudado</th>
                  <th style={{ textAlign: 'right' }}>Saldo</th>
                  <th style={{ textAlign: 'right' }}>% Cobro</th>
                </tr>
              </thead>
              <tbody>
                {mesesConDatos.flatMap(m =>
                  tendencia.filter(t => t.mes === m).map(t => {
                    const pct = Number(t.total_venta) > 0 ? Math.round((Number(t.total_abonado) / Number(t.total_venta)) * 100) : 0;
                    return (
                      <tr key={`${m}-${t.pais}`}>
                        <td style={{ fontWeight: 600 }}>{MESES_LABEL[m - 1]}</td>
                        <td>{PAIS_BANDERA[t.pais]} {t.pais}</td>
                        <td style={{ textAlign: 'right' }}>{t.cantidad_ventas}</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }}>{fmt(Number(t.total_venta))}</td>
                        <td style={{ textAlign: 'right', color: 'var(--oz-green-400)' }}>{fmt(Number(t.total_abonado))}</td>
                        <td style={{ textAlign: 'right', color: Number(t.total_saldo) > 0 ? 'var(--amber-400)' : 'var(--neutral-400)' }}>{fmt(Number(t.total_saldo))}</td>
                        <td style={{ textAlign: 'right' }}>
                          <span style={{ color: pct >= 80 ? 'var(--oz-green-400)' : pct >= 50 ? 'var(--amber-400)' : 'var(--red-400)', fontWeight: 700 }}>{pct}%</span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ── Contabilidad Colombia ─── */}
      {contab && (
        <>
          <div className="section-label" style={{ marginBottom: 12 }}>Sistema — Colombia</div>
          <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
            <div className="stat-card fade-in">
              <div className="stat-card-header"><div className="stat-card-icon green">📋</div></div>
              <div className="stat-card-value">{contab.total_cuentas_puc}</div>
              <div className="stat-card-label">Cuentas PUC</div>
            </div>
            <div className="stat-card fade-in fade-in-delay-1">
              <div className="stat-card-header"><div className="stat-card-icon blue">🏷️</div></div>
              <div className="stat-card-value">{contab.total_centros_costo}</div>
              <div className="stat-card-label">Centros de Costo</div>
            </div>
            <div className="stat-card fade-in fade-in-delay-2">
              <div className="stat-card-header"><div className="stat-card-icon amber">📅</div></div>
              <div className="stat-card-value">{contab.total_periodos}</div>
              <div className="stat-card-label">Períodos {new Date().getFullYear()}</div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
