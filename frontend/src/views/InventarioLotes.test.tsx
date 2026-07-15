import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Auth: Admin (para que se muestren todas las pestañas)
vi.mock('../contexts/auth', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'a@a.co', nombre_completo: 'Admin', rol: 'Superusuario', is_active: true },
    token: 'tok', login: vi.fn(), logout: vi.fn(), isLoading: false,
  }),
}));

const dashboard = {
  valor_total_inventario: 1000, productos_stock_bajo: 0, movimientos_mes: 3,
  top_productos_por_valor: [], lotes_por_vencer: 2, lotes_vencidos: 1,
};

const lotes = [
  { id: 1, producto_id: 10, producto_nombre: 'Aceite Ozonizado', producto_sku: 'LOT-1',
    codigo_lote: 'L-PV', fecha_vencimiento: '2027-01-10', cantidad_actual: 5,
    activo: true, estado: 'por_vencer', dias_para_vencer: 12 },
  { id: 2, producto_id: 10, producto_nombre: 'Aceite Ozonizado', producto_sku: 'LOT-1',
    codigo_lote: 'L-OLD', fecha_vencimiento: '2025-01-10', cantidad_actual: 3,
    activo: true, estado: 'vencido', dias_para_vencer: -30 },
];

vi.mock('../services/inventarioApi', () => ({
  inventarioApi: {
    getDashboard: () => Promise.resolve({ data: dashboard }),
    getLotes: () => Promise.resolve({ data: lotes }),
    getMovimientos: () => Promise.resolve({ data: [] }),
  },
}));

vi.mock('../services/ventasApi', () => ({
  ventasApi: { getProductos: () => Promise.resolve({ data: [] }) },
}));

import InventarioView from './InventarioView';

describe('InventarioView — lotes (Capa 4)', () => {
  it('el dashboard muestra los KPIs de vencimiento de lotes', async () => {
    render(<InventarioView />);
    expect(await screen.findByText('Lotes por vencer')).toBeInTheDocument();
    expect(screen.getByText('Lotes vencidos')).toBeInTheDocument();
  });

  it('la pestaña Lotes lista las existencias con su estado de vencimiento', async () => {
    const user = userEvent.setup();
    render(<InventarioView />);
    await user.click(await screen.findByRole('button', { name: /Lotes/ }));

    expect(await screen.findByText('L-PV')).toBeInTheDocument();
    expect(screen.getByText('L-OLD')).toBeInTheDocument();
    expect(screen.getByText('Por vencer')).toBeInTheDocument();
    expect(screen.getByText('Vencido')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/Existencias por Lote/)).toBeInTheDocument());
  });
});
