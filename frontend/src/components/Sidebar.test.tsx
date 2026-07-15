import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Sidebar from './Sidebar';
import type { ViewId } from '../App';

const baseProps = {
  activeView: 'dashboard' as ViewId,
  onViewChange: vi.fn(),
  onLogout: vi.fn(),
  userName: 'Leonardo Guzmán',
};

describe('Sidebar — gating por rol', () => {
  it('Admin ve todos los módulos, incluida la administración de usuarios', () => {
    render(
      <Sidebar
        {...baseProps}
        activeRole="Superusuario"
        allowedViews={[
          'dashboard', 'puc', 'centros-costo', 'periodos', 'tributarios', 'nomina',
          'ventas', 'compras', 'cartera', 'inventario', 'rrhh', 'plataformas',
          'reportes', 'usuarios',
        ]}
      />,
    );
    expect(screen.getByText('Usuarios & Accesos')).toBeInTheDocument();
    expect(screen.getByText('Reportes & BI')).toBeInTheDocument();
    expect(screen.getByText('Plan de Cuentas (PUC)')).toBeInTheDocument();
    // Los módulos 🚧 (Fase 2+) no aparecen en el menú aunque el rol los permita
    expect(screen.queryByText('Talento Humano')).not.toBeInTheDocument();
    expect(screen.queryByText('Plataformas')).not.toBeInTheDocument();
  });

  it('Auxiliar solo ve sus 4 módulos — sin contabilidad ni usuarios', () => {
    render(
      <Sidebar
        {...baseProps}
        activeRole="Auxiliar Contable"
        allowedViews={['dashboard', 'ventas', 'compras', 'cartera']}
      />,
    );
    expect(screen.getByText('Ventas & Comercial')).toBeInTheDocument();
    expect(screen.getByText('Cartera CxC & CxP')).toBeInTheDocument();
    expect(screen.queryByText('Usuarios & Accesos')).not.toBeInTheDocument();
    expect(screen.queryByText('Plan de Cuentas (PUC)')).not.toBeInTheDocument();
    // La sección "Contabilidad" desaparece completa si no tiene ítems visibles
    expect(screen.queryByText('Contabilidad')).not.toBeInTheDocument();
  });

  it('navegar llama onViewChange con el id de la vista', async () => {
    const onViewChange = vi.fn();
    const user = userEvent.setup();
    render(
      <Sidebar
        {...baseProps}
        onViewChange={onViewChange}
        activeRole="Auxiliar Contable"
        allowedViews={['dashboard', 'ventas']}
      />,
    );
    await user.click(screen.getByText('Ventas & Comercial'));
    expect(onViewChange).toHaveBeenCalledWith('ventas');
  });

  it('muestra iniciales, rol y permite cerrar sesión', async () => {
    const onLogout = vi.fn();
    const user = userEvent.setup();
    render(
      <Sidebar
        {...baseProps}
        onLogout={onLogout}
        activeRole="Directora"
        allowedViews={['dashboard']}
      />,
    );
    expect(screen.getByText('LG')).toBeInTheDocument(); // iniciales de Leonardo Guzmán
    expect(screen.getByText('Directora')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Cerrar Sesión/ }));
    expect(onLogout).toHaveBeenCalled();
  });

  it('el toggle colapsa el menú (oculta labels, conserva navegación)', async () => {
    const user = userEvent.setup();
    render(
      <Sidebar {...baseProps} activeRole="Superusuario" allowedViews={['dashboard', 'ventas']} />,
    );
    expect(screen.getByText('Ventas & Comercial')).toBeInTheDocument();

    await user.click(screen.getByTitle('Colapsar menú'));
    expect(screen.queryByText('Ventas & Comercial')).not.toBeInTheDocument();
    // El botón sigue ahí, ahora identificado por title
    expect(screen.getByTitle('Ventas & Comercial')).toBeInTheDocument();
  });
});
