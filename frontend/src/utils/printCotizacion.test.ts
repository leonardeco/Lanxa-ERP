import { describe, it, expect, afterEach, vi } from 'vitest';
import { printCotizacion } from './printCotizacion';
import { mockPrintWindow, mockBlockedPopup } from '../test/printWindow';
import type { Cotizacion } from '../services/ventasApi';

const COP = (n: number | string) =>
  Number(n).toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 0 });

function makeCotizacion(overrides: Partial<Cotizacion> = {}): Cotizacion {
  return {
    id: 1,
    numero: 'COT-0001',
    fecha: '2026-07-11',
    vigencia_dias: 15,
    fecha_vencimiento: '2026-07-26',
    cliente_id: 1,
    vendedor: 'Leonardo',
    subtotal: 100000,
    descuento_total: 0,
    base_gravable: 100000,
    iva_total: 19000,
    total: 119000,
    estado: 'Enviada',
    vencida: false,
    created_at: '2026-07-11T10:00:00',
    cliente_razon_social: 'Distribuidora El Ozono S.A.S.',
    cliente_nit: '900123456-7',
    detalles: [
      {
        id: 1,
        producto_id: 1,
        cantidad: 2,
        precio_unitario: 50000,
        descuento_porcentaje: 0,
        subtotal_linea: 100000,
        iva_porcentaje: 19,
        iva_valor: 19000,
        total_linea: 119000,
        created_at: '2026-07-11T10:00:00',
        producto_nombre: 'Generador de Ozono X1',
        producto_sku: 'OZ-X1',
      },
    ],
    ...overrides,
  };
}

afterEach(() => vi.restoreAllMocks());

describe('printCotizacion', () => {
  it('abre una ventana y escribe el HTML de la cotización', () => {
    const { write, close, html } = mockPrintWindow();

    printCotizacion(makeCotizacion());

    expect(write).toHaveBeenCalledTimes(1);
    expect(close).toHaveBeenCalledTimes(1);
    const out = html();
    expect(out).toContain('Cotización');
    expect(out).toContain('COT-0001');
    expect(out).toContain('TOTAL COTIZADO');
    expect(out).toContain(COP(119000));
  });

  it('incluye la vigencia y la aclaración de que no es factura', () => {
    const { html } = mockPrintWindow();

    printCotizacion(makeCotizacion());
    const out = html();

    expect(out).toContain('válida por 15 días');
    expect(out).toContain('no constituye factura de venta');
  });

  it('escapa el markup del cliente', () => {
    const { html } = mockPrintWindow();
    printCotizacion(makeCotizacion({ cliente_razon_social: '<b>x</b>' }));
    const out = html();
    expect(out).not.toContain('<b>x</b>');
    expect(out).toContain('&lt;b&gt;x&lt;/b&gt;');
  });

  it('si el navegador bloquea el popup, avisa', () => {
    const { alertSpy } = mockBlockedPopup();
    printCotizacion(makeCotizacion());
    expect(alertSpy).toHaveBeenCalledTimes(1);
    expect(alertSpy.mock.calls[0][0]).toMatch(/ventana emergente/i);
  });
});
