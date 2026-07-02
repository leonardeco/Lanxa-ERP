/**
 * Ventas & Comercial View — Módulo completo de ventas
 * 4 pestañas: Dashboard, Productos, Clientes, Facturas
 */

import { useState, useEffect, useCallback } from 'react';
import {
  ventasApi,
  type Producto,
  type Cliente,
  type Venta,
  type VentaDashboard,
  type VentaDetalleInput,
} from '../services/ventasApi';
import { printFactura } from '../utils/printFactura';
import Toast from '../components/Toast';
import Modal from '../components/Modal';

type VentasTab = 'dashboard' | 'productos' | 'clientes' | 'facturas';

// ══════════════════════════════════════════════════════════
// MARCAS PARA FILTRO
// ══════════════════════════════════════════════════════════

const MARCAS = [
  'Superozono', 'Ecoozono', 'Agroking', 'Ozono Evolution',
  'Agro Vital', 'Agro Fusion', 'Hiper Ozono', 'Ozono Pro', 'Ozomax', 'Biozono',
];

const MARCA_COLORS: Record<string, string> = {
  Superozono: '#2dd4a0', Ecoozono: '#60a5fa', Agroking: '#fbbf24',
  'Ozono Evolution': '#a78bfa', 'Agro Vital': '#22d3ee', 'Agro Fusion': '#6ee7b7',
  'Hiper Ozono': '#3b82f6', 'Ozono Pro': '#f59e0b', Ozomax: '#f87171', Biozono: '#8b5cf6',
};

// ══════════════════════════════════════════════════════════
// VENTAS DASHBOARD TAB
// ══════════════════════════════════════════════════════════

function VentasDashboardTab() {
  const [stats, setStats] = useState<VentaDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ventasApi.getDashboard()
      .then(res => setStats(res.data))
      .catch(() => { })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="empty-state fade-in"><div className="empty-state-icon">⏳</div><div className="empty-state-text">Cargando dashboard...</div></div>;
  if (!stats) return <div className="empty-state fade-in"><div className="empty-state-icon">⚠️</div><div className="empty-state-text">Error al cargar dashboard</div></div>;

  const kpis = [
    { icon: '💰', label: 'Ventas del Mes', value: `$${Number(stats.ventas_mes_actual).toLocaleString('es-CO')}`, color: 'green' },
    { icon: '📊', label: 'Mes Anterior', value: `$${Number(stats.ventas_mes_anterior).toLocaleString('es-CO')}`, color: 'blue' },
    { icon: '🧾', label: 'Facturas Mes', value: String(stats.cantidad_ventas_mes), color: 'amber' },
    { icon: '🎯', label: 'Ticket Promedio', value: `$${Number(stats.ticket_promedio).toLocaleString('es-CO')}`, color: 'purple' },
    { icon: '👥', label: 'Clientes Activos', value: String(stats.total_clientes_activos), color: 'cyan' },
    { icon: '📦', label: 'Productos Activos', value: String(stats.total_productos_activos), color: 'green' },
    { icon: '⚠️', label: 'Stock Bajo', value: String(stats.productos_stock_bajo), color: stats.productos_stock_bajo > 0 ? 'red' : 'neutral' },
  ];

  const maxVentaMarca = Math.max(...stats.ventas_por_marca.map(v => v.total), 1);

  return (
    <div>
      <div className="stats-grid">
        {kpis.map((kpi, i) => (
          <div key={kpi.label} className={`stat-card fade-in fade-in-delay-${i + 1}`}>
            <div className="stat-card-header">
              <div className={`stat-card-icon ${kpi.color}`}>{kpi.icon}</div>
            </div>
            <div className="stat-card-value">{kpi.value}</div>
            <div className="stat-card-label">{kpi.label}</div>
          </div>
        ))}
      </div>

      {stats.ventas_por_marca.length > 0 && (
        <div className="chart-card fade-in" style={{ marginTop: 16 }}>
          <div className="chart-card-title">📊 Ventas por Marca (Mes Actual)</div>
          <div className="bar-chart">
            {stats.ventas_por_marca.map(vm => (
              <div className="bar-item" key={vm.marca}>
                <div className="bar-label">{vm.marca}</div>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{
                      width: `${Math.max((vm.total / maxVentaMarca) * 100, 5)}%`,
                      background: `linear-gradient(90deg, ${MARCA_COLORS[vm.marca] || '#6b7280'}88, ${MARCA_COLORS[vm.marca] || '#6b7280'})`,
                    }}
                  >
                    <span>${Number(vm.total).toLocaleString('es-CO')}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// PRODUCTOS TAB
// ══════════════════════════════════════════════════════════

function ProductosTab() {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtroMarca, setFiltroMarca] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Producto | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);

  const fetchProductos = useCallback(() => {
    setLoading(true);
    ventasApi.getProductos(filtroMarca || undefined)
      .then(res => setProductos(res.data))
      .catch(() => setToast({ msg: 'Error al cargar productos', type: 'error' }))
      .finally(() => setLoading(false));
  }, [filtroMarca]);

  useEffect(() => { fetchProductos(); }, [fetchProductos]);

  const handleSaveProducto = async (data: Record<string, any>) => {
    try {
      if (editing) {
        await ventasApi.updateProducto(editing.id, data);
        setToast({ msg: 'Producto actualizado', type: 'success' });
      } else {
        await ventasApi.createProducto(data as any);
        setToast({ msg: 'Producto creado exitosamente', type: 'success' });
      }
      setShowModal(false);
      setEditing(null);
      fetchProductos();
    } catch (err: any) {
      setToast({ msg: err.response?.data?.detail || 'Error al guardar', type: 'error' });
    }
  };

  const handleDelete = async (p: Producto) => {
    if (!confirm(`¿Desactivar "${p.nombre}"?`)) return;
    try {
      await ventasApi.deleteProducto(p.id);
      setToast({ msg: 'Producto desactivado', type: 'success' });
      fetchProductos();
    } catch {
      setToast({ msg: 'Error al desactivar', type: 'error' });
    }
  };

  return (
    <div className="fade-in">
      {toast && <Toast message={toast.msg} type={toast.type} onClose={() => setToast(null)} />}

      <div className="table-container">
        <div className="table-header">
          <div className="table-title">📦 Catálogo de Productos</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <select
              className="form-select-sm"
              value={filtroMarca}
              onChange={e => setFiltroMarca(e.target.value)}
            >
              <option value="">Todas las marcas</option>
              {MARCAS.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
            <div className="table-count">{productos.length} productos</div>
            <button className="btn-primary-sm" onClick={() => { setEditing(null); setShowModal(true); }}>
              + Nuevo Producto
            </button>
          </div>
        </div>

        {loading ? (
          <div className="empty-state"><div className="empty-state-icon">⏳</div></div>
        ) : (
          <div style={{ maxHeight: 'calc(100vh - 280px)', overflowY: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Producto</th>
                  <th>Marca</th>
                  <th>Categoría</th>
                  <th>Precio Venta</th>
                  <th>IVA</th>
                  <th>Stock</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {productos.map(p => (
                  <tr key={p.id} style={{ opacity: p.activo ? 1 : 0.5 }}>
                    <td className="code">{p.sku}</td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{p.nombre}</div>
                      {p.contenido_neto && <div style={{ fontSize: '0.7rem', color: 'var(--neutral-500)' }}>{p.contenido_neto} · {p.unidad_medida}</div>}
                    </td>
                    <td>
                      <span className="badge" style={{ background: `${MARCA_COLORS[p.marca] || '#6b7280'}22`, color: MARCA_COLORS[p.marca] || '#9ca3af' }}>
                        {p.marca}
                      </span>
                    </td>
                    <td><span className="badge neutral">{p.categoria}</span></td>
                    <td className="code" style={{ color: 'var(--oz-green-400)' }}>
                      ${Number(p.precio_venta).toLocaleString('es-CO')}
                    </td>
                    <td className="code">{Number(p.tarifa_iva)}%</td>
                    <td>
                      <span className={`badge ${p.stock_actual <= p.stock_minimo ? 'red' : 'green'}`}>
                        {p.stock_actual} {p.stock_actual <= p.stock_minimo ? '⚠️' : ''}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${p.activo ? 'green' : 'neutral'}`}>
                        {p.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td>
                      <div className="action-btns">
                        <button className="btn-icon" title="Editar" onClick={() => { setEditing(p); setShowModal(true); }}>✏️</button>
                        {p.activo && <button className="btn-icon" title="Desactivar" onClick={() => handleDelete(p)}>🗑️</button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <ProductoFormModal
          producto={editing}
          onSave={handleSaveProducto}
          onClose={() => { setShowModal(false); setEditing(null); }}
        />
      )}
    </div>
  );
}

// ── Producto Form Modal ──

function ProductoFormModal({ producto, onSave, onClose }: {
  producto: Producto | null;
  onSave: (data: Record<string, any>) => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    sku: producto?.sku || '',
    nombre: producto?.nombre || '',
    descripcion: producto?.descripcion || '',
    categoria: producto?.categoria || 'Biocida',
    marca: producto?.marca || 'Superozono',
    unidad_medida: producto?.unidad_medida || 'Litro',
    contenido_neto: producto?.contenido_neto || '',
    precio_venta: producto?.precio_venta?.toString() || '',
    precio_costo: producto?.precio_costo?.toString() || '',
    tarifa_iva: producto?.tarifa_iva?.toString() || '19',
    stock_actual: producto?.stock_actual?.toString() || '0',
    stock_minimo: producto?.stock_minimo?.toString() || '5',
    registro_ica: producto?.registro_ica || '',
    notas: producto?.notas || '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      ...form,
      precio_venta: parseFloat(form.precio_venta) || 0,
      precio_costo: parseFloat(form.precio_costo) || 0,
      tarifa_iva: parseFloat(form.tarifa_iva) || 19,
      stock_actual: parseInt(form.stock_actual) || 0,
      stock_minimo: parseInt(form.stock_minimo) || 5,
    });
  };

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm(prev => ({ ...prev, [field]: e.target.value }));

  return (
    <Modal title={producto ? 'Editar Producto' : 'Nuevo Producto'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="modal-form">
        <div className="form-row">
          <div className="form-group">
            <label>SKU *</label>
            <input type="text" value={form.sku} onChange={set('sku')} required disabled={!!producto} placeholder="SOZ-001" />
          </div>
          <div className="form-group">
            <label>Marca *</label>
            <select value={form.marca} onChange={set('marca')}>
              {MARCAS.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>Nombre del Producto *</label>
          <input type="text" value={form.nombre} onChange={set('nombre')} required placeholder="Biocida Concentrado 1L" />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Categoría</label>
            <select value={form.categoria} onChange={set('categoria')}>
              {['Biocida', 'Fertilizante', 'Coadyuvante', 'Desinfectante', 'Otro'].map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Unidad</label>
            <select value={form.unidad_medida} onChange={set('unidad_medida')}>
              {['Litro', 'Galón', 'Kilo', 'Unidad', 'Caja', 'Caneca'].map(u => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Contenido</label>
            <input type="text" value={form.contenido_neto} onChange={set('contenido_neto')} placeholder="1L" />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Precio Venta *</label>
            <input type="number" value={form.precio_venta} onChange={set('precio_venta')} required min="0" step="100" />
          </div>
          <div className="form-group">
            <label>Precio Costo</label>
            <input type="number" value={form.precio_costo} onChange={set('precio_costo')} min="0" step="100" />
          </div>
          <div className="form-group">
            <label>IVA %</label>
            <select value={form.tarifa_iva} onChange={set('tarifa_iva')}>
              <option value="19">19%</option>
              <option value="5">5%</option>
              <option value="0">0% (Exento)</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Stock Actual</label>
            <input type="number" value={form.stock_actual} onChange={set('stock_actual')} min="0" />
          </div>
          <div className="form-group">
            <label>Stock Mínimo</label>
            <input type="number" value={form.stock_minimo} onChange={set('stock_minimo')} min="0" />
          </div>
          <div className="form-group">
            <label>Registro ICA</label>
            <input type="text" value={form.registro_ica} onChange={set('registro_ica')} placeholder="ICA-2024-XXX" />
          </div>
        </div>

        <div className="form-group">
          <label>Descripción</label>
          <textarea value={form.descripcion} onChange={set('descripcion')} rows={2} placeholder="Descripción del producto..." />
        </div>

        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancelar</button>
          <button type="submit" className="btn-primary">{producto ? 'Guardar Cambios' : 'Crear Producto'}</button>
        </div>
      </form>
    </Modal>
  );
}

// ══════════════════════════════════════════════════════════
// CLIENTES TAB
// ══════════════════════════════════════════════════════════

function ClientesTab() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Cliente | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);

  const fetchClientes = useCallback(() => {
    setLoading(true);
    ventasApi.getClientes()
      .then(res => setClientes(res.data))
      .catch(() => setToast({ msg: 'Error al cargar clientes', type: 'error' }))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchClientes(); }, [fetchClientes]);

  const filtered = clientes.filter(c =>
    c.razon_social.toLowerCase().includes(search.toLowerCase()) ||
    c.nit_cc.includes(search) ||
    (c.ciudad || '').toLowerCase().includes(search.toLowerCase())
  );

  const handleSaveCliente = async (data: Record<string, any>) => {
    try {
      if (editing) {
        await ventasApi.updateCliente(editing.id, data);
        setToast({ msg: 'Cliente actualizado', type: 'success' });
      } else {
        await ventasApi.createCliente(data as any);
        setToast({ msg: 'Cliente creado exitosamente', type: 'success' });
      }
      setShowModal(false);
      setEditing(null);
      fetchClientes();
    } catch (err: any) {
      setToast({ msg: err.response?.data?.detail || 'Error al guardar', type: 'error' });
    }
  };

  const handleDelete = async (c: Cliente) => {
    if (!confirm(`¿Desactivar "${c.razon_social}"?`)) return;
    try {
      await ventasApi.deleteCliente(c.id);
      setToast({ msg: 'Cliente desactivado', type: 'success' });
      fetchClientes();
    } catch {
      setToast({ msg: 'Error al desactivar', type: 'error' });
    }
  };

  return (
    <div className="fade-in">
      {toast && <Toast message={toast.msg} type={toast.type} onClose={() => setToast(null)} />}

      <div className="table-container">
        <div className="table-header">
          <div className="table-title">👥 Clientes Comerciales</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              className="form-search"
              type="text"
              placeholder="Buscar NIT, nombre o ciudad..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <div className="table-count">{filtered.length} clientes</div>
            <button className="btn-primary-sm" onClick={() => { setEditing(null); setShowModal(true); }}>
              + Nuevo Cliente
            </button>
          </div>
        </div>

        {loading ? (
          <div className="empty-state"><div className="empty-state-icon">⏳</div></div>
        ) : (
          <div style={{ maxHeight: 'calc(100vh - 280px)', overflowY: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>NIT / CC</th>
                  <th>Razón Social</th>
                  <th>Ciudad</th>
                  <th>Contacto</th>
                  <th>Lista</th>
                  <th>Cupo Crédito</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(c => (
                  <tr key={c.id} style={{ opacity: c.activo ? 1 : 0.5 }}>
                    <td className="code">{c.nit_cc}{c.dv ? `-${c.dv}` : ''}</td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{c.razon_social}</div>
                      {c.nombre_comercial && <div style={{ fontSize: '0.7rem', color: 'var(--neutral-500)' }}>{c.nombre_comercial}</div>}
                    </td>
                    <td>
                      <div>{c.ciudad || '—'}</div>
                      {c.departamento && <div style={{ fontSize: '0.7rem', color: 'var(--neutral-500)' }}>{c.departamento}</div>}
                    </td>
                    <td>
                      <div style={{ fontSize: '0.78rem' }}>{c.contacto_nombre || '—'}</div>
                      {c.celular && <div style={{ fontSize: '0.7rem', color: 'var(--neutral-500)' }}>{c.celular}</div>}
                    </td>
                    <td>
                      <span className={`badge ${c.lista_precios === 'Distribuidor' ? 'green' : c.lista_precios === 'Mayorista' ? 'blue' : 'neutral'}`}>
                        {c.lista_precios}
                      </span>
                    </td>
                    <td className="code" style={{ color: 'var(--blue-400)' }}>
                      ${Number(c.cupo_credito).toLocaleString('es-CO')}
                    </td>
                    <td>
                      <span className={`badge ${c.activo ? 'green' : 'neutral'}`}>
                        {c.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td>
                      <div className="action-btns">
                        <button className="btn-icon" title="Editar" onClick={() => { setEditing(c); setShowModal(true); }}>✏️</button>
                        {c.activo && <button className="btn-icon" title="Desactivar" onClick={() => handleDelete(c)}>🗑️</button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <ClienteFormModal
          cliente={editing}
          onSave={handleSaveCliente}
          onClose={() => { setShowModal(false); setEditing(null); }}
        />
      )}
    </div>
  );
}

// ── Cliente Form Modal ──

function ClienteFormModal({ cliente, onSave, onClose }: {
  cliente: Cliente | null;
  onSave: (data: Record<string, any>) => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    nit_cc: cliente?.nit_cc || '',
    dv: cliente?.dv || '',
    razon_social: cliente?.razon_social || '',
    nombre_comercial: cliente?.nombre_comercial || '',
    tipo_persona: cliente?.tipo_persona || 'Jurídica',
    regimen_iva: cliente?.regimen_iva || 'Responsable',
    direccion: cliente?.direccion || '',
    ciudad: cliente?.ciudad || '',
    departamento: cliente?.departamento || '',
    telefono: cliente?.telefono || '',
    celular: cliente?.celular || '',
    email: cliente?.email || '',
    contacto_nombre: cliente?.contacto_nombre || '',
    contacto_cargo: cliente?.contacto_cargo || '',
    lista_precios: cliente?.lista_precios || 'General',
    cupo_credito: cliente?.cupo_credito?.toString() || '0',
    dias_credito: cliente?.dias_credito?.toString() || '30',
    retiene_fuente: cliente?.retiene_fuente ?? false,
    retiene_iva: cliente?.retiene_iva ?? false,
    retiene_ica: cliente?.retiene_ica ?? false,
    tarifa_reteica: cliente?.tarifa_reteica != null ? String(cliente.tarifa_reteica) : '',
    notas: cliente?.notas || '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      ...form,
      cupo_credito: parseFloat(form.cupo_credito) || 0,
      dias_credito: parseInt(form.dias_credito) || 30,
      tarifa_reteica: form.retiene_ica && form.tarifa_reteica ? parseFloat(form.tarifa_reteica) : null,
    });
  };

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm(prev => ({ ...prev, [field]: e.target.value }));

  const setCheck = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(prev => ({ ...prev, [field]: e.target.checked }));

  return (
    <Modal title={cliente ? 'Editar Cliente' : 'Nuevo Cliente'} onClose={onClose} wide>
      <form onSubmit={handleSubmit} className="modal-form">
        <div className="form-row">
          <div className="form-group" style={{ flex: 2 }}>
            <label>NIT / CC *</label>
            <input type="text" value={form.nit_cc} onChange={set('nit_cc')} required disabled={!!cliente} placeholder="900123456" />
          </div>
          <div className="form-group" style={{ flex: 0.5 }}>
            <label>DV</label>
            <input type="text" value={form.dv} onChange={set('dv')} maxLength={1} placeholder="7" />
          </div>
          <div className="form-group" style={{ flex: 2 }}>
            <label>Tipo Persona</label>
            <select value={form.tipo_persona} onChange={set('tipo_persona')}>
              <option value="Jurídica">Jurídica</option>
              <option value="Natural">Natural</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>Razón Social *</label>
          <input type="text" value={form.razon_social} onChange={set('razon_social')} required />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Nombre Comercial</label>
            <input type="text" value={form.nombre_comercial} onChange={set('nombre_comercial')} />
          </div>
          <div className="form-group">
            <label>Régimen IVA</label>
            <select value={form.regimen_iva} onChange={set('regimen_iva')}>
              <option value="Responsable">Responsable</option>
              <option value="No responsable">No responsable</option>
              <option value="Gran contribuyente">Gran contribuyente</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>Dirección</label>
          <input type="text" value={form.direccion} onChange={set('direccion')} />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Ciudad</label>
            <input type="text" value={form.ciudad} onChange={set('ciudad')} />
          </div>
          <div className="form-group">
            <label>Departamento</label>
            <input type="text" value={form.departamento} onChange={set('departamento')} />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Teléfono</label>
            <input type="text" value={form.telefono} onChange={set('telefono')} />
          </div>
          <div className="form-group">
            <label>Celular</label>
            <input type="text" value={form.celular} onChange={set('celular')} />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={form.email} onChange={set('email')} />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Contacto</label>
            <input type="text" value={form.contacto_nombre} onChange={set('contacto_nombre')} />
          </div>
          <div className="form-group">
            <label>Cargo</label>
            <input type="text" value={form.contacto_cargo} onChange={set('contacto_cargo')} />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Lista de Precios</label>
            <select value={form.lista_precios} onChange={set('lista_precios')}>
              <option value="General">General</option>
              <option value="Distribuidor">Distribuidor</option>
              <option value="Mayorista">Mayorista</option>
            </select>
          </div>
          <div className="form-group">
            <label>Cupo Crédito</label>
            <input type="number" value={form.cupo_credito} onChange={set('cupo_credito')} min="0" step="1000000" />
          </div>
          <div className="form-group">
            <label>Días Crédito</label>
            <input type="number" value={form.dias_credito} onChange={set('dias_credito')} min="0" />
          </div>
        </div>

        <div className="form-group" style={{ border: '1px solid var(--neutral-800)', borderRadius: 'var(--radius-md)', padding: 14 }}>
          <label style={{ marginBottom: 8 }}>Perfil tributario — retenciones que practica el cliente</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 18 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontWeight: 400 }}>
              <input type="checkbox" checked={form.retiene_fuente} onChange={setCheck('retiene_fuente')} />
              <span>Practica ReteFuente</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontWeight: 400 }}>
              <input type="checkbox" checked={form.retiene_iva} onChange={setCheck('retiene_iva')} />
              <span>Practica ReteIVA</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontWeight: 400 }}>
              <input type="checkbox" checked={form.retiene_ica} onChange={setCheck('retiene_ica')} />
              <span>Practica ReteICA</span>
            </label>
          </div>
          {form.retiene_ica && (
            <div className="form-group" style={{ marginTop: 12, maxWidth: 220 }}>
              <label>Tarifa ReteICA (por mil)</label>
              <input type="number" value={form.tarifa_reteica} onChange={set('tarifa_reteica')}
                min="0" step="0.001" placeholder="Ej: 4.140" />
            </div>
          )}
          <div style={{ fontSize: '0.72rem', color: 'var(--neutral-500)', marginTop: 8 }}>
            Estos indicadores determinan qué retenciones se sugieren automáticamente al facturarle. Puedes ajustarlas manualmente en cada venta.
          </div>
        </div>

        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancelar</button>
          <button type="submit" className="btn-primary">{cliente ? 'Guardar Cambios' : 'Crear Cliente'}</button>
        </div>
      </form>
    </Modal>
  );
}

// ══════════════════════════════════════════════════════════
// FACTURAS TAB
// ══════════════════════════════════════════════════════════

function FacturasTab() {
  const [ventas, setVentas] = useState<Venta[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNueva, setShowNueva] = useState(false);
  const [showDetalle, setShowDetalle] = useState<Venta | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);

  const fetchVentas = useCallback(() => {
    setLoading(true);
    ventasApi.getVentas()
      .then(res => setVentas(res.data))
      .catch(() => setToast({ msg: 'Error al cargar ventas', type: 'error' }))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchVentas(); }, [fetchVentas]);

  const handleAnular = async (v: Venta) => {
    if (!confirm(`¿Anular venta ${v.numero}?`)) return;
    try {
      await ventasApi.anularVenta(v.id);
      setToast({ msg: `Venta ${v.numero} anulada`, type: 'success' });
      fetchVentas();
    } catch {
      setToast({ msg: 'Error al anular', type: 'error' });
    }
  };

  const handleConfirmar = async (v: Venta) => {
    try {
      await ventasApi.confirmarVenta(v.id);
      setToast({ msg: `Venta ${v.numero} confirmada`, type: 'success' });
      fetchVentas();
    } catch {
      setToast({ msg: 'Error al confirmar', type: 'error' });
    }
  };

  const estadoColor = (estado: string) => {
    switch (estado) {
      case 'Borrador': return 'neutral';
      case 'Confirmada': return 'blue';
      case 'Facturada': return 'green';
      case 'Anulada': return 'red';
      default: return 'neutral';
    }
  };

  const pagoColor = (estado: string) => {
    switch (estado) {
      case 'Pendiente': return 'amber';
      case 'Parcial': return 'blue';
      case 'Pagado': return 'green';
      default: return 'neutral';
    }
  };

  return (
    <div className="fade-in">
      {toast && <Toast message={toast.msg} type={toast.type} onClose={() => setToast(null)} />}

      <div className="table-container">
        <div className="table-header">
          <div className="table-title">🧾 Documentos de Venta</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <div className="table-count">{ventas.length} documentos</div>
            <button className="btn-primary-sm" onClick={() => setShowNueva(true)}>
              + Nueva Venta
            </button>
          </div>
        </div>

        {loading ? (
          <div className="empty-state"><div className="empty-state-icon">⏳</div></div>
        ) : ventas.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🧾</div>
            <div className="empty-state-text">No hay documentos de venta</div>
            <div className="empty-state-sub">Crea tu primera venta con el botón "+ Nueva Venta"</div>
          </div>
        ) : (
          <div style={{ maxHeight: 'calc(100vh - 280px)', overflowY: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>N° Documento</th>
                  <th>Fecha</th>
                  <th>Cliente</th>
                  <th>Subtotal</th>
                  <th>IVA</th>
                  <th>Total</th>
                  <th>Estado</th>
                  <th>Pago</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {ventas.map(v => (
                  <tr key={v.id} style={{ opacity: v.estado === 'Anulada' ? 0.5 : 1 }}>
                    <td className="code">{v.numero}</td>
                    <td>{new Date(v.fecha + 'T00:00:00').toLocaleDateString('es-CO')}</td>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: '0.82rem' }}>{v.cliente_razon_social}</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--neutral-500)' }}>NIT: {v.cliente_nit}</div>
                    </td>
                    <td className="code">${Number(v.subtotal).toLocaleString('es-CO')}</td>
                    <td className="code">${Number(v.iva_total).toLocaleString('es-CO')}</td>
                    <td className="code" style={{ color: 'var(--oz-green-400)', fontWeight: 700 }}>
                      ${Number(v.total).toLocaleString('es-CO')}
                    </td>
                    <td><span className={`badge ${estadoColor(v.estado)}`}>{v.estado}</span></td>
                    <td><span className={`badge ${pagoColor(v.estado_pago)}`}>{v.estado_pago}</span></td>
                    <td>
                      <div className="action-btns">
                        <button className="btn-icon" title="Ver detalle" onClick={() => setShowDetalle(v)}>👁️</button>
                        <button className="btn-icon" title="Imprimir / PDF" onClick={() => printFactura(v)}>🖨️</button>
                        {v.estado === 'Borrador' && (
                          <button className="btn-icon" title="Confirmar" onClick={() => handleConfirmar(v)}>✅</button>
                        )}
                        {v.estado !== 'Anulada' && (
                          <button className="btn-icon" title="Anular" onClick={() => handleAnular(v)}>❌</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showNueva && (
        <NuevaVentaModal
          onClose={() => setShowNueva(false)}
          onCreated={() => { setShowNueva(false); fetchVentas(); setToast({ msg: 'Venta creada exitosamente', type: 'success' }); }}
        />
      )}

      {showDetalle && (
        <Modal title={`Detalle — ${showDetalle.numero}`} onClose={() => setShowDetalle(null)} wide>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
            <button className="btn btn-primary" style={{ fontSize: '0.85rem' }} onClick={() => printFactura(showDetalle)}>
              🖨️ Imprimir / Guardar PDF
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <div>
              <div className="detail-label">Cliente</div>
              <div className="detail-value">{showDetalle.cliente_razon_social}</div>
              <div className="detail-sub">NIT: {showDetalle.cliente_nit}</div>
            </div>
            <div>
              <div className="detail-label">Fecha</div>
              <div className="detail-value">{new Date(showDetalle.fecha + 'T00:00:00').toLocaleDateString('es-CO', { dateStyle: 'long' })}</div>
              {showDetalle.vendedor && <div className="detail-sub">Vendedor: {showDetalle.vendedor}</div>}
            </div>
          </div>

          <table className="data-table" style={{ marginBottom: 16 }}>
            <thead>
              <tr>
                <th>SKU</th>
                <th>Producto</th>
                <th>Cant.</th>
                <th>P. Unit.</th>
                <th>Desc%</th>
                <th>IVA</th>
                <th>Total Línea</th>
              </tr>
            </thead>
            <tbody>
              {showDetalle.detalles.map(d => (
                <tr key={d.id}>
                  <td className="code">{d.producto_sku}</td>
                  <td>{d.producto_nombre}</td>
                  <td>{Number(d.cantidad)}</td>
                  <td className="code">${Number(d.precio_unitario).toLocaleString('es-CO')}</td>
                  <td>{Number(d.descuento_porcentaje)}%</td>
                  <td>{Number(d.iva_porcentaje)}%</td>
                  <td className="code" style={{ fontWeight: 600 }}>${Number(d.total_linea).toLocaleString('es-CO')}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="venta-totales">
            <div className="total-row"><span>Subtotal</span><span>${Number(showDetalle.subtotal).toLocaleString('es-CO')}</span></div>
            {Number(showDetalle.descuento_total) > 0 && <div className="total-row"><span>Descuentos</span><span>-${Number(showDetalle.descuento_total).toLocaleString('es-CO')}</span></div>}
            <div className="total-row"><span>Base Gravable</span><span>${Number(showDetalle.base_gravable).toLocaleString('es-CO')}</span></div>
            <div className="total-row"><span>IVA</span><span>${Number(showDetalle.iva_total).toLocaleString('es-CO')}</span></div>
            {Number(showDetalle.retefuente) > 0 && <div className="total-row"><span>ReteFuente</span><span>-${Number(showDetalle.retefuente).toLocaleString('es-CO')}</span></div>}
            {Number(showDetalle.reteiva) > 0 && <div className="total-row"><span>ReteIVA</span><span>-${Number(showDetalle.reteiva).toLocaleString('es-CO')}</span></div>}
            <div className="total-row total-final"><span>TOTAL</span><span>${Number(showDetalle.total).toLocaleString('es-CO')}</span></div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ── Nueva Venta Modal ──

function NuevaVentaModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [clienteId, setClienteId] = useState('');
  const [fecha, setFecha] = useState(new Date().toISOString().split('T')[0]);
  const [vendedor, setVendedor] = useState('');
  const [observaciones, setObservaciones] = useState('');
  const [lineas, setLineas] = useState<VentaDetalleInput[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    ventasApi.getClientes().then(r => setClientes(r.data)).catch(() => { });
    ventasApi.getProductos().then(r => setProductos(r.data.filter(p => p.activo))).catch(() => { });
  }, []);

  const addLinea = () => {
    setLineas(prev => [...prev, {
      producto_id: 0,
      cantidad: 1,
      precio_unitario: 0,
      descuento_porcentaje: 0,
      iva_porcentaje: 19,
    }]);
  };

  const updateLinea = (idx: number, field: string, value: any) => {
    setLineas(prev => prev.map((l, i) => {
      if (i !== idx) return l;
      const updated = { ...l, [field]: value };
      // Auto-fill price and IVA when product changes
      if (field === 'producto_id') {
        const prod = productos.find(p => p.id === Number(value));
        if (prod) {
          updated.precio_unitario = Number(prod.precio_venta);
          updated.iva_porcentaje = Number(prod.tarifa_iva);
        }
      }
      return updated;
    }));
  };

  const removeLinea = (idx: number) => {
    setLineas(prev => prev.filter((_, i) => i !== idx));
  };

  const calcTotalLinea = (l: VentaDetalleInput) => {
    const sub = l.cantidad * l.precio_unitario;
    const desc = sub * (l.descuento_porcentaje / 100);
    const base = sub - desc;
    const iva = base * (l.iva_porcentaje / 100);
    return base + iva;
  };

  const totalGeneral = lineas.reduce((sum, l) => sum + calcTotalLinea(l), 0);

  const handleSubmit = async () => {
    if (!clienteId) { setError('Selecciona un cliente'); return; }
    if (lineas.length === 0) { setError('Agrega al menos una línea de producto'); return; }
    if (lineas.some(l => !l.producto_id)) { setError('Selecciona un producto en cada línea'); return; }

    setSaving(true);
    setError('');
    try {
      await ventasApi.createVenta({
        fecha,
        cliente_id: parseInt(clienteId),
        vendedor: vendedor || undefined,
        observaciones: observaciones || undefined,
        detalles: lineas,
      });
      onCreated();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al crear la venta');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="🧾 Nueva Venta" onClose={onClose} wide>
      <div className="modal-form">
        {error && <div className="form-error fade-in">{error}</div>}

        <div className="form-row">
          <div className="form-group" style={{ flex: 3 }}>
            <label>Cliente *</label>
            <select value={clienteId} onChange={e => setClienteId(e.target.value)}>
              <option value="">— Seleccionar cliente —</option>
              {clientes.filter(c => c.activo).map(c => (
                <option key={c.id} value={c.id}>{c.razon_social} ({c.nit_cc})</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Fecha</label>
            <input type="date" value={fecha} onChange={e => setFecha(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Vendedor</label>
            <input type="text" value={vendedor} onChange={e => setVendedor(e.target.value)} placeholder="Nombre" />
          </div>
        </div>

        {/* Líneas de detalle */}
        <div style={{ marginTop: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <label style={{ fontWeight: 600, color: 'var(--neutral-200)' }}>Líneas de Detalle</label>
            <button type="button" className="btn-primary-sm" onClick={addLinea}>+ Agregar Línea</button>
          </div>

          {lineas.length === 0 ? (
            <div className="empty-state" style={{ padding: 20 }}>
              <div className="empty-state-text" style={{ fontSize: '0.8rem' }}>Agrega productos a esta venta</div>
            </div>
          ) : (
            <div className="venta-lineas">
              {lineas.map((l, idx) => (
                <div key={idx} className="venta-linea fade-in">
                  <div className="form-row" style={{ gap: 6 }}>
                    <div className="form-group" style={{ flex: 3 }}>
                      <select
                        value={l.producto_id}
                        onChange={e => updateLinea(idx, 'producto_id', Number(e.target.value))}
                      >
                        <option value={0}>— Producto —</option>
                        {productos.map(p => (
                          <option key={p.id} value={p.id}>
                            [{p.sku}] {p.nombre} — ${Number(p.precio_venta).toLocaleString('es-CO')}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="form-group" style={{ flex: 0.7 }}>
                      <input
                        type="number" min="1" placeholder="Cant."
                        value={l.cantidad}
                        onChange={e => updateLinea(idx, 'cantidad', Number(e.target.value))}
                      />
                    </div>
                    <div className="form-group" style={{ flex: 1 }}>
                      <input
                        type="number" min="0" step="100" placeholder="P. Unit."
                        value={l.precio_unitario}
                        onChange={e => updateLinea(idx, 'precio_unitario', Number(e.target.value))}
                      />
                    </div>
                    <div className="form-group" style={{ flex: 0.6 }}>
                      <input
                        type="number" min="0" max="100" step="0.5" placeholder="Desc%"
                        value={l.descuento_porcentaje}
                        onChange={e => updateLinea(idx, 'descuento_porcentaje', Number(e.target.value))}
                      />
                    </div>
                    <div className="linea-total" style={{ flex: 1, textAlign: 'right' }}>
                      <span className="code" style={{ color: 'var(--oz-green-400)', fontWeight: 700 }}>
                        ${calcTotalLinea(l).toLocaleString('es-CO', { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                    <button type="button" className="btn-icon-danger" onClick={() => removeLinea(idx)} title="Eliminar línea">×</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {lineas.length > 0 && (
          <div className="venta-total-bar">
            <span>Total Estimado</span>
            <span className="code" style={{ fontSize: '1.2rem', color: 'var(--oz-green-400)', fontWeight: 800 }}>
              ${totalGeneral.toLocaleString('es-CO', { maximumFractionDigits: 0 })}
            </span>
          </div>
        )}

        <div className="form-group" style={{ marginTop: 12 }}>
          <label>Observaciones</label>
          <textarea value={observaciones} onChange={e => setObservaciones(e.target.value)} rows={2} placeholder="Notas de la venta..." />
        </div>

        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancelar</button>
          <button
            type="button"
            className="btn-primary"
            onClick={handleSubmit}
            disabled={saving}
          >
            {saving ? 'Creando...' : 'Crear Documento de Venta'}
          </button>
        </div>
      </div>
    </Modal>
  );
}

// ══════════════════════════════════════════════════════════
// MAIN VENTAS VIEW
// ══════════════════════════════════════════════════════════

export default function VentasView() {
  const [activeTab, setActiveTab] = useState<VentasTab>('dashboard');

  const TABS: { id: VentasTab; icon: string; label: string }[] = [
    { id: 'dashboard', icon: '📊', label: 'Dashboard' },
    { id: 'productos', icon: '📦', label: 'Productos' },
    { id: 'clientes', icon: '👥', label: 'Clientes' },
    { id: 'facturas', icon: '🧾', label: 'Facturas' },
  ];

  return (
    <div className="ventas-module fade-in">
      {/* Tab Navigation */}
      <div className="tabs-bar">
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`tab-item ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'dashboard' && <VentasDashboardTab />}
        {activeTab === 'productos' && <ProductosTab />}
        {activeTab === 'clientes' && <ClientesTab />}
        {activeTab === 'facturas' && <FacturasTab />}
      </div>
    </div>
  );
}
