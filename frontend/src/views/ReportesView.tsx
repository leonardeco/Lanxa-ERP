import { useState, useEffect } from 'react';
import {
  reportesApi,
  type AgingCarteraResponse,
  type AgingReporte,
  type ComprasPeriodoResponse,
  type VentasPeriodoResponse,
  type RetencionesPeriodoResponse,
} from '../services/reportesApi';

type ReportesTab = 'aging' | 'periodo' | 'retenciones';

const COP = (n: number | string) =>
  Number(n).toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 0 });

const BUCKET_COLOR: Record<string, string> = {
  Corriente: '#22c55e',
  '1-30': '#3b82f6',
  '31-60': '#f59e0b',
  '61-90': '#f97316',
  '+90': '#ef4444',
};

const hoyISO = () => new Date().toISOString().slice(0, 10);
const primerDiaMesISO = () => {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
};

// ══════════════════════════════════════════════════════════
// AGING DE CARTERA
// ══════════════════════════════════════════════════════════

function AgingTabla({ titulo, reporte }: { titulo: string; reporte: AgingReporte }) {
  return (
    <div className="fade-in" style={{ marginBottom: 32 }}>
      <h3 style={{ marginBottom: 12 }}>{titulo} — Total pendiente: {COP(reporte.total_pendiente)}</h3>
      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 16 }}>
        {reporte.buckets.map(b => (
          <div className="kpi-card" key={b.bucket}>
            <div className="kpi-label" style={{ color: BUCKET_COLOR[b.bucket] }}>{b.bucket}</div>
            <div className="kpi-value">{COP(b.total)}</div>
            <div className="kpi-change">{b.cantidad} documento{b.cantidad === 1 ? '' : 's'}</div>
          </div>
        ))}
      </div>
      <div className="table-card">
        <table className="erp-table">
          <thead>
            <tr>
              <th>Número</th>
              <th>Tercero</th>
              <th>NIT</th>
              <th style={{ textAlign: 'right' }}>Saldo</th>
              <th style={{ textAlign: 'right' }}>Días vencido</th>
              <th>Bucket</th>
            </tr>
          </thead>
          <tbody>
            {reporte.detalle.length === 0 ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', color: '#888', padding: 24 }}>Sin documentos pendientes</td></tr>
            ) : reporte.detalle.map(d => (
              <tr key={d.id}>
                <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{d.numero}</td>
                <td>{d.tercero}</td>
                <td style={{ fontSize: 11, color: '#666' }}>{d.nit}</td>
                <td style={{ textAlign: 'right', fontWeight: 600 }}>{COP(d.saldo_pendiente)}</td>
                <td style={{ textAlign: 'right' }}>{d.dias_vencido > 0 ? d.dias_vencido : '—'}</td>
                <td><span className="badge" style={{ background: '#f0f4ff', color: BUCKET_COLOR[d.bucket] ?? '#555' }}>{d.bucket}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AgingTab() {
  const [data, setData] = useState<AgingCarteraResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    reportesApi.getAgingCartera().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-spinner" style={{ margin: '60px auto' }} />;
  if (!data) return <div className="empty-state"><div className="empty-state-text">Error cargando el reporte</div></div>;

  return (
    <div className="fade-in">
      <AgingTabla titulo="Cuentas por Cobrar (CxC)" reporte={data.cxc} />
      <AgingTabla titulo="Cuentas por Pagar (CxP)" reporte={data.cxp} />
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// COMPRAS Y VENTAS POR PERÍODO
// ══════════════════════════════════════════════════════════

function PeriodoTab() {
  const [fechaDesde, setFechaDesde] = useState(primerDiaMesISO());
  const [fechaHasta, setFechaHasta] = useState(hoyISO());
  const [compras, setCompras] = useState<ComprasPeriodoResponse | null>(null);
  const [ventas, setVentas] = useState<VentasPeriodoResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const cargar = () => {
    setLoading(true);
    Promise.all([
      reportesApi.getComprasPeriodo(fechaDesde, fechaHasta),
      reportesApi.getVentasPeriodo(fechaDesde, fechaHasta),
    ]).then(([c, v]) => { setCompras(c); setVentas(v); }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { cargar(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="fade-in">
      <div className="table-card" style={{ marginBottom: 20, padding: 16, display: 'flex', gap: 12, alignItems: 'flex-end' }}>
        <div className="form-group" style={{ margin: 0 }}>
          <label>Desde</label>
          <input className="form-input" type="date" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} />
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label>Hasta</label>
          <input className="form-input" type="date" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} />
        </div>
        <button className="btn-primary" onClick={cargar} disabled={loading}>{loading ? 'Cargando...' : 'Aplicar'}</button>
      </div>

      {loading ? <div className="loading-spinner" style={{ margin: '60px auto' }} /> : (
        <>
          {compras && (
            <div style={{ marginBottom: 32 }}>
              <h3 style={{ marginBottom: 12 }}>Compras del período</h3>
              <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 16 }}>
                <div className="kpi-card">
                  <div className="kpi-label">Total comprado</div>
                  <div className="kpi-value">{COP(compras.total)}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Documentos</div>
                  <div className="kpi-value">{compras.cantidad_documentos}</div>
                </div>
              </div>
              <div className="table-card">
                <div className="table-card-header"><h3>Por proveedor</h3></div>
                <table className="erp-table">
                  <thead><tr><th>Proveedor</th><th style={{ textAlign: 'right' }}>Documentos</th><th style={{ textAlign: 'right' }}>Total</th></tr></thead>
                  <tbody>
                    {compras.por_proveedor.length === 0 ? (
                      <tr><td colSpan={3} style={{ textAlign: 'center', color: '#888', padding: 24 }}>Sin compras en el período</td></tr>
                    ) : compras.por_proveedor.map((p, i) => (
                      <tr key={i}>
                        <td>{p.nombre}</td>
                        <td style={{ textAlign: 'right' }}>{p.cantidad}</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }}>{COP(p.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {ventas && (
            <div>
              <h3 style={{ marginBottom: 12 }}>Ventas del período</h3>
              <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 16 }}>
                <div className="kpi-card">
                  <div className="kpi-label">Total vendido</div>
                  <div className="kpi-value">{COP(ventas.total)}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Documentos</div>
                  <div className="kpi-value">{ventas.cantidad_documentos}</div>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div className="table-card">
                  <div className="table-card-header"><h3>Por cliente</h3></div>
                  <table className="erp-table">
                    <thead><tr><th>Cliente</th><th style={{ textAlign: 'right' }}>Doc.</th><th style={{ textAlign: 'right' }}>Total</th></tr></thead>
                    <tbody>
                      {ventas.por_cliente.length === 0 ? (
                        <tr><td colSpan={3} style={{ textAlign: 'center', color: '#888', padding: 24 }}>Sin ventas</td></tr>
                      ) : ventas.por_cliente.map((c, i) => (
                        <tr key={i}>
                          <td>{c.nombre}</td>
                          <td style={{ textAlign: 'right' }}>{c.cantidad}</td>
                          <td style={{ textAlign: 'right', fontWeight: 600 }}>{COP(c.total)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="table-card">
                  <div className="table-card-header"><h3>Por marca</h3></div>
                  <table className="erp-table">
                    <thead><tr><th>Marca</th><th style={{ textAlign: 'right' }}>Líneas</th><th style={{ textAlign: 'right' }}>Total</th></tr></thead>
                    <tbody>
                      {ventas.por_marca.length === 0 ? (
                        <tr><td colSpan={3} style={{ textAlign: 'center', color: '#888', padding: 24 }}>Sin ventas</td></tr>
                      ) : ventas.por_marca.map((m, i) => (
                        <tr key={i}>
                          <td>{m.nombre}</td>
                          <td style={{ textAlign: 'right' }}>{m.cantidad}</td>
                          <td style={{ textAlign: 'right', fontWeight: 600 }}>{COP(m.total)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// RETENCIONES ACUMULADAS
// ══════════════════════════════════════════════════════════

function RetencionesTab() {
  const [fechaDesde, setFechaDesde] = useState(primerDiaMesISO());
  const [fechaHasta, setFechaHasta] = useState(hoyISO());
  const [data, setData] = useState<RetencionesPeriodoResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const cargar = () => {
    setLoading(true);
    reportesApi.getRetencionesPeriodo(fechaDesde, fechaHasta).then(setData).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { cargar(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="fade-in">
      <div className="table-card" style={{ marginBottom: 20, padding: 16, display: 'flex', gap: 12, alignItems: 'flex-end' }}>
        <div className="form-group" style={{ margin: 0 }}>
          <label>Desde</label>
          <input className="form-input" type="date" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} />
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label>Hasta</label>
          <input className="form-input" type="date" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} />
        </div>
        <button className="btn-primary" onClick={cargar} disabled={loading}>{loading ? 'Cargando...' : 'Aplicar'}</button>
      </div>

      {loading ? <div className="loading-spinner" style={{ margin: '60px auto' }} /> : data && (
        <>
          <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 20 }}>
            <div className="kpi-card">
              <div className="kpi-label">ReteFuente total</div>
              <div className="kpi-value">{COP(data.total_retefuente)}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">ReteIVA total</div>
              <div className="kpi-value">{COP(data.total_reteiva)}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">ReteICA total</div>
              <div className="kpi-value">{COP(data.total_reteica)}</div>
            </div>
          </div>
          <div className="table-card">
            <div className="table-card-header"><h3>Detalle por origen</h3></div>
            <table className="erp-table">
              <thead>
                <tr><th>Origen</th><th style={{ textAlign: 'right' }}>ReteFuente</th><th style={{ textAlign: 'right' }}>ReteIVA</th><th style={{ textAlign: 'right' }}>ReteICA</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td>Compras</td>
                  <td style={{ textAlign: 'right' }}>{COP(data.compras_retefuente)}</td>
                  <td style={{ textAlign: 'right' }}>{COP(data.compras_reteiva)}</td>
                  <td style={{ textAlign: 'right' }}>{COP(data.compras_reteica)}</td>
                </tr>
                <tr>
                  <td>Ventas</td>
                  <td style={{ textAlign: 'right' }}>{COP(data.ventas_retefuente)}</td>
                  <td style={{ textAlign: 'right' }}>{COP(data.ventas_reteiva)}</td>
                  <td style={{ textAlign: 'right' }}>{COP(data.ventas_reteica)}</td>
                </tr>
                <tr style={{ fontWeight: 700, background: '#f0f4ff' }}>
                  <td>Total</td>
                  <td style={{ textAlign: 'right' }}>{COP(data.total_retefuente)}</td>
                  <td style={{ textAlign: 'right' }}>{COP(data.total_reteiva)}</td>
                  <td style={{ textAlign: 'right' }}>{COP(data.total_reteica)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════

export default function ReportesView() {
  const [tab, setTab] = useState<ReportesTab>('aging');

  const TABS: { id: ReportesTab; label: string }[] = [
    { id: 'aging', label: '⏰ Aging de Cartera' },
    { id: 'periodo', label: '📦 Compras y Ventas por Período' },
    { id: 'retenciones', label: '🧾 Retenciones Acumuladas' },
  ];

  return (
    <div>
      <div className="tabs-bar" style={{ marginBottom: 20 }}>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`tab-btn ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'aging' && <AgingTab />}
      {tab === 'periodo' && <PeriodoTab />}
      {tab === 'retenciones' && <RetencionesTab />}
    </div>
  );
}
