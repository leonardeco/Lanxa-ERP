import React, { useState } from 'react';
import { useAuth } from '../contexts/auth';
import { api } from '../services/api';
import { APP_VERSION, apiHostLabel, healthUrl } from '../config';

const LoginView: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [loading, setLoading] = useState(false);
  const [probing, setProbing] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { login } = useAuth();

  const handleProbe = async () => {
    setError('');
    setInfo('');
    setProbing(true);
    try {
      const res = await fetch(healthUrl());
      if (!res.ok) {
        setError(`El servidor respondió HTTP ${res.status}. Revisa el backend (ventana "Backend — FastAPI").`);
        return;
      }
      const data = await res.json();
      setInfo(
        `Conexión OK · API v${data.version ?? APP_VERSION} · ${apiHostLabel()} · BD: ${data.database ?? '?'}`,
      );
    } catch {
      setError(
        `No se puede conectar a ${apiHostLabel()}. En el PC servidor ejecuta start.bat (espera Backend y Frontend). ` +
          'Si cambió la IP de la red, vuelve a ejecutar start.bat o ops\\sync-lan-ip.ps1.',
      );
    } finally {
      setProbing(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setInfo('');
    setLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await api.post('/login/access-token', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      login(response.data.access_token);
    } catch (err: any) {
      const status = err.response?.status as number | undefined;
      const data = err.response?.data;
      const detail = typeof data?.detail === 'string' ? data.detail : undefined;
      const rateMsg = typeof data?.error === 'string' ? data.error : undefined;
      if (!err.response) {
        setError(
          `No se puede conectar al servidor (${apiHostLabel()}). ` +
            'En el PC servidor ejecuta start.bat y espera a que Backend y Frontend estén abiertos. ' +
            'Si cambió la IP, ejecuta start.bat de nuevo (sincroniza sola).',
        );
      } else if (status === 429 || (rateMsg && /rate limit/i.test(rateMsg))) {
        setError('Demasiados intentos de login. Espera 1 minuto e inténtalo de nuevo.');
      } else {
        setError(detail || rateMsg || 'Error al iniciar sesión. Verifica tus credenciales.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-glass-card fade-in">
        <div className="login-header">
          <svg viewBox="0 0 40 40" width={48} height={48} aria-label="Lanxa" className="login-logo-small" style={{ display: 'block', margin: '0 auto' }}>
            <defs>
              <linearGradient id="lanxa-login" x1="0" y1="1" x2="1" y2="0">
                <stop offset="0" stopColor="#7c5cff" />
                <stop offset="1" stopColor="#1fe6cd" />
              </linearGradient>
            </defs>
            <path d="M9 31 L21 7 L26 7 L14 31 Z" fill="url(#lanxa-login)" />
            <path d="M18 31 L30 7 L35 7 L23 31 Z" fill="url(#lanxa-login)" opacity={0.55} />
          </svg>
          <h2>Lanxa ERP</h2>
          <p>Portal ERP Corporativo · v{APP_VERSION}</p>
        </div>

        {error && <div className="login-error fade-in">{error}</div>}
        {info && !error && (
          <div
            className="fade-in"
            style={{
              background: 'rgba(26, 122, 94, 0.15)',
              border: '1px solid rgba(26, 122, 94, 0.4)',
              color: 'var(--oz-green-300, #6ee7b7)',
              borderRadius: 8,
              padding: '10px 14px',
              fontSize: '0.85rem',
              marginBottom: 12,
            }}
          >
            {info}
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label>Correo Electrónico</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="usuario@lanxa.local"
              required
            />
          </div>

          <div className="form-group">
            <label>Contraseña</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={{ paddingRight: '2.5rem', width: '100%', boxSizing: 'border-box' }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(v => !v)}
                aria-label={showPassword ? 'Ocultar contraseña' : 'Ver contraseña'}
                style={{
                  position: 'absolute',
                  right: '0.6rem',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '0.2rem',
                  color: 'var(--neutral-400, #9ca3af)',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                {showPassword ? (
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                )}
              </button>
            </div>
          </div>

          <button type="submit" className="login-button" disabled={loading || probing}>
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                <span className="loading-spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                Verificando...
              </span>
            ) : (
              'Acceder al Sistema'
            )}
          </button>
        </form>

        <button
          type="button"
          className="btn-secondary"
          style={{ width: '100%', marginTop: 12, fontSize: '0.85rem' }}
          onClick={handleProbe}
          disabled={loading || probing}
        >
          {probing ? 'Probando…' : 'Probar conexión al servidor'}
        </button>

        <div
          style={{
            textAlign: 'center',
            marginTop: 20,
            fontSize: '0.7rem',
            color: 'var(--neutral-600)',
            lineHeight: 1.5,
          }}
        >
          LANXA S.A.S.
          <br />
          API: {apiHostLabel()} · v{APP_VERSION}
        </div>
      </div>
    </div>
  );
};

export default LoginView;
