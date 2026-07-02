import { useState, useEffect, useCallback } from 'react';
import { contabilidadApi, type Periodo } from '../services/contabilidadApi';
import { useAuth } from '../contexts/auth';
import Toast from '../components/Toast';
import Skeleton from '../components/Skeleton';

const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

export default function PeriodosView() {
  const { user } = useAuth();
  const canEdit = user?.rol === 'Admin' || user?.rol === 'Administradora';

  const [periodos, setPeriodos] = useState<Periodo[]>([]);
  const [loading, setLoading] = useState(true);
  const [creando, setCreando] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const load = useCallback(async () => {
    try {
      setPeriodos(await contabilidadApi.getPeriodos());
    } catch {
      setToast({ message: 'Error al cargar períodos', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleToggle = async (p: Periodo) => {
    try {
      await contabilidadApi.togglePeriodo(p.id);
      setToast({ message: `Período ${p.periodo} ${p.estado === 'Abierto' ? 'cerrado' : 'reabierto'}`, type: 'success' });
      load();
    } catch {
      setToast({ message: 'Error al cambiar estado del período', type: 'error' });
    }
  };

  const handleNuevoAnio = async () => {
    const anios = [...new Set(periodos.map(p => p.anio))];
    const maxAnio = anios.length ? Math.max(...anios) : new Date().getFullYear();
    const nuevoAnio = maxAnio + 1;

    if (!confirm(`¿Crear los 12 períodos para el año ${nuevoAnio}?`)) return;

    setCreando(true);
    try {
      for (let mes = 1; mes <= 12; mes++) {
        await contabilidadApi.createPeriodo(nuevoAnio, mes);
      }
      setToast({ message: `12 períodos de ${nuevoAnio} creados`, type: 'success' });
      load();
    } catch (err: any) {
      setToast({ message: err?.response?.data?.detail ?? 'Error al crear períodos', type: 'error' });
    } finally {
      setCreando(false);
    }
  };

  // Agrupar por año
  const porAnio = periodos.reduce<Record<number, Periodo[]>>((acc, p) => {
    if (!acc[p.anio]) acc[p.anio] = [];
    acc[p.anio].push(p);
    return acc;
  }, {});

  if (loading) return <div className="table-container" aria-busy="true" style={{ padding: 16 }}><Skeleton variant="row" count={8} /></div>;

  return (
    <div className="fade-in">
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

      {Object.entries(porAnio).sort(([a], [b]) => Number(b) - Number(a)).map(([anio, ps]) => (
        <div key={anio} className="table-container" style={{ marginBottom: 24 }}>
          <div className="table-header">
            <div className="table-title">📅 Períodos Contables — {anio}</div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span className="table-count">{ps.filter(p => p.estado === 'Abierto').length} abiertos</span>
            </div>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Período</th>
                <th>Mes</th>
                <th>Estado</th>
                <th>Fecha cierre</th>
                {canEdit && <th style={{ textAlign: 'right' }}>Acciones</th>}
              </tr>
            </thead>
            <tbody>
              {ps.map(p => (
                <tr key={p.id}>
                  <td className="code">{p.periodo}</td>
                  <td>{MESES[p.mes - 1]}</td>
                  <td><span className={`badge ${p.estado === 'Abierto' ? 'green' : 'neutral'}`}>{p.estado}</span></td>
                  <td style={{ color: 'var(--neutral-500)', fontSize: '0.85rem' }}>{p.fecha_cierre ?? '—'}</td>
                  {canEdit && (
                    <td>
                      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <button
                          className={`btn ${p.estado === 'Abierto' ? 'btn-ghost' : 'btn-primary'}`}
                          style={{ fontSize: '0.78rem', padding: '4px 10px' }}
                          onClick={() => handleToggle(p)}
                        >
                          {p.estado === 'Abierto' ? '🔒 Cerrar' : '🔓 Reabrir'}
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      {canEdit && (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 8 }}>
          <button className="btn btn-primary" onClick={handleNuevoAnio} disabled={creando}>
            {creando ? 'Creando...' : '+ Nuevo año'}
          </button>
        </div>
      )}
    </div>
  );
}
