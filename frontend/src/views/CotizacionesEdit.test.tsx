import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const { updateSpy, createSpy } = vi.hoisted(() => ({
  updateSpy: vi.fn(() => Promise.resolve({ data: {} })),
  createSpy: vi.fn(() => Promise.resolve({ data: {} })),
}));

vi.mock('../services/ventasApi', () => ({
  ventasApi: {
    getClientes: () => Promise.resolve({ data: [
      { id: 7, nit_cc: '900', razon_social: 'Cliente 7', activo: true },
    ] }),
    getProductos: () => Promise.resolve({ data: [
      { id: 3, sku: 'P3', nombre: 'Producto 3', precio_venta: 20000, tarifa_iva: 19, activo: true },
    ] }),
    updateCotizacion: updateSpy,
    createCotizacion: createSpy,
  },
}));

import { NuevaCotizacionModal } from './VentasView';

const cotizacion = {
  id: 42,
  numero: 'COT-0042',
  fecha: '2026-07-06',
  vigencia_dias: 20,
  fecha_vencimiento: '2026-07-26',
  cliente_id: 7,
  vendedor: 'Ana',
  subtotal: 20000, descuento_total: 0, base_gravable: 20000,
  iva_total: 3800, total: 23800,
  estado: 'Borrador',
  vencida: false,
  observaciones: 'nota',
  created_at: '2026-07-06',
  detalles: [{
    id: 1, producto_id: 3, cantidad: 1, precio_unitario: 20000,
    descuento_porcentaje: 0, subtotal_linea: 20000, iva_porcentaje: 19,
    iva_valor: 3800, total_linea: 23800, created_at: '2026-07-06',
  }],
} as any;

describe('NuevaCotizacionModal — modo edición (#25)', () => {
  beforeEach(() => { updateSpy.mockClear(); createSpy.mockClear(); });

  it('en modo edición precarga el vendedor y guarda con updateCotizacion (PUT)', async () => {
    const onCreated = vi.fn();
    const user = userEvent.setup();
    render(<NuevaCotizacionModal cotizacion={cotizacion} onClose={() => {}} onCreated={onCreated} />);

    // Título de edición y datos precargados
    expect(await screen.findByText(/Editar Cotización/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByDisplayValue('Ana')).toBeInTheDocument());

    // Guardar → llama updateCotizacion con el id, NO createCotizacion
    await user.click(screen.getByRole('button', { name: 'Guardar Cambios' }));
    await waitFor(() => expect(updateSpy).toHaveBeenCalledTimes(1));
    expect(updateSpy.mock.calls[0][0]).toBe(42);
    expect(createSpy).not.toHaveBeenCalled();
    expect(onCreated).toHaveBeenCalled();
  });
});
