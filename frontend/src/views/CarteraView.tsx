import { useState, useEffect, useCallback } from 'react';
import { carteraApi, type CxC, type CxP, type CarteraStats } from '../services/carteraApi';

// ── Helpers ──────────────────────────────────────────────

function formatCOP(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v);
}

function rowColor(dias: number, estado: string): string {
  if (estado === 'Pagado') return 'var(--neutral-800)';
  if (estado === 'Anulado') return 'var(--neutral-900)';
  if (dias > 30) return 'rgba(239,68,68,0.07)';
  if (dias > 0) return 'rgba(251,191,36,0.07)';
  return 'transparent';
}

function estadoBadge(estado: string, dias: number) {
  if (estado === 'Pagado') return <span className="badge green">Pagado</span>;
  if (estado === 'Anulado') return <span className="badge neutral">Anulado</span>;
  if (estado === 'Parcial') return <span className="badge blue">Parcial</span>;
  if (dias > 0) return <span className="badge red">Vencida {dias}d</span>;
  return <span className="badge amber">Pendiente</span>;
}

// ── Toast ────────────────────────────────────────────────

function Toast({ message, type, onClose }: { message: string; type: 'success' | 'error'; onClose: () => void }) {
  useEffect(() => { const t = setTimeout(onClose, 3500); return () => clearTimeout(t); }, [onClose]);
  return (
    <div className={`toast toast-${type} fade-in`}>
      <span>{type === 'success' ? '✅' : '❌'}</span>
      <span>{message}</span>
      <button className="toast-close" onClick={onClose}>×</button>
    </div>
  );
}

// ── Modal ────────────────────────────────────────────────

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal-card fade-in">
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

// ── Modal Abono ───────────────────────────────────────────

function AbonoModal({ saldo, onAbono, onClose }: {
  saldo: number; onAbono: (valor: number, notas: string) => Promise<void>; onClose: () => void;
}) {
  const [valor, setValor] = useState('');
  const [notas, setNotas] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const n = parseFloat(valor);
    if (!n || n <= 0) return setError('Ingresa un valor válido');
    if (n > saldo) return setError(`El valor supera el saldo pendiente (${formatCOP(saldo)})`);
    setSaving(true);
    try { await onAbono(n, notas); }
    catch (err: any) { setError(err?.response?.data?.detail ?? 'Error al registrar abono'); }
    finally { setSaving(false); }
  };

  return (
    <Modal title="Registrar abono" onClose={onClose}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ padding: '10px 14px', background: 'var(--neutral-850)', borderRadius: 8, fontSize: '0.85rem', color: 'var(--neutral-300)' }}>
          Saldo pendiente: <strong style={{ color: 'var(--neutral-100)' }}>{formatCOP(saldo)}</strong>
        </div>
        <div className="form-group">
          <label className="form-label">Valor del abono *</label>
          <input className="form-input" type="number" step="0.01" min="1" value={valor}
            onChange={e => setValor(e.target.value)} placeholder="0.00" required />
        </div>
        <div className="form-group">
          <label className="form-label">Notas (opcional)</label>
          <input className="form-input" type="text" value={notas} onChange={e => setNotas(e.target.value)} placeholder="Referencia de pago, banco, etc." />
        </div>
        {error && <div className="form-error">{error}</div>}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>Cancelar</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Guardando...' : 'Registrar abono'}</button>
        </div>
      </form>
    </Modal>
  );
}

// ── Modal Crear CxC ───────────────────────────────────────

function CxCFormModal({ onSave, onClose }: { onSave: (d: any) => Promise<void>; onClose: () => void }) {
  const [form, setForm] = useState({ numero_factura: '', fecha_emision: new Date().toISOString().slice(0, 10), cliente_nit: '', nombre_cliente: '', marca: '', valor_factura: '', fecha_vencimiento: '', notas: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    if (!form.valor_factura || parseFloat(form.valor_factura) <= 0) return setError('Ingresa un valor válido');
    setSaving(true);
    try {
      await onSave({ ...form, valor_factura: parseFloat(form.valor_factura), marca: form.marca || undefined, fecha_vencimiento: form.fecha_vencimiento || undefined, notas: form.notas || undefined });
    } catch (err: any) { setError(err?.response?.data?.detail ?? 'Error al guardar'); }
    finally { setSaving(false); }
  };

  return (
    <Modal title="Nueva Cuenta por Cobrar" onClose={onClose}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div className="form-group"><label className="form-label">N° Factura *</label><input className="form-input" value={form.numero_factura} onChange={e => set('numero_factura', e.target.value)} required /></div>
          <div className="form-group"><label className="form-label">Fecha emisión *</label><input className="form-input" type="date" value={form.fecha_emision} onChange={e => set('fecha_emision', e.target.value)} required /></div>
          <div className="form-group"><label className="form-label">NIT Cliente *</label><input className="form-input" value={form.cliente_nit} onChange={e => set('cliente_nit', e.target.value)} required /></div>
          <div className="form-group"><label className="form-label">Nombre Cliente *</label><input className="form-input" value={form.nombre_cliente} onChange={e => set('nombre_cliente', e.target.value)} required /></div>
          <div className="form-group"><label className="form-label">Marca</label><input className="form-input" value={form.marca} onChange={e => set('marca', e.target.value)} placeholder="Superozono, Ecoozono..." /></div>
          <div className="form-group"><label className="form-label">Valor factura *</label><input className="form-input" type="number" step="0.01" value={form.valor_factura} onChange={e => set('valor_factura', e.target.value)} required /></div>
          <div className="form-group"><label className="form-label">Fecha vencimiento</label><input className="form-input" type="date" value={form.fecha_vencimiento} onChange={e => set('fecha_vencimiento', e.target.value)} /></div>
        </div>
        <div className="form-group"><label className="form-label">Notas</label><input className="form-input" value={form.notas} onChange={e => set('notas', e.target.value)} /></div>
        {error && <div className="form-error">{error}</div>}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>Cancelar</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Guardando...' : 'Crear CxC'}</button>
        </div>
      </form>
    </Modal>
  );
}

// ── Modal Crear CxP ───────────────────────────────────────

function CxPFormModal({ onSave, onClose }: { onSave: (d: any) => Promise<void>; onClose: () => void }) {
  const [form, setForm] = useState({ numero_documento: '', fecha: new Date().toISOString().slice(0, 10), proveedor_nit: '', razon_social: '', concepto: '', valor: '', fecha_vencimiento: '', notas: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    if (!form.valor || parseFloat(form.valor) <= 0) return setError('Ingresa un valor válido');
    setSaving(true);
    try {
      await onSave({ ...form, valor: parseFloat(form.valor), concepto: form.concepto || undefined, fecha_vencimiento: form.fecha_vencimiento || undefined, notas: form.notas || undefined });
    } catch (err: any) { setError(err?.response?.data?.detail ?? 'Error al guardar'); }
    finally { setSaving(false); }
  };

  return (
    <Modal title="Nueva Cuenta por Pagar" onClose={onClose}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div className="form-group"><label className="form-label">N° Documento *</label><input className="form-input" value={form.numero_documento} onChange={e => set('numero_documento', e.target.value)} required /></div>
          <div className="form-group"><label className="form-label">Fecha *</label><input className="form-input" type="date" value={form.fecha} onChange={e => set('fecha', e.target.value)} required /></div>
          <div className="form-group"><label className="form-label">NIT Proveedor *</label><input className="form-input" value={form.proveedor_nit} onChange={e => set('proveedor_nit', e.target.value)} required /></div>
          <div className="form-group"><label className="form-label">Razón Social *</label><input className="form-input" value={form.razon_social} onChange={e => set('razon_social', e.target.value)} required /></div>
          <div className="form-group"><label className="form-label">Concepto</label><input className="form-input" value={form.concepto} onChange={e => set('concepto', e.target.value)} /></div>
          <div className="form-group"><label className="form-label">Valor *</label><input className="form-input" type="number" step="0.01" value={form.valor} onChange={e => set('valor', e.target.value)} required /></div>
          <div className="form-group"><label className="form-label">Fecha vencimiento</label><input className="form-input" type="date" value={form.fecha_vencimiento} onChange={e => set('fecha_vencimiento', e.target.value)} /></div>
        </div>
        <div className="form-group"><label className="form-label">Notas</label><input className="form-input" value={form.notas} onChange={e => set('notas', e.target.value)} /></div>
        {error && <div className="form-error">{error}</div>}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>Cancelar</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Guardando...' : 'Crear CxP'}</button>
        </div>
      </form>
    </Modal>
  );
}

// ── Vista principal ───────────────────────────────────────

type Tab = 'cxc' | 'cxp';

export default function CarteraView() {
  const [tab, setTab] = useState<Tab>('cxc');
  const [stats, setStats] = useState<CarteraStats | null>(null);
  const [cxcList, setCxcList] = useState<CxC[]>([]);
  const [cxpList, setCxpList] = useState<CxP[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [filterEstado, setFilterEstado] = useState('');
  const [modalCxC, setModalCxC] = useState(false);
  const [modalCxP, setModalCxP] = useState(false);
  const [abonoTarget, setAbonoTarget] = useState<{ id: number; saldo: number; tipo: Tab } | null>(null);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => setToast({ message, type });

  const load = useCallback(async () => {
    try {
      const [s, cxc, cxp] = await Promise.all([
        carteraApi.stats(),
        carteraApi.listCxC(filterEstado || undefined),
        carteraApi.listCxP(filterEstado || undefined),
      ]);
      setStats(s); setCxcList(cxc); setCxpList(cxp);
    } catch { showToast('Error al cargar cartera', 'error'); }
    finally { setLoading(false); }
  }, [filterEstado]);

  useEffect(() => { load(); }, [load]);

  const handleCreateCxC = async (data: any) => {
    await carteraApi.createCxC(data);
    showToast('CxC creada'); setModalCxC(false); load();
  };
  const handleCreateCxP = async (data: any) => {
    await carteraApi.createCxP(data);
    showToast('CxP creada'); setModalCxP(false); load();
  };
  const handleAbono = async (valor: number, notas: string) => {
    if (!abonoTarget) return;
    if (abonoTarget.tipo === 'cxc') await carteraApi.abonarCxC(abonoTarget.id, valor, notas);
    else await carteraApi.abonarCxP(abonoTarget.id, valor, notas);
    showToast('Abono registrado'); setAbonoTarget(null); load();
  };
  const handleAnular = async (id: number, tipo: Tab) => {
    if (!confirm('¿Anular este documento?')) return;
    if (tipo === 'cxc') await carteraApi.anularCxC(id);
    else await carteraApi.anularCxP(id);
    showToast('Documento anulado'); load();
  };

  const ESTADOS = ['', 'Pendiente', 'Parcial', 'Pagado', 'Vencido', 'Anulado'];

  return (
    <div>
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

      {/* ── Stats ───────────────────────────────────── */}
      {stats && (
        <div className="stats-grid" style={{ marginBottom: 24 }}>
          <div className="stat-card fade-in">
            <div className="stat-card-header"><div className="stat-card-icon green">💰</div></div>
            <div className="stat-card-value">{formatCOP(stats.cxc_pendiente)}</div>
            <div className="stat-card-label">Por cobrar</div>
          </div>
          <div className="stat-card fade-in">
            <div className="stat-card-header"><div className={`stat-card-icon ${stats.cxc_vencida > 0 ? 'red' : 'neutral'}`}>⚠️</div></div>
            <div className="stat-card-value">{formatCOP(stats.cxc_vencida)}</div>
            <div className="stat-card-label">CxC vencida</div>
          </div>
          <div className="stat-card fade-in">
            <div className="stat-card-header"><div className="stat-card-icon amber">💸</div></div>
            <div className="stat-card-value">{formatCOP(stats.cxp_pendiente)}</div>
            <div className="stat-card-label">Por pagar</div>
          </div>
          <div className="stat-card fade-in">
            <div className="stat-card-header"><div className={`stat-card-icon ${stats.cxp_vencida > 0 ? 'red' : 'neutral'}`}>🔴</div></div>
            <div className="stat-card-value">{formatCOP(stats.cxp_vencida)}</div>
            <div className="stat-card-label">CxP vencida</div>
          </div>
        </div>
      )}

      {/* ── Tabs + acciones ─────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          {(['cxc', 'cxp'] as Tab[]).map(t => (
            <button key={t} className={`btn ${tab === t ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setTab(t)}>
              {t === 'cxc' ? '📥 Cuentas por Cobrar' : '📤 Cuentas por Pagar'}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select className="form-input" style={{ width: 'auto', padding: '6px 10px' }} value={filterEstado} onChange={e => setFilterEstado(e.target.value)}>
            {ESTADOS.map(e => <option key={e} value={e}>{e || 'Todos los estados'}</option>)}
          </select>
          <button className="btn btn-primary" onClick={() => tab === 'cxc' ? setModalCxC(true) : setModalCxP(true)}>
            + Nueva {tab === 'cxc' ? 'CxC' : 'CxP'}
          </button>
        </div>
      </div>

      {/* ── Tabla CxC ───────────────────────────────── */}
      {tab === 'cxc' && (
        loading ? (
          <div className="loading-screen" style={{ minHeight: 200 }}><div className="loading-spinner" /></div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Factura</th>
                  <th>Cliente</th>
                  <th>Marca</th>
                  <th>Valor</th>
                  <th>Abonos</th>
                  <th>Saldo</th>
                  <th>Vence</th>
                  <th>Estado</th>
                  <th style={{ textAlign: 'right' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {cxcList.length === 0
                  ? <tr><td colSpan={9} style={{ textAlign: 'center', padding: 32, color: 'var(--neutral-500)' }}>Sin registros</td></tr>
                  : cxcList.map(c => (
                    <tr key={c.id} style={{ background: rowColor(c.dias_vencido, c.estado) }}>
                      <td style={{ fontWeight: 600, color: 'var(--neutral-100)' }}>{c.numero_factura}</td>
                      <td>
                        <div style={{ fontWeight: 500 }}>{c.nombre_cliente}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--neutral-500)' }}>{c.cliente_nit}</div>
                      </td>
                      <td style={{ color: 'var(--neutral-400)', fontSize: '0.82rem' }}>{c.marca || '—'}</td>
                      <td>{formatCOP(c.valor_factura)}</td>
                      <td style={{ color: 'var(--green-400)' }}>{formatCOP(c.abonos)}</td>
                      <td style={{ fontWeight: 600 }}>{formatCOP(c.saldo_pendiente)}</td>
                      <td style={{ fontSize: '0.82rem', color: c.dias_vencido > 0 ? 'var(--red-400)' : 'var(--neutral-400)' }}>
                        {c.fecha_vencimiento ? new Date(c.fecha_vencimiento).toLocaleDateString('es-CO') : '—'}
                      </td>
                      <td>{estadoBadge(c.estado, c.dias_vencido)}</td>
                      <td>
                        <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                          {!['Pagado', 'Anulado'].includes(c.estado) && (
                            <button className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '3px 8px' }}
                              onClick={() => setAbonoTarget({ id: c.id, saldo: c.saldo_pendiente, tipo: 'cxc' })}>
                              💵 Abonar
                            </button>
                          )}
                          {!['Anulado'].includes(c.estado) && (
                            <button className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '3px 8px', color: 'var(--red-400)' }}
                              onClick={() => handleAnular(c.id, 'cxc')}>
                              🚫
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )
      )}

      {/* ── Tabla CxP ───────────────────────────────── */}
      {tab === 'cxp' && (
        loading ? (
          <div className="loading-screen" style={{ minHeight: 200 }}><div className="loading-spinner" /></div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Documento</th>
                  <th>Origen</th>
                  <th>Proveedor</th>
                  <th>Concepto</th>
                  <th>Valor</th>
                  <th>Abonos</th>
                  <th>Saldo</th>
                  <th>Vence</th>
                  <th>Estado</th>
                  <th style={{ textAlign: 'right' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {cxpList.length === 0
                  ? <tr><td colSpan={10} style={{ textAlign: 'center', padding: 32, color: 'var(--neutral-500)' }}>Sin registros</td></tr>
                  : cxpList.map(p => (
                    <tr key={p.id} style={{ background: rowColor(p.dias_vencido, p.estado) }}>
                      <td style={{ fontWeight: 600, color: 'var(--neutral-100)', fontFamily: 'monospace', fontSize: '0.82rem' }}>{p.numero_documento}</td>
                      <td>
                        {p.compra_id
                          ? <span className="badge" style={{ background: '#dbeafe', color: '#1d4ed8', fontSize: 10 }}>📥 Compra</span>
                          : <span className="badge" style={{ background: '#f3f4f6', color: '#6b7280', fontSize: 10 }}>Manual</span>
                        }
                      </td>
                      <td>
                        <div style={{ fontWeight: 500 }}>{p.razon_social}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--neutral-500)' }}>{p.proveedor_nit}</div>
                      </td>
                      <td style={{ color: 'var(--neutral-400)', fontSize: '0.82rem', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.concepto || '—'}</td>
                      <td>{formatCOP(p.valor)}</td>
                      <td style={{ color: 'var(--green-400)' }}>{formatCOP(p.abonos)}</td>
                      <td style={{ fontWeight: 600 }}>{formatCOP(p.saldo_pendiente)}</td>
                      <td style={{ fontSize: '0.82rem', color: p.dias_vencido > 0 ? 'var(--red-400)' : 'var(--neutral-400)' }}>
                        {p.fecha_vencimiento ? new Date(p.fecha_vencimiento).toLocaleDateString('es-CO') : '—'}
                      </td>
                      <td>{estadoBadge(p.estado, p.dias_vencido)}</td>
                      <td>
                        <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                          {!['Pagado', 'Anulado'].includes(p.estado) && (
                            <button className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '3px 8px' }}
                              onClick={() => setAbonoTarget({ id: p.id, saldo: p.saldo_pendiente, tipo: 'cxp' })}>
                              💵 Pagar
                            </button>
                          )}
                          {!['Anulado'].includes(p.estado) && (
                            <button className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '3px 8px', color: 'var(--red-400)' }}
                              onClick={() => handleAnular(p.id, 'cxp')}>
                              🚫
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )
      )}

      {/* ── Modales ──────────────────────────────────── */}
      {modalCxC && <CxCFormModal onSave={handleCreateCxC} onClose={() => setModalCxC(false)} />}
      {modalCxP && <CxPFormModal onSave={handleCreateCxP} onClose={() => setModalCxP(false)} />}
      {abonoTarget && (
        <AbonoModal saldo={abonoTarget.saldo} onAbono={handleAbono} onClose={() => setAbonoTarget(null)} />
      )}
    </div>
  );
}
