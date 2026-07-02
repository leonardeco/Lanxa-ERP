import { useState, useEffect, useCallback } from 'react';
import { contabilidadApi, type CentroCosto } from '../services/contabilidadApi';
import { useAuth } from '../contexts/AuthContext';
import Toast from '../components/Toast';
import Modal from '../components/Modal';
import Skeleton from '../components/Skeleton';

const TIPOS = ['Marca', 'Área', 'Proyecto', 'Otro'];

function CentroModal({ centro, onSave, onClose }: {
  centro: Partial<CentroCosto> | null;
  onSave: (data: any) => Promise<void>;
  onClose: () => void;
}) {
  const isEdit = centro?.id != null;
  const [codigo, setCodigo] = useState(centro?.codigo ?? '');
  const [nombre, setNombre] = useState(centro?.nombre ?? '');
  const [tipo, setTipo] = useState(centro?.tipo ?? 'Marca');
  const [marca, setMarca] = useState(centro?.marca_asociada ?? '');
  const [responsable, setResponsable] = useState(centro?.responsable ?? '');
  const [notas, setNotas] = useState(centro?.notas ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nombre.trim()) { setError('El nombre es obligatorio'); return; }
    if (!isEdit && !codigo.trim()) { setError('El código es obligatorio'); return; }
    setError(''); setSaving(true);
    try {
      await onSave(isEdit
        ? { nombre: nombre.trim(), tipo, marca_asociada: marca || null, responsable: responsable || null, notas: notas || null }
        : { codigo: codigo.trim(), nombre: nombre.trim(), tipo, marca_asociada: marca || null, responsable: responsable || null, notas: notas || null, activo: true }
      );
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={isEdit ? 'Editar centro de costo' : 'Nuevo centro de costo'} onClose={onClose}>
          <form onSubmit={handleSubmit} className="form-vertical">
            {isEdit ? (
              <div className="form-group">
                <label className="form-label">Código</label>
                <input className="form-input" value={centro?.codigo ?? ''} disabled style={{ opacity: 0.5 }} />
              </div>
            ) : (
              <div className="form-group">
                <label className="form-label">Código *</label>
                <input className="form-input" value={codigo} onChange={e => setCodigo(e.target.value)} placeholder="Ej: CC-11" />
              </div>
            )}
            <div className="form-group">
              <label className="form-label">Nombre *</label>
              <input className="form-input" value={nombre} onChange={e => setNombre(e.target.value)} placeholder="Nombre del centro de costo" />
            </div>
            <div className="form-grid-2">
              <div className="form-group">
                <label className="form-label">Tipo</label>
                <select className="form-input" value={tipo} onChange={e => setTipo(e.target.value)}>
                  {TIPOS.map(t => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Marca Asociada</label>
                <input className="form-input" value={marca} onChange={e => setMarca(e.target.value)} placeholder="Ej: Superozono" />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Responsable</label>
              <input className="form-input" value={responsable} onChange={e => setResponsable(e.target.value)} placeholder="Nombre del responsable (opcional)" />
            </div>
            <div className="form-group">
              <label className="form-label">Notas</label>
              <input className="form-input" value={notas} onChange={e => setNotas(e.target.value)} placeholder="Observaciones (opcional)" />
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

export default function CentrosCostoView() {
  const { user } = useAuth();
  const canEdit = user?.rol === 'Admin' || user?.rol === 'Administradora';

  const [centros, setCentros] = useState<CentroCosto[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [modal, setModal] = useState<Partial<CentroCosto> | null | 'new'>(null);

  const load = useCallback(async () => {
    try {
      setCentros(await contabilidadApi.getCentros());
    } catch {
      setToast({ message: 'Error al cargar centros de costo', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async (data: any) => {
    if (modal === 'new') {
      await contabilidadApi.createCentro(data);
      setToast({ message: 'Centro de costo creado', type: 'success' });
    } else if (modal && 'id' in modal) {
      await contabilidadApi.updateCentro((modal as CentroCosto).id, data);
      setToast({ message: 'Centro de costo actualizado', type: 'success' });
    }
    setModal(null);
    load();
  };

  const handleToggle = async (c: CentroCosto) => {
    try {
      await contabilidadApi.toggleCentro(c.id);
      setToast({ message: `Centro ${c.activo ? 'desactivado' : 'activado'}`, type: 'success' });
      load();
    } catch {
      setToast({ message: 'Error al cambiar estado', type: 'error' });
    }
  };

  const modalCentro = modal === 'new' ? {} : (modal as Partial<CentroCosto> | null);

  if (loading) return <div className="table-container" aria-busy="true" style={{ padding: 16 }}><Skeleton variant="row" count={8} /></div>;

  return (
    <div className="fade-in">
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      {modal !== null && (
        <CentroModal
          centro={modalCentro}
          onSave={handleSave}
          onClose={() => setModal(null)}
        />
      )}

      <div className="table-container">
        <div className="table-header">
          <div className="table-title">🏷️ Centros de Costo — Marcas y Áreas</div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <span className="table-count">{centros.length} centros</span>
            {canEdit && (
              <button className="btn btn-primary" style={{ fontSize: '0.85rem' }} onClick={() => setModal('new')}>
                + Nuevo centro
              </button>
            )}
          </div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Código</th>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Marca Asociada</th>
              <th>Responsable</th>
              <th>Notas</th>
              <th style={{ textAlign: 'center' }}>Estado</th>
              {canEdit && <th style={{ textAlign: 'right' }}>Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {centros.map(c => (
              <tr key={c.id} style={{ opacity: c.activo ? 1 : 0.5 }}>
                <td className="code">{c.codigo}</td>
                <td style={{ fontWeight: 600 }}>{c.nombre}</td>
                <td><span className={`badge ${c.tipo === 'Marca' ? 'blue' : 'purple'}`}>{c.tipo}</span></td>
                <td style={{ color: c.marca_asociada ? undefined : 'var(--neutral-500)' }}>{c.marca_asociada ?? '—'}</td>
                <td style={{ fontSize: '0.85rem', color: 'var(--neutral-400)' }}>{c.responsable ?? '—'}</td>
                <td style={{ fontSize: '0.75rem', color: c.notas?.includes('⚠️') ? 'var(--amber-400)' : 'var(--neutral-500)' }}>
                  {c.notas || '—'}
                </td>
                <td style={{ textAlign: 'center' }}>
                  <span className={`badge ${c.activo ? 'green' : 'neutral'}`}>{c.activo ? 'Activo' : 'Inactivo'}</span>
                </td>
                {canEdit && (
                  <td>
                    <div className="row-actions">
                      <button className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '3px 8px' }} onClick={() => setModal(c)}>✏️ Editar</button>
                      <button className={`btn ${c.activo ? 'btn-ghost' : 'btn-primary'}`} style={{ fontSize: '0.75rem', padding: '3px 8px' }} onClick={() => handleToggle(c)}>
                        {c.activo ? '🚫' : '✅'}
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
            {centros.length === 0 && (
              <tr><td colSpan={canEdit ? 8 : 7} style={{ textAlign: 'center', color: 'var(--neutral-500)', padding: 32 }}>No hay centros de costo</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
