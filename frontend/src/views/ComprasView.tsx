import { useState, useEffect, useCallback } from 'react';
import {
  comprasApi,
  type Proveedor,
  type Compra,
  type ComprasDashboard,
  type CompraDetalleInput,
} from '../services/comprasApi';
import { printCompra } from '../utils/printCompra';

type ComprasTab = 'dashboard' | 'proveedores' | 'compras' | 'nueva';

// ══════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════

const COP = (n: number | string) =>
  Number(n).toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 0 });

const ESTADO_PAGO_COLOR: Record<string, string> = {
  Pendiente: '#f59e0b',
  Pagado: '#22c55e',
  Vencido: '#ef4444',
  Parcial: '#3b82f6',
};

const IVA_OPTIONS = [0, 5, 19];

// ══════════════════════════════════════════════════════════
// TOAST
// ══════════════════════════════════════════════════════════

function Toast({ message, type, onClose }: { message: string; type: 'success' | 'error'; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3500);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className={`toast toast-${type} fade-in`}>
      <span>{type === 'success' ? '✅' : '❌'}</span>
      <span>{message}</span>
      <button className="toast-close" onClick={onClose}>×</button>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// MODAL
// ══════════════════════════════════════════════════════════

function Modal({ title, onClose, children, wide }: { title: string; onClose: () => void; children: React.ReactNode; wide?: boolean }) {
  return (
    <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className={`modal-card fade-in ${wide ? 'modal-wide' : ''}`}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// DASHBOARD TAB
// ══════════════════════════════════════════════════════════

function ComprasDashboardTab() {
  const [stats, setStats] = useState<ComprasDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    comprasApi.getDashboard()
      .then(r => setStats(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-spinner" style={{ margin: '60px auto' }} />;
  if (!stats) return <div className="empty-state"><div className="empty-state-text">Error cargando dashboard</div></div>;

  const variacion = stats.total_compras_mes_anterior > 0
    ? ((Number(stats.total_compras_mes) - Number(stats.total_compras_mes_anterior)) / Number(stats.total_compras_mes_anterior)) * 100
    : 0;

  return (
    <div className="fade-in">
      {/* KPIs */}
      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
        <div className="kpi-card">
          <div className="kpi-label">Compras este mes</div>
          <div className="kpi-value">{COP(stats.total_compras_mes)}</div>
          <div className={`kpi-change ${variacion >= 0 ? 'kpi-up' : 'kpi-down'}`}>
            {variacion >= 0 ? '▲' : '▼'} {Math.abs(variacion).toFixed(1)}% vs mes anterior
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Documentos este mes</div>
          <div className="kpi-value">{stats.cantidad_compras_mes}</div>
          <div className="kpi-change">facturas/notas registradas</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">CxP pendiente</div>
          <div className="kpi-value" style={{ color: '#ef4444' }}>{COP(stats.cxp_pendiente)}</div>
          <div className="kpi-change">por pagar a proveedores</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Proveedores activos</div>
          <div className="kpi-value">{stats.total_proveedores_activos}</div>
          <div className="kpi-change">proveedores activos</div>
        </div>
      </div>

      {/* Top proveedores */}
      {stats.top_proveedores.length > 0 && (
        <div className="table-card">
          <div className="table-card-header">
            <h3>Top Proveedores del Mes</h3>
          </div>
          <table className="erp-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Proveedor</th>
                <th style={{ textAlign: 'right' }}>Total comprado</th>
              </tr>
            </thead>
            <tbody>
              {stats.top_proveedores.map((p, i) => (
                <tr key={i}>
                  <td><span className="badge" style={{ background: '#2563eb', color: '#fff' }}>{i + 1}</span></td>
                  <td>{p.proveedor ?? '—'}</td>
                  <td style={{ textAlign: 'right', fontWeight: 700 }}>{COP(p.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// PROVEEDORES TAB
// ══════════════════════════════════════════════════════════

const PROVEEDOR_EMPTY = {
  nit_cc: '', razon_social: '', nombre_comercial: '', tipo_persona: 'Jurídica',
  regimen_iva: 'Responsable', categoria: '', direccion: '', ciudad: '', departamento: '',
  telefono: '', celular: '', email: '', contacto_nombre: '', contacto_cargo: '',
  dias_credito: 30, notas: '',
};

function ProveedoresTab({ onToast }: { onToast: (msg: string, type: 'success' | 'error') => void }) {
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState<'crear' | 'editar' | null>(null);
  const [selected, setSelected] = useState<Proveedor | null>(null);
  const [form, setForm] = useState({ ...PROVEEDOR_EMPTY });
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    comprasApi.getProveedores()
      .then(r => setProveedores(r.data))
      .catch(() => onToast('Error cargando proveedores', 'error'))
      .finally(() => setLoading(false));
  }, [onToast]);

  useEffect(() => { load(); }, [load]);

  const filtered = proveedores.filter(p =>
    p.razon_social.toLowerCase().includes(search.toLowerCase()) ||
    p.nit_cc.includes(search)
  );

  const openCrear = () => { setForm({ ...PROVEEDOR_EMPTY }); setSelected(null); setModal('crear'); };
  const openEditar = (p: Proveedor) => {
    setSelected(p);
    setForm({
      nit_cc: p.nit_cc, razon_social: p.razon_social, nombre_comercial: p.nombre_comercial ?? '',
      tipo_persona: p.tipo_persona, regimen_iva: p.regimen_iva, categoria: p.categoria ?? '',
      direccion: p.direccion ?? '', ciudad: p.ciudad ?? '', departamento: p.departamento ?? '',
      telefono: p.telefono ?? '', celular: p.celular ?? '', email: p.email ?? '',
      contacto_nombre: p.contacto_nombre ?? '', contacto_cargo: p.contacto_cargo ?? '',
      dias_credito: p.dias_credito, notas: p.notas ?? '',
    });
    setModal('editar');
  };

  const handleSave = async () => {
    if (!form.nit_cc || !form.razon_social) { onToast('NIT y Razón Social son requeridos', 'error'); return; }
    setSaving(true);
    try {
      if (modal === 'crear') {
        await comprasApi.createProveedor(form as any);
        onToast('Proveedor creado', 'success');
      } else if (selected) {
        await comprasApi.updateProveedor(selected.id, form);
        onToast('Proveedor actualizado', 'success');
      }
      setModal(null);
      load();
    } catch {
      onToast('Error guardando proveedor', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (p: Proveedor) => {
    if (!confirm(`¿Desactivar proveedor "${p.razon_social}"?`)) return;
    try {
      await comprasApi.deleteProveedor(p.id);
      onToast('Proveedor desactivado', 'success');
      load();
    } catch {
      onToast('Error desactivando proveedor', 'error');
    }
  };

  const F = (field: keyof typeof form, value: string | number) =>
    setForm(f => ({ ...f, [field]: value }));

  return (
    <div className="fade-in">
      <div className="table-card">
        <div className="table-card-header">
          <h3>Proveedores ({filtered.length})</h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              className="search-input"
              placeholder="Buscar por nombre o NIT..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <button className="btn-primary" onClick={openCrear}>+ Nuevo</button>
          </div>
        </div>

        {loading ? <div className="loading-spinner" style={{ margin: '40px auto' }} /> : (
          <table className="erp-table">
            <thead>
              <tr>
                <th>NIT / CC</th>
                <th>Razón Social</th>
                <th>Ciudad</th>
                <th>Teléfono</th>
                <th>Días crédito</th>
                <th>Régimen IVA</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={8} style={{ textAlign: 'center', color: '#888', padding: 32 }}>Sin proveedores registrados</td></tr>
              ) : filtered.map(p => (
                <tr key={p.id}>
                  <td><span style={{ fontFamily: 'monospace', fontSize: 11 }}>{p.nit_cc}{p.dv ? `-${p.dv}` : ''}</span></td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{p.razon_social}</div>
                    {p.nombre_comercial && <div style={{ fontSize: 10, color: '#888' }}>{p.nombre_comercial}</div>}
                  </td>
                  <td>{p.ciudad ?? '—'}</td>
                  <td>{p.celular ?? p.telefono ?? '—'}</td>
                  <td>{p.dias_credito} días</td>
                  <td><span className="badge">{p.regimen_iva}</span></td>
                  <td>
                    <span className="badge" style={{ background: p.activo ? '#dcfce7' : '#fee2e2', color: p.activo ? '#16a34a' : '#dc2626' }}>
                      {p.activo ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td>
                    <button className="btn-icon" onClick={() => openEditar(p)} title="Editar">✏️</button>
                    {p.activo && <button className="btn-icon" onClick={() => handleDelete(p)} title="Desactivar">🗑️</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modal && (
        <Modal title={modal === 'crear' ? 'Nuevo Proveedor' : `Editar: ${selected?.razon_social}`} onClose={() => setModal(null)} wide>
          <div className="form-grid-2">
            <div className="form-group">
              <label>NIT / CC *</label>
              <input className="form-input" value={form.nit_cc} onChange={e => F('nit_cc', e.target.value)} placeholder="900123456" disabled={modal === 'editar'} />
            </div>
            <div className="form-group">
              <label>Razón Social *</label>
              <input className="form-input" value={form.razon_social} onChange={e => F('razon_social', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Nombre Comercial</label>
              <input className="form-input" value={form.nombre_comercial} onChange={e => F('nombre_comercial', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Tipo Persona</label>
              <select className="form-select" value={form.tipo_persona} onChange={e => F('tipo_persona', e.target.value)}>
                <option>Jurídica</option>
                <option>Natural</option>
              </select>
            </div>
            <div className="form-group">
              <label>Régimen IVA</label>
              <select className="form-select" value={form.regimen_iva} onChange={e => F('regimen_iva', e.target.value)}>
                <option>Responsable</option>
                <option>No Responsable</option>
                <option>Gran Contribuyente</option>
              </select>
            </div>
            <div className="form-group">
              <label>Categoría</label>
              <input className="form-input" value={form.categoria} onChange={e => F('categoria', e.target.value)} placeholder="Insumos, Servicios..." />
            </div>
            <div className="form-group">
              <label>Ciudad</label>
              <input className="form-input" value={form.ciudad} onChange={e => F('ciudad', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Departamento</label>
              <input className="form-input" value={form.departamento} onChange={e => F('departamento', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Teléfono</label>
              <input className="form-input" value={form.telefono} onChange={e => F('telefono', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Celular</label>
              <input className="form-input" value={form.celular} onChange={e => F('celular', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input className="form-input" type="email" value={form.email} onChange={e => F('email', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Días de Crédito</label>
              <input className="form-input" type="number" min={0} value={form.dias_credito} onChange={e => F('dias_credito', Number(e.target.value))} />
            </div>
            <div className="form-group">
              <label>Contacto — Nombre</label>
              <input className="form-input" value={form.contacto_nombre} onChange={e => F('contacto_nombre', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Contacto — Cargo</label>
              <input className="form-input" value={form.contacto_cargo} onChange={e => F('contacto_cargo', e.target.value)} />
            </div>
          </div>
          <div className="form-group" style={{ marginTop: 8 }}>
            <label>Notas</label>
            <textarea className="form-input" rows={2} value={form.notas} onChange={e => F('notas', e.target.value)} />
          </div>
          <div className="modal-footer">
            <button className="btn-secondary" onClick={() => setModal(null)}>Cancelar</button>
            <button className="btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// COMPRAS LIST TAB
// ══════════════════════════════════════════════════════════

function ComprasListTab({
  onToast,
  onNueva,
}: { onToast: (msg: string, type: 'success' | 'error') => void; onNueva: () => void }) {
  const [compras, setCompras] = useState<Compra[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Compra | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    comprasApi.getCompras()
      .then(r => setCompras(r.data))
      .catch(() => onToast('Error cargando compras', 'error'))
      .finally(() => setLoading(false));
  }, [onToast]);

  useEffect(() => { load(); }, [load]);

  const filtered = compras.filter(c =>
    c.numero.toLowerCase().includes(search.toLowerCase()) ||
    (c.proveedor_razon_social ?? '').toLowerCase().includes(search.toLowerCase())
  );

  const handleConfirmar = async (c: Compra) => {
    if (!confirm(`¿Confirmar compra ${c.numero}?`)) return;
    try {
      await comprasApi.confirmarCompra(c.id);
      onToast('Compra confirmada', 'success');
      load();
    } catch {
      onToast('Error confirmando compra', 'error');
    }
  };

  const handleAnular = async (c: Compra) => {
    if (!confirm(`¿Anular compra ${c.numero}? Esta acción no se puede deshacer.`)) return;
    try {
      await comprasApi.anularCompra(c.id);
      onToast('Compra anulada', 'success');
      load();
    } catch {
      onToast('Error anulando compra', 'error');
    }
  };

  return (
    <div className="fade-in">
      <div className="table-card">
        <div className="table-card-header">
          <h3>Compras Registradas ({filtered.length})</h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              className="search-input"
              placeholder="Buscar por número o proveedor..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <button className="btn-primary" onClick={onNueva}>+ Nueva Compra</button>
          </div>
        </div>

        {loading ? <div className="loading-spinner" style={{ margin: '40px auto' }} /> : (
          <table className="erp-table">
            <thead>
              <tr>
                <th>Número</th>
                <th>Fecha</th>
                <th>Proveedor</th>
                <th>Ref. Proveedor</th>
                <th style={{ textAlign: 'right' }}>Total</th>
                <th>Estado</th>
                <th>Pago</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={8} style={{ textAlign: 'center', color: '#888', padding: 32 }}>Sin compras registradas</td></tr>
              ) : filtered.map(c => (
                <tr key={c.id}>
                  <td><span style={{ fontFamily: 'monospace', fontSize: 11, fontWeight: 700, color: '#2563eb' }}>{c.numero}</span></td>
                  <td>{c.fecha}</td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{c.proveedor_razon_social ?? '—'}</div>
                    {c.proveedor_nit && <div style={{ fontSize: 10, color: '#888' }}>NIT: {c.proveedor_nit}</div>}
                  </td>
                  <td style={{ fontSize: 11, color: '#666' }}>{c.ref_proveedor ?? '—'}</td>
                  <td style={{ textAlign: 'right', fontWeight: 700 }}>{COP(c.total)}</td>
                  <td>
                    <span className="badge" style={{
                      background: c.estado === 'Confirmada' ? '#dbeafe' : c.estado === 'Anulada' ? '#fee2e2' : '#fef3c7',
                      color: c.estado === 'Confirmada' ? '#1d4ed8' : c.estado === 'Anulada' ? '#dc2626' : '#92400e',
                    }}>{c.estado}</span>
                  </td>
                  <td>
                    <span className="badge" style={{
                      background: '#f0f4ff',
                      color: ESTADO_PAGO_COLOR[c.estado_pago] ?? '#555',
                    }}>{c.estado_pago}</span>
                  </td>
                  <td style={{ display: 'flex', gap: 4 }}>
                    <button className="btn-icon" onClick={() => setSelected(c)} title="Ver detalle">🔍</button>
                    <button className="btn-icon" onClick={() => printCompra(c)} title="Imprimir">🖨️</button>
                    {c.estado === 'Borrador' && (
                      <button className="btn-icon" style={{ color: '#2563eb' }} onClick={() => handleConfirmar(c)} title="Confirmar">✔️</button>
                    )}
                    {c.estado !== 'Anulada' && (
                      <button className="btn-icon" style={{ color: '#ef4444' }} onClick={() => handleAnular(c)} title="Anular">🚫</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <Modal title={`Compra ${selected.numero}`} onClose={() => setSelected(null)} wide>
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 12 }}>
              <div><span style={{ color: '#888', fontSize: 11 }}>Proveedor</span><br /><strong>{selected.proveedor_razon_social}</strong></div>
              <div><span style={{ color: '#888', fontSize: 11 }}>NIT</span><br /><strong>{selected.proveedor_nit}</strong></div>
              <div><span style={{ color: '#888', fontSize: 11 }}>Fecha</span><br /><strong>{selected.fecha}</strong></div>
              <div><span style={{ color: '#888', fontSize: 11 }}>Vencimiento</span><br /><strong>{selected.fecha_vencimiento ?? '—'}</strong></div>
              <div><span style={{ color: '#888', fontSize: 11 }}>Estado</span><br /><strong>{selected.estado}</strong></div>
              <div><span style={{ color: '#888', fontSize: 11 }}>Pago</span><br /><strong>{selected.estado_pago}</strong></div>
            </div>

            <table className="erp-table">
              <thead>
                <tr>
                  <th>Descripción</th>
                  <th style={{ textAlign: 'right' }}>Cant.</th>
                  <th style={{ textAlign: 'right' }}>P. Unit.</th>
                  <th style={{ textAlign: 'right' }}>Desc.%</th>
                  <th style={{ textAlign: 'right' }}>IVA%</th>
                  <th style={{ textAlign: 'right' }}>Total línea</th>
                </tr>
              </thead>
              <tbody>
                {selected.detalles.map(d => (
                  <tr key={d.id}>
                    <td>{d.descripcion}</td>
                    <td style={{ textAlign: 'right' }}>{Number(d.cantidad)}</td>
                    <td style={{ textAlign: 'right' }}>{COP(d.precio_unitario)}</td>
                    <td style={{ textAlign: 'right' }}>{Number(d.descuento_porcentaje)}%</td>
                    <td style={{ textAlign: 'right' }}>{Number(d.iva_porcentaje)}%</td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>{COP(d.total_linea)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
              <table style={{ minWidth: 240, borderCollapse: 'collapse' }}>
                <tbody>
                  {[
                    ['Subtotal', selected.subtotal],
                    Number(selected.descuento_total) > 0 ? ['Descuentos', -Number(selected.descuento_total)] : null,
                    ['Base gravable', selected.base_gravable],
                    ['IVA', selected.iva_total],
                    Number(selected.retefuente) > 0 ? ['ReteFuente', -Number(selected.retefuente)] : null,
                    Number(selected.reteiva) > 0 ? ['ReteIVA', -Number(selected.reteiva)] : null,
                    Number(selected.reteica) > 0 ? ['ReteICA', -Number(selected.reteica)] : null,
                  ].filter(Boolean).map(([label, val], i) => (
                    <tr key={i}>
                      <td style={{ padding: '3px 12px', color: '#666', fontSize: 12 }}>{label as string}</td>
                      <td style={{ padding: '3px 12px', textAlign: 'right', fontFamily: 'monospace' }}>{COP(val as number)}</td>
                    </tr>
                  ))}
                  <tr style={{ background: '#2563eb', color: '#fff' }}>
                    <td style={{ padding: '7px 12px', fontWeight: 800, fontSize: 13 }}>TOTAL A PAGAR</td>
                    <td style={{ padding: '7px 12px', textAlign: 'right', fontWeight: 800, fontFamily: 'monospace', fontSize: 13 }}>{COP(selected.total)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div className="modal-footer">
            <button className="btn-secondary" onClick={() => setSelected(null)}>Cerrar</button>
            <button className="btn-primary" onClick={() => printCompra(selected)}>🖨️ Imprimir</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// NUEVA COMPRA TAB
// ══════════════════════════════════════════════════════════

const DETALLE_EMPTY: CompraDetalleInput = {
  descripcion: '',
  cantidad: 1,
  precio_unitario: 0,
  descuento_porcentaje: 0,
  iva_porcentaje: 19,
};

function NuevaCompraTab({
  onToast,
  onSaved,
}: { onToast: (msg: string, type: 'success' | 'error') => void; onSaved: () => void }) {
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [form, setForm] = useState({
    fecha: new Date().toISOString().slice(0, 10),
    fecha_vencimiento: '',
    proveedor_id: 0,
    ref_proveedor: '',
    retefuente: 0,
    reteiva: 0,
    reteica: 0,
    observaciones: '',
  });
  const [detalles, setDetalles] = useState<CompraDetalleInput[]>([{ ...DETALLE_EMPTY }]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    comprasApi.getProveedores().then(r => setProveedores(r.data)).catch(() => {});
  }, []);

  const F = (field: keyof typeof form, value: string | number) =>
    setForm(f => ({ ...f, [field]: value }));

  const setDetalle = (i: number, field: keyof CompraDetalleInput, value: string | number) =>
    setDetalles(ds => ds.map((d, idx) => idx === i ? { ...d, [field]: value } : d));

  const addDetalle = () => setDetalles(ds => [...ds, { ...DETALLE_EMPTY }]);
  const removeDetalle = (i: number) => setDetalles(ds => ds.filter((_, idx) => idx !== i));

  // Cálculos en tiempo real
  const calcTotales = () => {
    let subtotal = 0, descuento_total = 0, iva_total = 0;
    for (const d of detalles) {
      const base = Number(d.cantidad) * Number(d.precio_unitario);
      const desc = base * (Number(d.descuento_porcentaje) / 100);
      const gravable = base - desc;
      const iva = gravable * (Number(d.iva_porcentaje) / 100);
      subtotal += base;
      descuento_total += desc;
      iva_total += iva;
    }
    const base_gravable = subtotal - descuento_total;
    const total = base_gravable + iva_total - Number(form.retefuente) - Number(form.reteiva) - Number(form.reteica);
    return { subtotal, descuento_total, base_gravable, iva_total, total };
  };

  const t = calcTotales();

  const handleSubmit = async () => {
    if (!form.proveedor_id) { onToast('Selecciona un proveedor', 'error'); return; }
    if (!form.fecha) { onToast('La fecha es requerida', 'error'); return; }
    if (detalles.length === 0 || detalles.some(d => !d.descripcion || !Number(d.precio_unitario))) {
      onToast('Completa todos los ítems (descripción y precio)', 'error'); return;
    }
    setSaving(true);
    try {
      await comprasApi.createCompra({
        ...form,
        proveedor_id: Number(form.proveedor_id),
        retefuente: Number(form.retefuente),
        reteiva: Number(form.reteiva),
        reteica: Number(form.reteica),
        fecha_vencimiento: form.fecha_vencimiento || undefined,
        detalles,
      });
      onToast('Compra creada exitosamente', 'success');
      onSaved();
    } catch {
      onToast('Error creando la compra', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="table-card" style={{ maxWidth: 900 }}>
        <div className="table-card-header">
          <h3>Nueva Compra / Factura de Proveedor</h3>
        </div>
        <div style={{ padding: '0 20px 20px' }}>
          {/* Cabecera */}
          <div className="form-grid-2" style={{ marginBottom: 16 }}>
            <div className="form-group">
              <label>Proveedor *</label>
              <select className="form-select" value={form.proveedor_id} onChange={e => F('proveedor_id', Number(e.target.value))}>
                <option value={0}>— Seleccionar proveedor —</option>
                {proveedores.map(p => (
                  <option key={p.id} value={p.id}>{p.razon_social} ({p.nit_cc})</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Ref. Proveedor (N° factura del proveedor)</label>
              <input className="form-input" value={form.ref_proveedor} onChange={e => F('ref_proveedor', e.target.value)} placeholder="FV-001..." />
            </div>
            <div className="form-group">
              <label>Fecha *</label>
              <input className="form-input" type="date" value={form.fecha} onChange={e => F('fecha', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Fecha Vencimiento</label>
              <input className="form-input" type="date" value={form.fecha_vencimiento} onChange={e => F('fecha_vencimiento', e.target.value)} />
            </div>
          </div>

          {/* Líneas de detalle */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <label style={{ fontWeight: 600, fontSize: 13 }}>Ítems</label>
              <button className="btn-secondary" style={{ fontSize: 11, padding: '4px 10px' }} onClick={addDetalle}>+ Agregar ítem</button>
            </div>
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Descripción</th>
                  <th style={{ textAlign: 'right', width: 70 }}>Cant.</th>
                  <th style={{ textAlign: 'right', width: 120 }}>P. Unitario</th>
                  <th style={{ textAlign: 'right', width: 70 }}>Desc.%</th>
                  <th style={{ textAlign: 'right', width: 70 }}>IVA%</th>
                  <th style={{ textAlign: 'right', width: 120 }}>Total</th>
                  <th style={{ width: 32 }}></th>
                </tr>
              </thead>
              <tbody>
                {detalles.map((d, i) => {
                  const base = Number(d.cantidad) * Number(d.precio_unitario);
                  const desc = base * (Number(d.descuento_porcentaje) / 100);
                  const iva = (base - desc) * (Number(d.iva_porcentaje) / 100);
                  const total = base - desc + iva;
                  return (
                    <tr key={i}>
                      <td>
                        <input
                          className="form-input" style={{ margin: 0, fontSize: 11 }}
                          value={d.descripcion}
                          onChange={e => setDetalle(i, 'descripcion', e.target.value)}
                          placeholder="Descripción del producto/servicio"
                        />
                      </td>
                      <td>
                        <input
                          className="form-input" style={{ margin: 0, textAlign: 'right', fontSize: 11 }}
                          type="number" min={1} value={d.cantidad}
                          onChange={e => setDetalle(i, 'cantidad', Number(e.target.value))}
                        />
                      </td>
                      <td>
                        <input
                          className="form-input" style={{ margin: 0, textAlign: 'right', fontSize: 11 }}
                          type="number" min={0} value={d.precio_unitario}
                          onChange={e => setDetalle(i, 'precio_unitario', Number(e.target.value))}
                        />
                      </td>
                      <td>
                        <input
                          className="form-input" style={{ margin: 0, textAlign: 'right', fontSize: 11 }}
                          type="number" min={0} max={100} value={d.descuento_porcentaje}
                          onChange={e => setDetalle(i, 'descuento_porcentaje', Number(e.target.value))}
                        />
                      </td>
                      <td>
                        <select
                          className="form-select" style={{ margin: 0, fontSize: 11 }}
                          value={d.iva_porcentaje}
                          onChange={e => setDetalle(i, 'iva_porcentaje', Number(e.target.value))}
                        >
                          {IVA_OPTIONS.map(v => <option key={v} value={v}>{v}%</option>)}
                        </select>
                      </td>
                      <td style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: 11, fontWeight: 600 }}>
                        {COP(total)}
                      </td>
                      <td>
                        {detalles.length > 1 && (
                          <button className="btn-icon" onClick={() => removeDetalle(i)} style={{ color: '#ef4444' }}>×</button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Retenciones */}
          <div className="form-grid-2" style={{ marginBottom: 16 }}>
            <div className="form-group">
              <label>ReteFuente ($)</label>
              <input className="form-input" type="number" min={0} value={form.retefuente} onChange={e => F('retefuente', Number(e.target.value))} />
            </div>
            <div className="form-group">
              <label>ReteIVA ($)</label>
              <input className="form-input" type="number" min={0} value={form.reteiva} onChange={e => F('reteiva', Number(e.target.value))} />
            </div>
            <div className="form-group">
              <label>ReteICA ($)</label>
              <input className="form-input" type="number" min={0} value={form.reteica} onChange={e => F('reteica', Number(e.target.value))} />
            </div>
            <div className="form-group">
              <label>Observaciones</label>
              <input className="form-input" value={form.observaciones} onChange={e => F('observaciones', e.target.value)} />
            </div>
          </div>

          {/* Totales */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
            <table style={{ minWidth: 260, borderCollapse: 'collapse', border: '1px solid #e0e0e0', borderRadius: 4, overflow: 'hidden' }}>
              <tbody>
                {[
                  ['Subtotal', t.subtotal],
                  t.descuento_total > 0 ? ['Descuentos', -t.descuento_total] : null,
                  ['Base gravable', t.base_gravable],
                  ['IVA', t.iva_total],
                  Number(form.retefuente) > 0 ? ['ReteFuente', -Number(form.retefuente)] : null,
                  Number(form.reteiva) > 0 ? ['ReteIVA', -Number(form.reteiva)] : null,
                  Number(form.reteica) > 0 ? ['ReteICA', -Number(form.reteica)] : null,
                ].filter(Boolean).map(([label, val], i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                    <td style={{ padding: '4px 12px', color: '#666', fontSize: 12 }}>{label as string}</td>
                    <td style={{ padding: '4px 12px', textAlign: 'right', fontFamily: 'monospace', fontSize: 12 }}>{COP(val as number)}</td>
                  </tr>
                ))}
                <tr style={{ background: '#2563eb', color: '#fff' }}>
                  <td style={{ padding: '8px 12px', fontWeight: 800, fontSize: 14 }}>TOTAL A PAGAR</td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 800, fontFamily: 'monospace', fontSize: 14 }}>{COP(t.total)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <button className="btn-secondary" onClick={() => {
              setForm({ fecha: new Date().toISOString().slice(0, 10), fecha_vencimiento: '', proveedor_id: 0, ref_proveedor: '', retefuente: 0, reteiva: 0, reteica: 0, observaciones: '' });
              setDetalles([{ ...DETALLE_EMPTY }]);
            }}>Limpiar</button>
            <button className="btn-primary" onClick={handleSubmit} disabled={saving}>
              {saving ? 'Guardando...' : '💾 Guardar Compra'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════

export default function ComprasView() {
  const [tab, setTab] = useState<ComprasTab>('dashboard');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type });
  }, []);

  const TABS: { id: ComprasTab; label: string }[] = [
    { id: 'dashboard', label: '📊 Dashboard' },
    { id: 'proveedores', label: '🏢 Proveedores' },
    { id: 'compras', label: '🧾 Compras' },
    { id: 'nueva', label: '+ Nueva Compra' },
  ];

  return (
    <div>
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

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

      {tab === 'dashboard' && <ComprasDashboardTab />}
      {tab === 'proveedores' && <ProveedoresTab onToast={showToast} />}
      {tab === 'compras' && <ComprasListTab onToast={showToast} onNueva={() => setTab('nueva')} />}
      {tab === 'nueva' && <NuevaCompraTab onToast={showToast} onSaved={() => setTab('compras')} />}
    </div>
  );
}
