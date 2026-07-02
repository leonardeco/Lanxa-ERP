import { useState, useEffect, useCallback } from 'react';
import { contabilidadApi, type ParametroTributario } from '../services/contabilidadApi';
import { useAuth } from '../contexts/auth';
import Toast from '../components/Toast';
import Modal from '../components/Modal';
import Skeleton from '../components/Skeleton';

function EditModal({ param, onSave, onClose }: {
  param: ParametroTributario;
  onSave: (data: Partial<ParametroTributario>) => Promise<void>;
  onClose: () => void;
}) {
  const [tarifa, setTarifa] = useState(param.tarifa_valor?.toString() ?? '');
  const [base, setBase] = useState(param.base_aplica ?? '');
  const [puc, setPuc] = useState(param.cuenta_puc ?? '');
  const [notas, setNotas] = useState(param.notas ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await onSave({
        tarifa_valor: tarifa !== '' ? parseFloat(tarifa) : null,
        base_aplica: base || null,
        cuenta_puc: puc || null,
        notas: notas || null,
      });
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Editar parámetro tributario" onClose={onClose}>
          <form onSubmit={handleSubmit} className="form-vertical">
            <div className="form-group">
              <label className="form-label">Concepto</label>
              <input className="form-input" value={param.concepto} disabled style={{ opacity: 0.5 }} />
            </div>
            <div className="form-group">
              <label className="form-label">Tarifa / Valor (%)</label>
              <input className="form-input" type="number" step="0.001" min="0" max="100"
                value={tarifa} onChange={e => setTarifa(e.target.value)} placeholder="Ej: 19.000" />
            </div>
            <div className="form-group">
              <label className="form-label">Base de aplicación</label>
              <input className="form-input" value={base} onChange={e => setBase(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Cuenta PUC</label>
              <input className="form-input" value={puc} onChange={e => setPuc(e.target.value)} placeholder="Ej: 2365" />
            </div>
            <div className="form-group">
              <label className="form-label">Notas</label>
              <input className="form-input" value={notas} onChange={e => setNotas(e.target.value)} />
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

export default function TributariosView() {
  const { user } = useAuth();
  const canEdit = user?.rol === 'Admin' || user?.rol === 'Administradora';

  const [params, setParams] = useState<ParametroTributario[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [editing, setEditing] = useState<ParametroTributario | null>(null);

  const load = useCallback(async () => {
    try {
      setParams(await contabilidadApi.getTributarios());
    } catch {
      setToast({ message: 'Error al cargar parámetros tributarios', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async (data: Partial<ParametroTributario>) => {
    if (!editing) return;
    await contabilidadApi.updateTributario(editing.id, data);
    setToast({ message: 'Parámetro actualizado', type: 'success' });
    setEditing(null);
    load();
  };

  const handleToggle = async (p: ParametroTributario) => {
    try {
      await contabilidadApi.toggleTributario(p.id);
      setToast({ message: `Parámetro ${p.activo ? 'desactivado' : 'activado'}`, type: 'success' });
      load();
    } catch {
      setToast({ message: 'Error al cambiar estado', type: 'error' });
    }
  };

  if (loading) return <div className="table-container" aria-busy="true" style={{ padding: 16 }}><Skeleton variant="row" count={8} /></div>;

  return (
    <div className="fade-in">
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      {editing && <EditModal param={editing} onSave={handleSave} onClose={() => setEditing(null)} />}

      <div className="table-container">
        <div className="table-header">
          <div className="table-title">🏛️ Parámetros Tributarios e Impuestos</div>
          <div className="table-count">{params.length} parámetros</div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Concepto</th>
              <th>Tarifa</th>
              <th>Base de Aplicación</th>
              <th>Cuenta PUC</th>
              <th>Notas</th>
              <th>Estado</th>
              {canEdit && <th style={{ textAlign: 'right' }}>Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {params.map(p => (
              <tr key={p.id} style={{ opacity: p.activo ? 1 : 0.5 }}>
                <td style={{ fontWeight: 500 }}>{p.concepto}</td>
                <td className="code" style={{ color: p.tarifa_valor != null ? 'var(--blue-400)' : 'var(--neutral-500)' }}>
                  {p.tarifa_valor != null ? `${(p.tarifa_valor * 100).toFixed(3)}%` : '—'}
                </td>
                <td style={{ fontSize: '0.85rem' }}>{p.base_aplica ?? '—'}</td>
                <td className="code">{p.cuenta_puc ?? '—'}</td>
                <td style={{ fontSize: '0.75rem', color: p.notas?.includes('⚠️') ? 'var(--amber-400)' : 'var(--neutral-500)' }}>
                  {p.notas ?? '—'}
                </td>
                <td><span className={`badge ${p.activo ? 'green' : 'neutral'}`}>{p.activo ? 'Activo' : 'Inactivo'}</span></td>
                {canEdit && (
                  <td>
                    <div className="row-actions">
                      <button className="btn btn-ghost" style={{ fontSize: '0.78rem', padding: '4px 10px' }} onClick={() => setEditing(p)}>✏️ Editar</button>
                      <button className={`btn ${p.activo ? 'btn-ghost' : 'btn-primary'}`} style={{ fontSize: '0.78rem', padding: '4px 10px' }} onClick={() => handleToggle(p)}>
                        {p.activo ? '🚫 Desactivar' : '✅ Activar'}
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
