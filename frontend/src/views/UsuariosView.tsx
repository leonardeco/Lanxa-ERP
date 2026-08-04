import { useState, useEffect, useCallback } from 'react';
import { usuariosApi, ROLES, type Usuario, type UsuarioCreate, type UsuarioUpdate } from '../services/usuariosApi';
import { useAuth } from '../contexts/auth';
import Toast from '../components/Toast';
import Modal from '../components/Modal';

// ── PasswordInput: campo con ojo mostrar/ocultar ─────────

function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  ) : (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  );
}

function PasswordInput({
  value,
  onChange,
  placeholder,
  autoComplete,
  required,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  autoComplete?: string;
  required?: boolean;
  className?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div style={{ position: 'relative' }}>
      <input
        className={className}
        type={show ? 'text' : 'password'}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required={required}
        style={{ paddingRight: '2.2rem', width: '100%', boxSizing: 'border-box' }}
      />
      <button
        type="button"
        onClick={() => setShow(v => !v)}
        aria-label={show ? 'Ocultar contraseña' : 'Ver contraseña'}
        style={{
          position: 'absolute', right: '0.5rem', top: '50%', transform: 'translateY(-50%)',
          background: 'none', border: 'none', cursor: 'pointer', padding: '0.2rem',
          color: 'var(--neutral-400, #9ca3af)', display: 'flex', alignItems: 'center',
        }}
      >
        <EyeIcon open={show} />
      </button>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────

function getInitials(name: string) {
  return name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
}

const ROL_COLORS: Record<string, string> = {
  Superusuario: 'red',
  Directora: 'purple',
  CEO: 'orange',
  Contador: 'blue',
  'Auxiliar Contable': 'green',
};

// ── Modal Crear / Editar usuario ─────────────────────────

const EMPTY_FORM: UsuarioCreate = {
  email: '', nombre_completo: '', rol: 'Auxiliar Contable', is_active: true, password: '',
};

function UsuarioFormModal({
  initial,
  isEdit,
  onSave,
  onClose,
}: {
  initial?: Usuario;
  isEdit: boolean;
  onSave: (data: UsuarioCreate | UsuarioUpdate) => Promise<void>;
  onClose: () => void;
}) {
  const [form, setForm] = useState<UsuarioCreate>(
    initial
      ? { email: initial.email, nombre_completo: initial.nombre_completo, rol: initial.rol, is_active: initial.is_active, password: '' }
      : EMPTY_FORM
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const set = (field: keyof UsuarioCreate, value: string | boolean) =>
    setForm(f => ({ ...f, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.nombre_completo.trim()) return setError('El nombre es requerido');
    if (!isEdit && !form.password) return setError('La contraseña es requerida');
    if (!isEdit && form.password.length < 8) return setError('La contraseña debe tener al menos 8 caracteres');
    setSaving(true);
    try {
      if (isEdit) {
        const update: UsuarioUpdate = { nombre_completo: form.nombre_completo, rol: form.rol };
        await onSave(update);
      } else {
        await onSave(form);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={isEdit ? 'Editar usuario' : 'Nuevo usuario'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="form-vertical">
        {!isEdit && (
          <div className="form-group">
            <label className="form-label">Correo electrónico *</label>
            <input
              className="form-input"
              type="email"
              value={form.email}
              onChange={e => set('email', e.target.value)}
              placeholder="usuario@ejemplo.com"
              required
            />
          </div>
        )}
        {isEdit && (
          <div className="form-group">
            <label className="form-label">Correo electrónico</label>
            <input className="form-input" value={form.email} disabled style={{ opacity: 0.5 }} />
          </div>
        )}
        <div className="form-group">
          <label className="form-label">Nombre completo *</label>
          <input
            className="form-input"
            type="text"
            value={form.nombre_completo}
            onChange={e => set('nombre_completo', e.target.value)}
            placeholder="Nombre Apellido"
            required
          />
        </div>
        <div className="form-group">
          <label className="form-label">Rol</label>
          <select className="form-input" value={form.rol} onChange={e => set('rol', e.target.value)}>
            {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        {!isEdit && (
          <div className="form-group">
            <label className="form-label">Contraseña *</label>
            <PasswordInput
              className="form-input"
              value={form.password}
              onChange={v => set('password', v)}
              placeholder="Mínimo 8 caracteres"
              autoComplete="new-password"
            />
          </div>
        )}
        {error && <div className="form-error">{error}</div>}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>Cancelar</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Guardando...' : isEdit ? 'Guardar cambios' : 'Crear usuario'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ── Modal Cambiar contraseña propia ───────────────────────

function ChangePasswordModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (next.length < 8) return setError('La nueva contraseña debe tener al menos 8 caracteres');
    if (next !== confirm) return setError('Las contraseñas no coinciden');
    setSaving(true);
    try {
      await usuariosApi.changePassword(current, next);
      onSaved();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Error al cambiar contraseña');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Cambiar mi contraseña" onClose={onClose}>
      <form onSubmit={handleSubmit} className="form-vertical">
        <div className="form-group">
          <label className="form-label">Contraseña actual</label>
          <PasswordInput className="form-input" value={current} onChange={setCurrent} autoComplete="current-password" required />
        </div>
        <div className="form-group">
          <label className="form-label">Nueva contraseña</label>
          <PasswordInput className="form-input" value={next} onChange={setNext} placeholder="Mínimo 8 caracteres" autoComplete="new-password" required />
        </div>
        <div className="form-group">
          <label className="form-label">Confirmar nueva contraseña</label>
          <PasswordInput className="form-input" value={confirm} onChange={setConfirm} autoComplete="new-password" required />
        </div>
        {error && <div className="form-error">{error}</div>}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>Cancelar</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Guardando...' : 'Cambiar contraseña'}</button>
        </div>
      </form>
    </Modal>
  );
}

// ── Modal Resetear contraseña de otro usuario (Admin) ────

function ResetPasswordModal({ usuario, onClose, onSaved }: { usuario: Usuario; onClose: () => void; onSaved: () => void }) {
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (next.length < 8) return setError('La nueva contraseña debe tener al menos 8 caracteres');
    if (next !== confirm) return setError('Las contraseñas no coinciden');
    setSaving(true);
    try {
      await usuariosApi.resetPassword(usuario.id, next);
      onSaved();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Error al restablecer la contraseña');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={`Resetear contraseña — ${usuario.nombre_completo}`} onClose={onClose}>
      <form onSubmit={handleSubmit} className="form-vertical">
        <p style={{ fontSize: '0.85rem', color: 'var(--neutral-400)', margin: 0 }}>
          Define una contraseña nueva para este usuario y comunícasela por fuera del sistema.
        </p>
        <div className="form-group">
          <label className="form-label">Contraseña nueva</label>
          <PasswordInput className="form-input" value={next} onChange={setNext} placeholder="Mínimo 8 caracteres" autoComplete="new-password" required />
        </div>
        <div className="form-group">
          <label className="form-label">Confirmar contraseña nueva</label>
          <PasswordInput className="form-input" value={confirm} onChange={setConfirm} autoComplete="new-password" required />
        </div>
        {error && <div className="form-error">{error}</div>}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>Cancelar</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Guardando...' : 'Restablecer contraseña'}</button>
        </div>
      </form>
    </Modal>
  );
}

// ── Vista principal ───────────────────────────────────────

export default function UsuariosView() {
  const { user: me } = useAuth();
  const isSuperadmin = me?.rol === 'Superusuario';

  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [modalCreate, setModalCreate] = useState(false);
  const [modalEdit, setModalEdit] = useState<Usuario | null>(null);
  const [modalPassword, setModalPassword] = useState(false);
  const [modalReset, setModalReset] = useState<Usuario | null>(null);

  const showToast = (message: string, type: 'success' | 'error' = 'success') =>
    setToast({ message, type });

  const load = useCallback(async () => {
    if (!isSuperadmin) { setLoading(false); return; }
    try {
      setUsuarios(await usuariosApi.list());
    } catch {
      showToast('Error al cargar usuarios', 'error');
    } finally {
      setLoading(false);
    }
  }, [isSuperadmin]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (data: any) => {
    await usuariosApi.create(data);
    showToast('Usuario creado correctamente');
    setModalCreate(false);
    load();
  };

  const handleEdit = async (data: any) => {
    if (!modalEdit) return;
    await usuariosApi.update(modalEdit.id, data);
    showToast('Usuario actualizado');
    setModalEdit(null);
    load();
  };

  const handleToggle = async (u: Usuario) => {
    try {
      await usuariosApi.toggle(u.id);
      showToast(`Usuario ${u.is_active ? 'desactivado' : 'activado'}`);
      load();
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? 'Error al cambiar estado', 'error');
    }
  };

  const handleRevocarSesiones = async (u: Usuario) => {
    if (!confirm(`¿Cerrar las sesiones remotas de ${u.nombre_completo}?\nTendrá que iniciar sesión de nuevo en todos sus equipos.`)) return;
    try {
      const res = await usuariosApi.revocarSesiones(u.id);
      showToast(res.message);
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? 'Error al revocar sesiones', 'error');
    }
  };

  const totalActivos = usuarios.filter(u => u.is_active).length;
  const totalInactivos = usuarios.length - totalActivos;

  return (
    <div>
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

      {/* ── Header actions ──────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-ghost" onClick={() => setModalPassword(true)}>
            🔑 Cambiar mi contraseña
          </button>
          {isSuperadmin && (
            <button className="btn btn-primary" onClick={() => setModalCreate(true)}>
              + Nuevo usuario
            </button>
          )}
        </div>
      </div>

      {/* ── Stats (solo Superadmin) ──────────────────── */}
      {isSuperadmin && !loading && (
        <div className="stats-grid" style={{ marginBottom: 20 }}>
          <div className="stat-card fade-in">
            <div className="stat-card-header"><div className="stat-card-icon blue">👤</div></div>
            <div className="stat-card-value">{usuarios.length}</div>
            <div className="stat-card-label">Total usuarios</div>
          </div>
          <div className="stat-card fade-in">
            <div className="stat-card-header"><div className="stat-card-icon green">✅</div></div>
            <div className="stat-card-value">{totalActivos}</div>
            <div className="stat-card-label">Activos</div>
          </div>
          <div className="stat-card fade-in">
            <div className="stat-card-header"><div className="stat-card-icon neutral">🚫</div></div>
            <div className="stat-card-value">{totalInactivos}</div>
            <div className="stat-card-label">Inactivos</div>
          </div>
          {ROLES.map(rol => {
            const count = usuarios.filter(u => u.rol === rol).length;
            if (count === 0) return null;
            return (
              <div className="stat-card fade-in" key={rol}>
                <div className="stat-card-header"><div className={`stat-card-icon ${ROL_COLORS[rol]}`}>🏷️</div></div>
                <div className="stat-card-value">{count}</div>
                <div className="stat-card-label">{rol}</div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Tabla de usuarios ────────────────────────── */}
      {isSuperadmin ? (
        loading ? (
          <div className="loading-screen" style={{ minHeight: 200 }}>
            <div className="loading-spinner" />
            <div className="loading-sub">Cargando usuarios...</div>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Usuario</th>
                  <th>Correo</th>
                  <th>Rol</th>
                  <th>Estado</th>
                  <th style={{ textAlign: 'right' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {usuarios.length === 0 ? (
                  <tr><td colSpan={5} style={{ textAlign: 'center', padding: 32, color: 'var(--neutral-500)' }}>Sin usuarios registrados</td></tr>
                ) : (
                  usuarios.map(u => (
                    <tr key={u.id}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div style={{
                            width: 34, height: 34, borderRadius: '50%', background: 'var(--neutral-800)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '0.75rem', fontWeight: 700, color: 'var(--neutral-200)', flexShrink: 0,
                          }}>
                            {getInitials(u.nombre_completo)}
                          </div>
                          <span style={{ fontWeight: 500, color: 'var(--neutral-100)' }}>
                            {u.nombre_completo}
                            {u.id === me?.id && (
                              <span style={{ marginLeft: 6, fontSize: '0.68rem', color: 'var(--neutral-500)' }}>(yo)</span>
                            )}
                          </span>
                        </div>
                      </td>
                      <td style={{ color: 'var(--neutral-400)', fontSize: '0.85rem' }}>{u.email}</td>
                      <td><span className={`badge ${ROL_COLORS[u.rol] ?? 'neutral'}`}>{u.rol}</span></td>
                      <td>
                        <span className={`badge ${u.is_active ? 'green' : 'neutral'}`}>
                          {u.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                          <button
                            className="btn btn-ghost"
                            style={{ fontSize: '0.78rem', padding: '4px 10px' }}
                            onClick={() => setModalEdit(u)}
                          >
                            ✏️ Editar
                          </button>
                          <button
                            className="btn btn-ghost"
                            style={{ fontSize: '0.78rem', padding: '4px 10px' }}
                            onClick={() => setModalReset(u)}
                          >
                            🔓 Resetear contraseña
                          </button>
                          <button
                            className="btn btn-ghost"
                            style={{ fontSize: '0.78rem', padding: '4px 10px' }}
                            onClick={() => handleRevocarSesiones(u)}
                            title="Borra sus refresh tokens: la sesión muere al expirar el access token (máx. 15 min)"
                          >
                            🔒 Cerrar sesiones
                          </button>
                          <button
                            className={`btn ${u.is_active ? 'btn-ghost' : 'btn-primary'}`}
                            style={{ fontSize: '0.78rem', padding: '4px 10px' }}
                            onClick={() => handleToggle(u)}
                            disabled={u.id === me?.id}
                            title={u.id === me?.id ? 'No puedes desactivarte a ti mismo' : ''}
                          >
                            {u.is_active ? '🚫 Desactivar' : '✅ Activar'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )
      ) : (
        <div className="empty-state">
          <div className="empty-state-icon">🔒</div>
          <div className="empty-state-text">Acceso restringido</div>
          <div className="empty-state-sub">Solo el Superusuario puede gestionar usuarios. Puedes cambiar tu contraseña desde el botón de arriba.</div>
        </div>
      )}

      {/* ── Modales ──────────────────────────────────── */}
      {modalCreate && (
        <UsuarioFormModal isEdit={false} onSave={handleCreate} onClose={() => setModalCreate(false)} />
      )}
      {modalEdit && (
        <UsuarioFormModal isEdit initial={modalEdit} onSave={handleEdit} onClose={() => setModalEdit(null)} />
      )}
      {modalPassword && (
        <ChangePasswordModal
          onClose={() => setModalPassword(false)}
          onSaved={() => { setModalPassword(false); showToast('Contraseña actualizada correctamente'); }}
        />
      )}
      {modalReset && (
        <ResetPasswordModal
          usuario={modalReset}
          onClose={() => setModalReset(null)}
          onSaved={() => { setModalReset(null); showToast('Contraseña restablecida correctamente'); }}
        />
      )}
    </div>
  );
}
