import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { AuthContext, useAuth, type AuthContextType, type User } from './auth';

const usuario: User = {
  id: 1,
  email: 'admin@superozonoglobal.com',
  nombre_completo: 'Admin Test',
  rol: 'Superusuario',
  is_active: true,
};

const contexto: AuthContextType = {
  user: usuario,
  token: 'token-de-prueba',
  login: vi.fn(),
  logout: vi.fn().mockResolvedValue(undefined),
  isLoading: false,
};

describe('useAuth', () => {
  it('lanza un error claro si se usa fuera de AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow(
      'useAuth must be used within an AuthProvider',
    );
  });

  it('devuelve el contexto cuando hay un provider', () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <AuthContext.Provider value={contexto}>{children}</AuthContext.Provider>
    );
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.user).toEqual(usuario);
    expect(result.current.token).toBe('token-de-prueba');
    expect(result.current.isLoading).toBe(false);
  });
});
