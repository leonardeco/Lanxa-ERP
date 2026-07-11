import React, { useState, useEffect } from 'react';
import { api, setOnSessionExpired, setAccessToken } from '../services/api';
import { jwtDecode } from 'jwt-decode';
import { AuthContext, type User } from './auth';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  // El token arranca en null (no se lee de localStorage): en cada recarga la
  // sesión se restablece en silencio con el refresh token en cookie HttpOnly.
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const login = (newToken: string) => {
    setAccessToken(newToken);
    setToken(newToken);
  };

  const logout = async () => {
    // Esperar a que el backend revoque el refresh token ANTES de poner token
    // en null: si no, el efecto de renovacion silenciosa (dispara al quedar
    // sin token) puede ganarle la carrera al logout y re-loguear solo.
    try {
      await api.post('/login/logout');
    } catch {
      // Igual se limpia el estado local aunque el backend no responda
    }
    setAccessToken(null);
    setToken(null);
    setUser(null);
  };

  useEffect(() => {
    setOnSessionExpired(logout);
  }, []);

  useEffect(() => {
    const loadUser = async () => {
      let currentToken: string | null = token;

      if (currentToken) {
        try {
          const decoded: any = jwtDecode(currentToken);
          if (decoded.exp * 1000 < Date.now()) {
            currentToken = null;
          }
        } catch {
          currentToken = null;
        }
      }

      // Sin access token vigente: intentar renovarlo en silencio con el refresh token (cookie)
      if (!currentToken) {
        try {
          const res = await api.post('/login/refresh-token');
          currentToken = res.data.access_token;
          setAccessToken(currentToken);
          setToken(currentToken);
        } catch {
          logout();
          setIsLoading(false);
          return;
        }
      }

      try {
        const res = await api.get('/users/me');
        setUser(res.data);
      } catch (error) {
        console.error("Error al cargar usuario:", error);
        logout();
      }
      setIsLoading(false);
    };
    loadUser();
  }, [token]);

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};
