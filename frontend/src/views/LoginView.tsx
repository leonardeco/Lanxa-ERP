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
      <div className="login-glass-card fade-in">
        <div className="login-header">
          <img src="/logo_ozono.png" alt="Super Ozono" className="login-logo-small" />
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
  );
};

export default LoginView;
