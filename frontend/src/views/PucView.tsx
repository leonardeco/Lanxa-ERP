import { useState, useEffect, useCallback } from 'react';
import { contabilidadApi, type CuentaPUC } from '../services/contabilidadApi';
import { useAuth } from '../contexts/AuthContext';
import Toast from '../components/Toast';
import Modal from '../components/Modal';
import Skeleton from '../components/Skeleton';

const CLASE_COLORS: Record<string, string> = {
  Activo: 'green', Pasivo: 'blue', Patrimonio: 'purple',
  Ingreso: 'amber', Gasto: 'red', Costo: 'cyan',
};

const CLASES = ['Activo', 'Pasivo', 'Patrimonio', 'Ingreso', 'Gasto', 'Costo'];
const NATURALEZAS = ['Débito', 'Crédito'];
const NIVELES = ['Clase', 'Grupo', 'Cuenta', 'Subcuenta', 'Auxiliar'];

function CuentaModal({ cuenta, onSave, onClose }: {
  cuenta: Partial<CuentaPUC> | null;
  onSave: (data: any) => Promise<void>;
  onClose: () => void;
}) {
  const isEdit = cuenta?.id != null;
  const [codigo, setCodigo] = useState(cuenta?.codigo_puc ?? '');
  const [nombre, setNombre] = useState(cuenta?.nombre ?? '');
  const [clase, setClase] = useState(cuenta?.clase ?? 'Activo');
  const [naturaleza, setNaturaleza] = useState(cuenta?.naturaleza ?? 'Débito');
  const [nivel, setNivel] = useState(cuenta?.nivel ?? 'Subcuenta');
  const [tercero, setTercero] = useState(cuenta?.requiere_tercero ?? false);
  const [cc, setCc] = useState(cuenta?.requiere_centro_costo ?? false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nombre.trim()) { setError('El nombre es obligatorio'); return; }
    if (!isEdit && !codigo.trim()) { setError('El código PUC es obligatorio'); return; }
    setError(''); setSaving(true);
    try {
      await onSave(isEdit
        ? { nombre: nombre.trim(), requiere_tercero: tercero, requiere_centro_costo: cc }
        : { codigo_puc: codigo.trim(), nombre: nombre.trim(), clase, naturaleza, nivel, requiere_tercero: tercero, requiere_centro_costo: cc, activo: true }
      );
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={isEdit ? 'Editar cuenta PUC' : 'Nueva cuenta PUC'} onClose={onClose}>
          <form onSubmit={handleSubmit} className="form-vertical">
            {!isEdit && (
              <div className="form-group">
                <label className="form-label">Código PUC *</label>
                <input className="form-input" value={codigo} onChange={e => setCodigo(e.target.value)} placeholder="Ej: 1105" />
              </div>
            )}
            {isEdit && (
              <div className="form-group">
                <label className="form-label">Código PUC</label>
                <input className="form-input" value={cuenta?.codigo_puc ?? ''} disabled style={{ opacity: 0.5 }} />
              </div>
            )}
            <div className="form-group">
              <label className="form-label">Nombre *</label>
              <input className="form-input" value={nombre} onChange={e => setNombre(e.target.value)} placeholder="Nombre de la cuenta" />
            </div>
            {!isEdit && (
              <>
                <div className="form-grid-2">
                  <div className="form-group">
                    <label className="form-label">Clase</label>
                    <select className="form-input" value={clase} onChange={e => setClase(e.target.value)}>
                      {CLASES.map(c => <option key={c}>{c}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Naturaleza</label>
                    <select className="form-input" value={naturaleza} onChange={e => setNaturaleza(e.target.value)}>
                      {NATURALEZAS.map(n => <option key={n}>{n}</option>)}
                    </select>
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Nivel</label>
                  <select className="form-input" value={nivel} onChange={e => setNivel(e.target.value)}>
                    {NIVELES.map(n => <option key={n}>{n}</option>)}
                  </select>
                </div>
              </>
            )}
            <div style={{ display: 'flex', gap: 20 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input type="checkbox" checked={tercero} onChange={e => setTercero(e.target.checked)} />
                <span style={{ fontSize: '0.9rem' }}>Requiere Tercero</span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input type="checkbox" checked={cc} onChange={e => setCc(e.target.checked)} />
                <span style={{ fontSize: '0.9rem' }}>Requiere Centro de Costo</span>
              </label>
            </div>
            {error && <div className="form-error">{error}</div>}
            <div className="form-actions">
              <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Guardando...' : 'Guardar'}</button>
            </div>
          </form>
    </Modal>
  );
}

export default function PucView() {
  const { user } = useAuth();
  const canEdit = user?.rol === 'Admin' || user?.rol === 'Administradora';

  const [cuentas, setCuentas] = useState<CuentaPUC[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [modal, setModal] = useState<Partial<CuentaPUC> | null | 'new'>(null);

  const load = useCallback(async () => {
    try {
      setCuentas(await contabilidadApi.getPuc());
    } catch {
      setToast({ message: 'Error al cargar el PUC', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async (data: any) => {
    if (modal === 'new') {
      await contabilidadApi.createPuc(data);
      setToast({ message: 'Cuenta creada exitosamente', type: 'success' });
    } else if (modal && 'id' in modal) {
      await contabilidadApi.updatePuc((modal as CuentaPUC).id, data);
      setToast({ message: 'Cuenta actualizada', type: 'success' });
    }
    setModal(null);
    load();
  };

  const handleToggle = async (c: CuentaPUC) => {
    try {
      await contabilidadApi.togglePuc(c.id);
      setToast({ message: `Cuenta ${c.activo ? 'desactivada' : 'activada'}`, type: 'success' });
      load();
    } catch {
      setToast({ message: 'Error al cambiar estado', type: 'error' });
    }
  };

  const filtered = cuentas.filter(c =>
    c.codigo_puc.includes(search) ||
    c.nombre.toLowerCase().includes(search.toLowerCase()) ||
    c.clase.toLowerCase().includes(search.toLowerCase())
  );

  const modalCuenta = modal === 'new' ? {} : (modal as Partial<CuentaPUC> | null);

  if (loading) return <div className="table-container" aria-busy="true" style={{ padding: 16 }}><Skeleton variant="row" count={8} /></div>;

  return (
    <div className="fade-in">
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      {modal !== null && (
        <CuentaModal
          cuenta={modalCuenta}
          onSave={handleSave}
          onClose={() => setModal(null)}
        />
      )}

      <div className="table-container">
        <div className="table-header">
          <div className="table-title">📋 Plan Único de Cuentas — PUC (Decreto 2650)</div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <input
              className="form-input"
              style={{ width: 220, padding: '6px 12px', fontSize: '0.85rem' }}
              placeholder="Buscar código o nombre..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <span className="table-count">{filtered.length} cuentas</span>
            {canEdit && (
              <button className="btn btn-primary" style={{ fontSize: '0.85rem' }} onClick={() => setModal('new')}>
                + Nueva cuenta
              </button>
            )}
          </div>
        </div>
        <div style={{ maxHeight: 'calc(100vh - 220px)', overflowY: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Código PUC</th>
                <th>Nombre de la Cuenta</th>
                <th>Clase</th>
                <th>Naturaleza</th>
                <th>Nivel</th>
                <th style={{ textAlign: 'center' }}>Tercero</th>
                <th style={{ textAlign: 'center' }}>C. Costo</th>
                <th style={{ textAlign: 'center' }}>Estado</th>
                {canEdit && <th style={{ textAlign: 'right' }}>Acciones</th>}
              </tr>
            </thead>
            <tbody>
              {filtered.map(c => (
                <tr key={c.id} style={{ opacity: c.activo ? 1 : 0.45 }}>
                  <td className="code">{c.codigo_puc}</td>
                  <td>{c.nombre}</td>
                  <td><span className={`badge ${CLASE_COLORS[c.clase] || 'neutral'}`}>{c.clase}</span></td>
                  <td><span className={`badge ${c.naturaleza === 'Débito' ? 'green' : 'blue'}`}>{c.naturaleza}</span></td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--neutral-400)' }}>{c.nivel}</td>
                  <td style={{ textAlign: 'center' }}>{c.requiere_tercero ? '✅' : '—'}</td>
                  <td style={{ textAlign: 'center' }}>{c.requiere_centro_costo ? '✅' : '—'}</td>
                  <td style={{ textAlign: 'center' }}>
                    <span className={`badge ${c.activo ? 'green' : 'neutral'}`}>{c.activo ? 'Activa' : 'Inactiva'}</span>
                  </td>
                  {canEdit && (
                    <td>
                      <div className="row-actions">
                        <button className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '3px 8px' }} onClick={() => setModal(c)}>✏️</button>
                        <button className={`btn ${c.activo ? 'btn-ghost' : 'btn-primary'}`} style={{ fontSize: '0.75rem', padding: '3px 8px' }} onClick={() => handleToggle(c)}>
                          {c.activo ? '🚫' : '✅'}
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={canEdit ? 9 : 8} style={{ textAlign: 'center', color: 'var(--neutral-500)', padding: 32 }}>No se encontraron cuentas</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
