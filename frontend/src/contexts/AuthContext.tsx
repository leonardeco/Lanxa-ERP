import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, setOnSessionExpired } from '../services/api';
import { jwtDecode } from 'jwt-decode';

export interface User {
  id: number;
  email: string;
  nombre_completo: string;
  rol: string;
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string) => void;
  logout: () => Promise<void>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const login = (newToken: string) => {
    localStorage.setItem('token', newToken);
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
    localStorage.removeItem('token');
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
          localStorage.setItem('token', currentToken as string);
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

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
