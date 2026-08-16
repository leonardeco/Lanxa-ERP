import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Spies compartidos con los mocks (vi.mock se eleva por encima de los imports).
const { logoutSpy, confirmarSpy } = vi.hoisted(() => ({
  logoutSpy: vi.fn(),
  confirmarSpy: vi.fn(),
}));

vi.mock('./contexts/auth', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: 'admin@lanxa.local',
      nombre_completo: 'Leonardo Guzmán',
      rol: 'Superusuario',
      is_active: true,
    },
    token: 'tok',
    login: vi.fn(),
    logout: logoutSpy,
    isLoading: false,
  }),
}));

vi.mock('./utils/unsavedGuard', () => ({
  confirmarDescartar: confirmarSpy,
}));

// Vistas/paneles pesados: stubs para que App renderice barato y sin red.
vi.mock('./views/DashboardView', () => ({ default: () => null }));
vi.mock('./components/HeaderBar', () => ({ default: () => null }));
vi.mock('./components/StatusBar', () => ({ default: () => null }));

import App from './App';

describe('App — el logout pasa por el guard de datos sin guardar (#26)', () => {
  beforeEach(() => {
    logoutSpy.mockClear();
    confirmarSpy.mockReset();
  });

  it('con datos sin guardar y el usuario cancela, NO cierra sesión', async () => {
    confirmarSpy.mockReturnValue(false);
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /Cerrar Sesión/ }));

    expect(confirmarSpy).toHaveBeenCalled();
    expect(logoutSpy).not.toHaveBeenCalled();
  });

  it('sin datos sin guardar (o el usuario confirma el descarte), cierra sesión', async () => {
    confirmarSpy.mockReturnValue(true);
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /Cerrar Sesión/ }));

    expect(confirmarSpy).toHaveBeenCalled();
    expect(logoutSpy).toHaveBeenCalledTimes(1);
  });
});
