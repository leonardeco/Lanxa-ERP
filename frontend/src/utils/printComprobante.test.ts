import { describe, it, expect, afterEach, vi } from 'vitest';
import { printComprobante } from './printComprobante';
import { mockPrintWindow, mockBlockedPopup } from '../test/printWindow';
import type { CxC, CxP, Pago } from '../services/carteraApi';

const COP = (n: number | string) =>
  Number(n).toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 0 });

function makeCxC(overrides: Partial<CxC> = {}): CxC {
  return {
    id: 1,
    numero_factura: 'SOG-V-0001',
    fecha_emision: '2026-07-01',
    cliente_nit: '900123456-7',
    nombre_cliente: 'Distribuidora El Ozono S.A.S.',
    valor_factura: 119000,
    abonos: 50000,
    saldo_pendiente: 69000,
    estado: 'Parcial',
    dias_vencido: 0,
    created_at: '2026-07-01T10:00:00',
    ...overrides,
  };
}

function makeCxP(overrides: Partial<CxP> = {}): CxP {
  return {
    id: 1,
    numero_documento: 'SOG-CP-0001',
    fecha: '2026-07-01',
    proveedor_nit: '890111222-3',
    razon_social: 'Insumos del Quindío Ltda.',
    concepto: 'Compra de insumos',
    valor: 238000,
    abonos: 0,
    saldo_pendiente: 238000,
    estado: 'Pendiente',
    dias_vencido: 0,
    created_at: '2026-07-01T10:00:00',
    ...overrides,
  };
}

function makePago(overrides: Partial<Pago> = {}): Pago {
  return {
    id: 1,
    numero_comprobante: 'RC-0001',
    tipo: 'CxC',
    valor: 50000,
    saldo_anterior: 119000,
    saldo_nuevo: 69000,
    fecha: '2026-07-11T10:00:00',
    created_at: '2026-07-11T10:00:00',
    anulado: false,
    ...overrides,
  };
}

afterEach(() => vi.restoreAllMocks());

describe('printComprobante — CxC (Recibo de Caja)', () => {
  it('rotula como Recibo de Caja y usa los datos del cliente', () => {
    const { write, close, html } = mockPrintWindow();

    printComprobante('CxC', makeCxC(), makePago());

    expect(write).toHaveBeenCalledTimes(1);
    expect(close).toHaveBeenCalledTimes(1);
    const out = html();
    expect(out).toContain('Recibo de Caja');
    expect(out).toContain('Recibido de');
    expect(out).toContain('Cliente');
    expect(out).toContain('Distribuidora El Ozono S.A.S.');
    expect(out).toContain('RC-0001');
    expect(out).toContain('Doc. relacionado: SOG-V-0001');
    expect(out).toContain('Valor recibido');
    expect(out).toContain(COP(50000));
  });

  it('marca estado Parcial cuando queda saldo pendiente', () => {
    const { html } = mockPrintWindow();
    printComprobante('CxC', makeCxC(), makePago({ saldo_nuevo: 69000 }));
    expect(html()).toContain('Parcial');
  });

  it('marca estado Pagado cuando el saldo nuevo llega a cero', () => {
    const { html } = mockPrintWindow();
    printComprobante('CxC', makeCxC(), makePago({ saldo_nuevo: 0 }));
    const out = html();
    expect(out).toContain('Pagado');
    expect(out).not.toContain('Parcial');
  });
});

describe('printComprobante — CxP (Comprobante de Egreso)', () => {
  it('rotula como Comprobante de Egreso y usa los datos del proveedor', () => {
    const { html } = mockPrintWindow();

    printComprobante('CxP', makeCxP(), makePago({ tipo: 'CxP', numero_comprobante: 'CE-0001', saldo_anterior: 238000, valor: 238000, saldo_nuevo: 0 }));
    const out = html();

    expect(out).toContain('Comprobante de Egreso');
    expect(out).toContain('Pagado a');
    expect(out).toContain('Proveedor');
    expect(out).toContain('Insumos del Quindío Ltda.');
    expect(out).toContain('CE-0001');
    expect(out).toContain('Doc. relacionado: SOG-CP-0001');
    expect(out).toContain('Valor pagado');
  });

  it('muestra el concepto de la CxP cuando existe', () => {
    const { html } = mockPrintWindow();
    printComprobante('CxP', makeCxP(), makePago({ tipo: 'CxP' }));
    expect(html()).toContain('Compra de insumos');
  });

  it('omite el concepto cuando no viene', () => {
    const { html } = mockPrintWindow();
    printComprobante('CxP', makeCxP({ concepto: undefined }), makePago({ tipo: 'CxP' }));
    expect(html()).not.toContain('Concepto');
  });
});

describe('printComprobante — seguridad y errores', () => {
  it('escapa el markup de las notas del pago', () => {
    const { html } = mockPrintWindow();
    printComprobante('CxC', makeCxC(), makePago({ notas: '<script>alert(1)</script>' }));
    const out = html();
    expect(out).not.toContain('<script>alert(1)</script>');
    expect(out).toContain('&lt;script&gt;alert(1)&lt;/script&gt;');
  });

  it('si el navegador bloquea el popup, avisa', () => {
    const { alertSpy } = mockBlockedPopup();
    printComprobante('CxC', makeCxC(), makePago());
    expect(alertSpy).toHaveBeenCalledTimes(1);
    expect(alertSpy.mock.calls[0][0]).toMatch(/ventana emergente/i);
  });
});
