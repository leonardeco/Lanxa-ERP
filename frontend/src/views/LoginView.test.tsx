import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import LoginView from './LoginView';
import { AuthContext, type AuthContextType } from '../contexts/auth';

vi.mock('../services/api', () => ({
  api: { post: vi.fn() },
  setOnSessionExpired: vi.fn(),
}));

import { api } from '../services/api';

const mockLogin = vi.fn();

const contexto: AuthContextType = {
  user: null,
  token: null,
  login: mockLogin,
  logout: vi.fn().mockResolvedValue(undefined),
  isLoading: false,
};

function renderLogin() {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <AuthContext.Provider value={contexto}>{children}</AuthContext.Provider>
  );
  return render(<LoginView />, { wrapper });
}

describe('LoginView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renderiza el formulario con email, contraseña y botón', () => {
    renderLogin();
    expect(screen.getByText('Correo Electrónico')).toBeInTheDocument();
    expect(screen.getByText('Contraseña')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Acceder al Sistema' })).toBeInTheDocument();
  });

  it('login exitoso: envía credenciales como form-urlencoded y llama login() con el token', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: { access_token: 'jwt-de-prueba' } });
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByPlaceholderText('usuario@lanxa.local'), 'admin@test.com');
    await user.type(screen.getByPlaceholderText('••••••••'), 'clave123');
    await user.click(screen.getByRole('button', { name: 'Acceder al Sistema' }));

    await waitFor(() => expect(mockLogin).toHaveBeenCalledWith('jwt-de-prueba'));

    const [url, body, config] = vi.mocked(api.post).mock.calls[0];
    expect(url).toBe('/login/access-token');
    expect(String(body)).toBe('username=admin%40test.com&password=clave123');
    expect(config?.headers?.['Content-Type']).toBe('application/x-www-form-urlencoded');
  });

  it('login fallido: muestra el detail del backend y no llama login()', async () => {
    vi.mocked(api.post).mockRejectedValueOnce({
      response: { data: { detail: 'Correo o contraseña incorrectos' } },
    });
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByPlaceholderText('usuario@lanxa.local'), 'x@test.com');
    await user.type(screen.getByPlaceholderText('••••••••'), 'mala');
    await user.click(screen.getByRole('button', { name: 'Acceder al Sistema' }));

    expect(await screen.findByText('Correo o contraseña incorrectos')).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('error de red sin response: indica que el servidor no responde (start.bat)', async () => {
    vi.mocked(api.post).mockRejectedValueOnce(new Error('Network Error'));
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByPlaceholderText('usuario@lanxa.local'), 'x@test.com');
    await user.type(screen.getByPlaceholderText('••••••••'), 'clave123');
    await user.click(screen.getByRole('button', { name: 'Acceder al Sistema' }));

    expect(
      await screen.findByText(/No se puede conectar al servidor/i),
    ).toBeInTheDocument();
  });

  it('muestra boton Probar conexion y version', () => {
    renderLogin();
    expect(screen.getByRole('button', { name: /Probar conexión al servidor/i })).toBeInTheDocument();
    expect(screen.getByText(/Portal ERP Corporativo · v0\.3\.0/i)).toBeInTheDocument();
  });

  it('rate limit 429: muestra mensaje de demasiados intentos', async () => {
    vi.mocked(api.post).mockRejectedValueOnce({
      response: { status: 429, data: { error: 'Rate limit exceeded: 5 per 1 minute' } },
    });
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByPlaceholderText('usuario@lanxa.local'), 'x@test.com');
    await user.type(screen.getByPlaceholderText('••••••••'), 'clave123');
    await user.click(screen.getByRole('button', { name: 'Acceder al Sistema' }));

    expect(
      await screen.findByText(/Demasiados intentos de login/i),
    ).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });
});

