import { describe, it, expect, afterEach, vi } from 'vitest';
import { printCompra } from './printCompra';
import { mockPrintWindow, mockBlockedPopup } from '../test/printWindow';
import type { Compra } from '../services/comprasApi';

const COP = (n: number | string) =>
  Number(n).toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 0 });

function makeCompra(overrides: Partial<Compra> = {}): Compra {
  return {
    id: 1,
    numero: 'SOG-CP-0001',
    fecha: '2026-07-11',
    proveedor_id: 1,
    proveedor_razon_social: 'Insumos del Quindío Ltda.',
    proveedor_nit: '890111222-3',
    ref_proveedor: 'FAC-4455',
    subtotal: 200000,
    descuento_total: 0,
    base_gravable: 200000,
    iva_total: 38000,
    retefuente: 0,
    reteiva: 0,
    reteica: 0,
    total: 238000,
    estado: 'Confirmada',
    estado_pago: 'Pendiente',
    created_at: '2026-07-11T10:00:00',
    detalles: [
      {
        id: 1,
        compra_id: 1,
        descripcion: 'Peróxido de hidrógeno 50L',
        cantidad: 4,
        precio_unitario: 50000,
        descuento_porcentaje: 0,
        iva_porcentaje: 19,
        subtotal_linea: 200000,
        iva_valor: 38000,
        total_linea: 238000,
        created_at: '2026-07-11T10:00:00',
      },
    ],
    ...overrides,
  };
}

afterEach(() => vi.restoreAllMocks());

describe('printCompra', () => {
  it('abre una ventana y escribe el HTML de la compra', () => {
    const { write, close, html } = mockPrintWindow();

    printCompra(makeCompra());

    expect(write).toHaveBeenCalledTimes(1);
    expect(close).toHaveBeenCalledTimes(1);
    const out = html();
    expect(out).toContain('Documento de Compra');
    expect(out).toContain('SOG-CP-0001');
  });

  it('incluye proveedor, ítem, ref. proveedor y total formateado', () => {
    const { html } = mockPrintWindow();

    printCompra(makeCompra());
    const out = html();

    expect(out).toContain('Insumos del Quindío Ltda.');
    expect(out).toContain('890111222-3');
    expect(out).toContain('Peróxido de hidrógeno 50L');
    expect(out).toContain('Ref. Proveedor: FAC-4455');
    expect(out).toContain('TOTAL A PAGAR');
    expect(out).toContain(COP(238000));
  });

  it('omite la referencia del proveedor cuando no viene', () => {
    const { html } = mockPrintWindow();
    printCompra(makeCompra({ ref_proveedor: undefined }));
    expect(html()).not.toContain('Ref. Proveedor:');
  });

  it('escapa el markup de la descripción del ítem', () => {
    const { html } = mockPrintWindow();
    printCompra(
      makeCompra({
        detalles: [
          {
            id: 1,
            compra_id: 1,
            descripcion: '<img src=x onerror=alert(1)>',
            cantidad: 1,
            precio_unitario: 100,
            descuento_porcentaje: 0,
            iva_porcentaje: 0,
            subtotal_linea: 100,
            iva_valor: 0,
            total_linea: 100,
            created_at: '2026-07-11T10:00:00',
          },
        ],
      }),
    );
    const out = html();
    expect(out).not.toContain('<img src=x onerror=alert(1)>');
    expect(out).toContain('&lt;img src=x onerror=alert(1)&gt;');
  });

  it('muestra las retenciones aplicadas solo cuando son mayores que cero', () => {
    const { html } = mockPrintWindow();
    printCompra(makeCompra({ retefuente: 7000 }));
    const out = html();
    expect(out).toContain('ReteFuente (aplicada)');
    expect(out).not.toContain('ReteIVA (aplicada)');
  });

  it('si el navegador bloquea el popup, avisa', () => {
    const { alertSpy } = mockBlockedPopup();
    printCompra(makeCompra());
    expect(alertSpy).toHaveBeenCalledTimes(1);
    expect(alertSpy.mock.calls[0][0]).toMatch(/ventana emergente/i);
  });
});
