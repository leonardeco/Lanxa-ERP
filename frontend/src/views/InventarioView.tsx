import { useState, useEffect, useCallback } from 'react';
import {
  inventarioApi,
  type MovimientoInventario,
  type InventarioDashboard,
  type PreviewImport,
  type Lote,
  type EstadoLote,
} from '../services/inventarioApi';
import { ventasApi, type Producto } from '../services/ventasApi';
import { useAuth } from '../contexts/auth';
import Toast from '../components/Toast';
import ErrorState from '../components/ErrorState';

type InventarioTab = 'dashboard' | 'productos' | 'movimientos' | 'lotes' | 'ajuste' | 'importar';

const LOTE_ESTADO: Record<EstadoLote, { label: string; bg: string; color: string }> = {
  vigente: { label: 'Vigente', bg: '#dcfce7', color: '#16a34a' },
  por_vencer: { label: 'Por vencer', bg: '#fef3c7', color: '#b45309' },
  vencido: { label: 'Vencido', bg: '#fee2e2', color: '#dc2626' },
  sin_vencimiento: { label: 'Sin vencimiento', bg: '#f1f5f9', color: '#64748b' },
};

const COP = (n: number | string) =>
  Number(n).toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 0 });

const TIPO_COLOR: Record<string, string> = {
  Entrada: '#22c55e',
  Salida: '#ef4444',
  'Ajuste positivo': '#3b82f6',
  'Ajuste negativo': '#f59e0b',
};


// ══════════════════════════════════════════════════════════
// DASHBOARD TAB
// ══════════════════════════════════════════════════════════

function InventarioDashboardTab() {
  const [stats, setStats] = useState<InventarioDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    setLoading(true);
    inventarioApi.getDashboard()
      .then(r => setStats(r.data))
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, [intento]);

  if (loading) return <div className="loading-spinner" style={{ margin: '60px auto' }} />;
  if (!stats) return <ErrorState mensaje="Error al cargar el dashboard de inventario" onRetry={() => setIntento(i => i + 1)} />;

  return (
    <div className="fade-in">
      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
        <div className="kpi-card">
          <div className="kpi-label">Valor total de inventario</div>
          <div className="kpi-value">{COP(stats.valor_total_inventario)}</div>
          <div className="kpi-change">stock × precio de costo</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Productos con stock bajo</div>
          <div className="kpi-value" style={{ color: stats.productos_stock_bajo > 0 ? '#ef4444' : undefined }}>
            {stats.productos_stock_bajo}
          </div>
          <div className="kpi-change">stock ≤ stock mínimo</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Movimientos este mes</div>
          <div className="kpi-value">{stats.movimientos_mes}</div>
          <div className="kpi-change">entradas, salidas y ajustes</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Lotes por vencer</div>
          <div className="kpi-value" style={{ color: stats.lotes_por_vencer > 0 ? '#b45309' : undefined }}>
            {stats.lotes_por_vencer}
          </div>
          <div className="kpi-change">vencen dentro de 30 días</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Lotes vencidos</div>
          <div className="kpi-value" style={{ color: stats.lotes_vencidos > 0 ? '#dc2626' : undefined }}>
            {stats.lotes_vencidos}
          </div>
          <div className="kpi-change">con existencia y ya vencidos</div>
        </div>
      </div>

      {stats.top_productos_por_valor.length > 0 && (
        <div className="table-card">
          <div className="table-card-header">
            <h3>Top Productos por Valor en Inventario</h3>
          </div>
          <table className="erp-table">
            <thead>
              <tr>
                <th>#</th>
                <th>SKU</th>
                <th>Producto</th>
                <th style={{ textAlign: 'right' }}>Valor en inventario</th>
              </tr>
            </thead>
            <tbody>
              {stats.top_productos_por_valor.map((p, i) => (
                <tr key={i}>
                  <td><span className="badge" style={{ background: '#2563eb', color: '#fff' }}>{i + 1}</span></td>
                  <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{p.sku}</td>
                  <td>{p.producto}</td>
                  <td style={{ textAlign: 'right', fontWeight: 700 }}>{COP(p.valor)}</td>
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
// PRODUCTOS TAB (solo lectura — el CRUD vive en Ventas)
// ══════════════════════════════════════════════════════════

function ProductosStockTab() {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState('');
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    setLoading(true);
    setError(false);
    ventasApi.getProductos().then(r => setProductos(r.data)).catch(() => setError(true)).finally(() => setLoading(false));
  }, [intento]);

  if (error) return <ErrorState mensaje="No se pudo cargar el stock de productos" onRetry={() => setIntento(i => i + 1)} />;

  const filtered = productos.filter(p =>
    p.nombre.toLowerCase().includes(search.toLowerCase()) ||
    p.sku.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="fade-in">
      <div className="table-card">
        <div className="table-card-header">
          <h3>Stock por Producto ({filtered.length})</h3>
          <input
            className="search-input"
            placeholder="Buscar por nombre o SKU..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        {loading ? <div className="loading-spinner" style={{ margin: '40px auto' }} /> : (
          <table className="erp-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Producto</th>
                <th>Marca</th>
                <th style={{ textAlign: 'right' }}>Stock actual</th>
                <th style={{ textAlign: 'right' }}>Stock mínimo</th>
                <th style={{ textAlign: 'right' }}>Costo unit.</th>
                <th style={{ textAlign: 'right' }}>Valor en inventario</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={7} style={{ textAlign: 'center', color: '#888', padding: 32 }}>Sin productos</td></tr>
              ) : filtered.map(p => (
                <tr key={p.id}>
                  <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{p.sku}</td>
                  <td>{p.nombre}</td>
                  <td>{p.marca}</td>
                  <td style={{ textAlign: 'right' }}>
                    <span className="badge" style={{
                      background: p.stock_actual <= p.stock_minimo ? '#fee2e2' : '#dcfce7',
                      color: p.stock_actual <= p.stock_minimo ? '#dc2626' : '#16a34a',
                    }}>
                      {p.stock_actual} {p.stock_actual <= p.stock_minimo ? '⚠️' : ''}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>{p.stock_minimo}</td>
                  <td style={{ textAlign: 'right' }}>{COP(p.precio_costo ?? 0)}</td>
                  <td style={{ textAlign: 'right', fontWeight: 700 }}>{COP(p.stock_actual * Number(p.precio_costo ?? 0))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <p style={{ fontSize: 11, color: '#888', marginTop: 8 }}>
        Para crear o editar productos, ve a <strong>Ventas & Comercial → Productos</strong>.
      </p>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// MOVIMIENTOS TAB (KARDEX)
// ══════════════════════════════════════════════════════════

function MovimientosTab() {
  const [movimientos, setMovimientos] = useState<MovimientoInventario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [productoFiltro, setProductoFiltro] = useState('');
  const [tipoFiltro, setTipoFiltro] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setError(false);
    inventarioApi.getMovimientos()
      .then(r => setMovimientos(r.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  if (error) return <ErrorState mensaje="No se pudo cargar el kardex de movimientos" onRetry={load} />;

  const filtered = movimientos.filter(m =>
    (!productoFiltro || (m.producto_nombre ?? '').toLowerCase().includes(productoFiltro.toLowerCase()) || (m.producto_sku ?? '').toLowerCase().includes(productoFiltro.toLowerCase())) &&
    (!tipoFiltro || m.tipo === tipoFiltro)
  );

  return (
    <div className="fade-in">
      <div className="table-card">
        <div className="table-card-header">
          <h3>Kardex de Movimientos ({filtered.length})</h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              className="search-input"
              placeholder="Buscar por producto o SKU..."
              value={productoFiltro}
              onChange={e => setProductoFiltro(e.target.value)}
            />
            <select className="form-select" style={{ margin: 0 }} value={tipoFiltro} onChange={e => setTipoFiltro(e.target.value)}>
              <option value="">Todos los tipos</option>
              <option value="Entrada">Entrada</option>
              <option value="Salida">Salida</option>
              <option value="Ajuste positivo">Ajuste positivo</option>
              <option value="Ajuste negativo">Ajuste negativo</option>
            </select>
          </div>
        </div>
        {loading ? <div className="loading-spinner" style={{ margin: '40px auto' }} /> : (
          <table className="erp-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Producto</th>
                <th>Tipo</th>
                <th>Origen</th>
                <th style={{ textAlign: 'right' }}>Cantidad</th>
                <th style={{ textAlign: 'right' }}>Stock antes</th>
                <th style={{ textAlign: 'right' }}>Stock después</th>
                <th>Motivo</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={8} style={{ textAlign: 'center', color: '#888', padding: 32 }}>Sin movimientos registrados</td></tr>
              ) : filtered.map(m => (
                <tr key={m.id}>
                  <td style={{ fontSize: 11 }}>{new Date(m.fecha).toLocaleString('es-CO')}</td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{m.producto_nombre ?? '—'}</div>
                    <div style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>{m.producto_sku}</div>
                  </td>
                  <td><span className="badge" style={{ background: '#f0f4ff', color: TIPO_COLOR[m.tipo] ?? '#555' }}>{m.tipo}</span></td>
                  <td style={{ fontSize: 11, color: '#666' }}>{m.origen}</td>
                  <td style={{ textAlign: 'right' }}>{Number(m.cantidad)}</td>
                  <td style={{ textAlign: 'right', color: '#888' }}>{m.stock_antes}</td>
                  <td style={{ textAlign: 'right', fontWeight: 700 }}>{m.stock_despues}</td>
                  <td style={{ fontSize: 11, color: '#666' }}>{m.motivo ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// LOTES TAB (existencias por lote + alertas de vencimiento)
// ══════════════════════════════════════════════════════════

function LotesTab() {
  const [lotes, setLotes] = useState<Lote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState('');
  const [estadoFiltro, setEstadoFiltro] = useState<EstadoLote | ''>('');

  const load = useCallback(() => {
    setLoading(true);
    setError(false);
    inventarioApi.getLotes(estadoFiltro ? { estado: estadoFiltro } : undefined)
      .then(r => setLotes(r.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [estadoFiltro]);

  useEffect(() => { load(); }, [load]);

  if (error) return <ErrorState mensaje="No se pudieron cargar los lotes" onRetry={load} />;

  const filtered = lotes.filter(l =>
    !search ||
    (l.producto_nombre ?? '').toLowerCase().includes(search.toLowerCase()) ||
    (l.producto_sku ?? '').toLowerCase().includes(search.toLowerCase()) ||
    l.codigo_lote.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="fade-in">
      <div className="table-card">
        <div className="table-card-header">
          <h3>Existencias por Lote ({filtered.length})</h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              className="search-input"
              placeholder="Buscar por producto, SKU o lote..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <select
              className="form-select"
              style={{ margin: 0 }}
              value={estadoFiltro}
              onChange={e => setEstadoFiltro(e.target.value as EstadoLote | '')}
            >
              <option value="">Todos los estados</option>
              <option value="por_vencer">Por vencer (30 días)</option>
              <option value="vencido">Vencidos</option>
              <option value="vigente">Vigentes</option>
              <option value="sin_vencimiento">Sin vencimiento</option>
            </select>
          </div>
        </div>
        {loading ? <div className="loading-spinner" style={{ margin: '40px auto' }} /> : (
          <table className="erp-table">
            <thead>
              <tr>
                <th>Producto</th>
                <th>Lote</th>
                <th>Vencimiento</th>
                <th style={{ textAlign: 'right' }}>Existencia</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={5} style={{ textAlign: 'center', color: '#888', padding: 32 }}>Sin lotes con existencia</td></tr>
              ) : filtered.map(l => {
                const est = LOTE_ESTADO[l.estado];
                return (
                  <tr key={l.id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{l.producto_nombre ?? '—'}</div>
                      <div style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>{l.producto_sku}</div>
                    </td>
                    <td style={{ fontFamily: 'monospace' }}>{l.codigo_lote}</td>
                    <td style={{ fontSize: 12 }}>
                      {l.fecha_vencimiento ? new Date(l.fecha_vencimiento + 'T00:00:00').toLocaleDateString('es-CO') : '—'}
                      {typeof l.dias_para_vencer === 'number' && (
                        <span style={{ fontSize: 10, color: '#888', display: 'block' }}>
                          {l.dias_para_vencer < 0
                            ? `hace ${Math.abs(l.dias_para_vencer)} d`
                            : `en ${l.dias_para_vencer} d`}
                        </span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>{Number(l.cantidad_actual)}</td>
                    <td><span className="badge" style={{ background: est.bg, color: est.color }}>{est.label}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
      <p style={{ fontSize: 11, color: '#888', marginTop: 8 }}>
        Las salidas de los productos con control de lote se despachan por <strong>FEFO</strong> (primero en vencer, primero en salir); los lotes vencidos no se venden.
      </p>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// AJUSTE MANUAL TAB
// ══════════════════════════════════════════════════════════

function AjusteTab({ onToast, onSaved }: { onToast: (msg: string, type: 'success' | 'error') => void; onSaved: () => void }) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [form, setForm] = useState({ producto_id: 0, tipo: 'Entrada' as 'Entrada' | 'Salida', cantidad: 1, motivo: '', codigo_lote: '', fecha_vencimiento: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    ventasApi.getProductos().then(r => setProductos(r.data))
      .catch(() => onToast('No se pudieron cargar los productos para el ajuste', 'error'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const F = (field: keyof typeof form, value: string | number) =>
    setForm(f => ({ ...f, [field]: value }));

  const productoSel = productos.find(p => p.id === Number(form.producto_id));
  const conLote = !!productoSel?.controla_lote;
  const pideLoteEntrada = conLote && form.tipo === 'Entrada';

  const handleSubmit = async () => {
    if (!form.producto_id) { onToast('Selecciona un producto', 'error'); return; }
    if (!form.cantidad || form.cantidad <= 0) { onToast('La cantidad debe ser mayor a cero', 'error'); return; }
    if (pideLoteEntrada && !form.codigo_lote.trim()) {
      onToast('Este producto controla lote: el código de lote es obligatorio', 'error');
      return;
    }
    setSaving(true);
    try {
      await inventarioApi.crearAjuste({
        producto_id: Number(form.producto_id),
        tipo: form.tipo,
        cantidad: Number(form.cantidad),
        motivo: form.motivo || undefined,
        codigo_lote: pideLoteEntrada ? form.codigo_lote.trim() : undefined,
        fecha_vencimiento: pideLoteEntrada && form.fecha_vencimiento ? form.fecha_vencimiento : undefined,
      });
      onToast('Ajuste registrado correctamente', 'success');
      setForm({ producto_id: 0, tipo: 'Entrada', cantidad: 1, motivo: '', codigo_lote: '', fecha_vencimiento: '' });
      onSaved();
    } catch {
      onToast('Error registrando el ajuste', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="table-card" style={{ maxWidth: 500 }}>
        <div className="table-card-header">
          <h3>Ajuste Manual de Inventario</h3>
        </div>
        <div style={{ padding: '0 20px 20px' }}>
          <div className="form-group">
            <label>Producto *</label>
            <select className="form-select" value={form.producto_id} onChange={e => F('producto_id', Number(e.target.value))}>
              <option value={0}>— Seleccionar producto —</option>
              {productos.map(p => (
                <option key={p.id} value={p.id}>{p.sku} — {p.nombre} (stock: {p.stock_actual})</option>
              ))}
            </select>
          </div>
          <div className="form-grid-2">
            <div className="form-group">
              <label>Tipo de ajuste *</label>
              <select className="form-select" value={form.tipo} onChange={e => F('tipo', e.target.value as 'Entrada' | 'Salida')}>
                <option value="Entrada">Entrada (suma stock)</option>
                <option value="Salida">Salida (resta stock)</option>
              </select>
            </div>
            <div className="form-group">
              <label>Cantidad *</label>
              <input className="form-input" type="number" min={1} value={form.cantidad} onChange={e => F('cantidad', Number(e.target.value))} />
            </div>
          </div>
          {pideLoteEntrada && (
            <div className="form-grid-2">
              <div className="form-group">
                <label>Código de lote *</label>
                <input className="form-input" value={form.codigo_lote} onChange={e => F('codigo_lote', e.target.value)} placeholder="Ej: L-2026-07" />
              </div>
              <div className="form-group">
                <label>Fecha de vencimiento</label>
                <input className="form-input" type="date" value={form.fecha_vencimiento} onChange={e => F('fecha_vencimiento', e.target.value)} />
              </div>
            </div>
          )}
          {conLote && form.tipo === 'Salida' && (
            <p style={{ fontSize: 12, color: '#b45309', margin: '0 0 8px' }}>
              ⓘ Producto con control de lote: la salida se descuenta por <strong>FEFO</strong> (primero en vencer, primero en salir).
            </p>
          )}
          <div className="form-group">
            <label>Motivo</label>
            <input className="form-input" value={form.motivo} onChange={e => F('motivo', e.target.value)} placeholder="Ej: conteo físico, merma, devolución..." />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
            <button className="btn-primary" onClick={handleSubmit} disabled={saving}>
              {saving ? 'Guardando...' : '💾 Registrar ajuste'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// IMPORTAR INVENTARIO INICIAL TAB
// ══════════════════════════════════════════════════════════

function ImportarTab({ onToast, onSaved }: { onToast: (msg: string, type: 'success' | 'error') => void; onSaved: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewImport | null>(null);
  const [validando, setValidando] = useState(false);
  const [importando, setImportando] = useState(false);

  const descargar = async () => {
    try {
      const res = await inventarioApi.descargarPlantilla();
      const url = URL.createObjectURL(res.data as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'plantilla-inventario-inicial.xlsx';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      onToast('No se pudo descargar la plantilla', 'error');
    }
  };

  const onPick = (f: File | null) => {
    setFile(f);
    setPreview(null);
  };

  const validar = async () => {
    if (!file) return;
    setValidando(true);
    try {
      const res = await inventarioApi.validarImport(file);
      setPreview(res.data);
    } catch {
      onToast('No se pudo leer el archivo. Usa la plantilla .xlsx.', 'error');
      setPreview(null);
    } finally {
      setValidando(false);
    }
  };

  const confirmar = async () => {
    if (!file) return;
    setImportando(true);
    try {
      const res = await inventarioApi.confirmarImport(file);
      onToast(`Importados ${res.data.importados} productos`, 'success');
      setFile(null);
      setPreview(null);
      onSaved();
    } catch {
      onToast('No se pudo completar la importación', 'error');
    } finally {
      setImportando(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="table-card" style={{ maxWidth: 820 }}>
        <div className="table-card-header">
          <h3>Importar Inventario Inicial</h3>
          <button className="btn-primary" onClick={descargar}>⬇️ Descargar plantilla</button>
        </div>
        <div style={{ padding: '0 20px 20px' }}>
          <p style={{ fontSize: 13, color: '#666', marginTop: 0 }}>
            Descarga la plantilla, llénala con los productos reales y súbela aquí. Primero se
            valida (sin guardar nada); si no hay errores podrás confirmar la importación.
          </p>
          <div className="form-group">
            <label>Archivo .xlsx</label>
            <input
              className="form-input"
              type="file"
              accept=".xlsx"
              onChange={e => onPick(e.target.files?.[0] ?? null)}
            />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn-primary" onClick={validar} disabled={!file || validando}>
              {validando ? 'Validando...' : '🔍 Validar'}
            </button>
            {preview && preview.errores.length === 0 && preview.validas > 0 && (
              <button
                className="btn-primary"
                onClick={confirmar}
                disabled={importando}
                style={{ background: '#16a34a' }}
              >
                {importando ? 'Importando...' : `✅ Confirmar importación (${preview.validas})`}
              </button>
            )}
          </div>

          {preview && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 13, marginBottom: 8 }}>
                Filas: <strong>{preview.total_filas}</strong> · Válidas:{' '}
                <strong style={{ color: '#16a34a' }}>{preview.validas}</strong> · Errores:{' '}
                <strong style={{ color: preview.errores.length ? '#dc2626' : '#16a34a' }}>
                  {preview.errores.length}
                </strong>
              </div>
              {preview.errores.length === 0 ? (
                <div style={{ color: '#16a34a', fontSize: 13 }}>
                  ✅ Sin errores. Puedes confirmar la importación.
                </div>
              ) : (
                <table className="erp-table">
                  <thead>
                    <tr><th>Fila</th><th>Columna</th><th>Error</th></tr>
                  </thead>
                  <tbody>
                    {preview.errores.map((e, i) => (
                      <tr key={i}>
                        <td>{e.fila}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{e.columna}</td>
                        <td style={{ color: '#dc2626' }}>{e.mensaje}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════

export default function InventarioView() {
  const { user } = useAuth();
  const puedeAjustar = user?.rol === 'Admin' || user?.rol === 'Administradora';

  const [tab, setTab] = useState<InventarioTab>('dashboard');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type });
  }, []);

  const TABS: { id: InventarioTab; label: string }[] = [
    { id: 'dashboard', label: '📊 Dashboard' },
    { id: 'productos', label: '📦 Productos' },
    { id: 'lotes', label: '🏷️ Lotes' },
    { id: 'movimientos', label: '📋 Movimientos' },
    ...(puedeAjustar ? [
      { id: 'ajuste' as InventarioTab, label: '+ Ajuste Manual' },
      { id: 'importar' as InventarioTab, label: '📥 Importar' },
    ] : []),
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

      {tab === 'dashboard' && <InventarioDashboardTab key={`dash-${refreshKey}`} />}
      {tab === 'productos' && <ProductosStockTab key={`prod-${refreshKey}`} />}
      {tab === 'lotes' && <LotesTab key={`lotes-${refreshKey}`} />}
      {tab === 'movimientos' && <MovimientosTab key={`mov-${refreshKey}`} />}
      {tab === 'ajuste' && puedeAjustar && (
        <AjusteTab onToast={showToast} onSaved={() => setRefreshKey(k => k + 1)} />
      )}
      {tab === 'importar' && puedeAjustar && (
        <ImportarTab onToast={showToast} onSaved={() => setRefreshKey(k => k + 1)} />
      )}
    </div>
  );
}
