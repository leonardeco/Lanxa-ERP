import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../services/api';

const LoginView: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
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
      setError(err.response?.data?.detail || 'Error al iniciar sesión. Verifica tus credenciales.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-form-side">
        <div className="login-glass-card fade-in">
          <div className="login-header">
            <div style={{
              width: 56, height: 56, margin: '0 auto 16px',
              background: 'linear-gradient(135deg, var(--oz-green-600), var(--oz-green-400))',
              borderRadius: 14, display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 4px 20px rgba(0,166,124,0.3)'
            }}>
              <svg viewBox="0 0 32 32" width="28" height="28" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="16" cy="16" r="14" stroke="white" strokeWidth="2" opacity="0.8"/>
                <circle cx="16" cy="16" r="8" stroke="white" strokeWidth="1.5" opacity="0.5"/>
                <circle cx="16" cy="16" r="3" fill="white"/>
                <path d="M16 2 L16 6" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M16 26 L16 30" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M2 16 L6 16" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M26 16 L30 16" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>
            <h2>Super Ozono Global</h2>
            <p>Portal ERP Corporativo</p>
          </div>

          {error && <div className="login-error fade-in">{error}</div>}

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label>Correo Electrónico</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="usuario@superozonoglobal.com"
                required
              />
            </div>

            <div className="form-group">
              <label>Contraseña</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>

            <button type="submit" className="login-button" disabled={loading}>
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

          <div style={{
            textAlign: 'center', marginTop: 24,
            fontSize: '0.7rem', color: 'var(--neutral-600)'
          }}>
            TECNOLOGÍA E INNOVACIÓN SUPER OZONO S.A.S. · NIT: 901841798-5
          </div>
        </div>
      </div>

      <div className="login-brand-side">
        <img src="/logo_ozono.png" alt="Super Ozono" className="login-brand-logo fade-in" />
      </div>
    </div>
  );
};

export default LoginView;
