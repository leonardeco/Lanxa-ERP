import { describe, it, expect, afterEach, vi } from 'vitest';
import { printFactura } from './printFactura';
import { mockPrintWindow, mockBlockedPopup } from '../test/printWindow';
import type { Venta } from '../services/ventasApi';

// Mismo formateador que usa la utilidad, para no acoplar el test al locale/ICU.
const COP = (n: number | string) =>
  Number(n).toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 0 });

function makeVenta(overrides: Partial<Venta> = {}): Venta {
  return {
    id: 1,
    numero: 'SOG-V-0001',
    fecha: '2026-07-11',
    cliente_id: 1,
    vendedor: 'Leonardo',
    subtotal: 100000,
    descuento_total: 0,
    base_gravable: 100000,
    iva_total: 19000,
    retefuente: 0,
    reteiva: 0,
    reteica: 0,
    total: 119000,
    estado: 'Confirmada',
    estado_pago: 'Pendiente',
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

describe('printFactura', () => {
  it('abre una ventana y escribe el HTML de la factura', () => {
    const { write, close, html } = mockPrintWindow();

    printFactura(makeVenta());

    expect(write).toHaveBeenCalledTimes(1);
    expect(close).toHaveBeenCalledTimes(1);
    const out = html();
    expect(out).toContain('<!DOCTYPE html>');
    expect(out).toContain('Documento de Venta');
    expect(out).toContain('SOG-V-0001');
    expect(out).toContain('TECNOLOGÍA E INNOVACIÓN SUPER OZONO S.A.S.');
    expect(out).toContain('sin resolución DIAN configurada');
  });

  it('incluye bloque de resolución DIAN y aviso Habeas Data cuando se configuran', () => {
    const { html } = mockPrintWindow();

    printFactura(makeVenta(), {
      dian: {
        resolucionNumero: '18760000001',
        resolucionFecha: '2026-01-15',
        prefijo: 'SETT',
        rangoDesde: '1',
        rangoHasta: '5000',
        vigenciaHasta: '2027-01-15',
      },
      habeasDataTexto: 'Autoriza tratamiento de datos personales Ley 1581.',
    });
    const out = html();
    expect(out).toContain('Resolución DIAN Nº 18760000001');
    expect(out).toContain('Prefijo SETT');
    expect(out).toContain('Autoriza tratamiento de datos personales Ley 1581.');
    expect(out).not.toContain('sin resolución DIAN configurada');
  });

  it('incluye cliente, línea de detalle y total formateado', () => {
    const { html } = mockPrintWindow();

    printFactura(makeVenta());
    const out = html();

    expect(out).toContain('Distribuidora El Ozono S.A.S.');
    expect(out).toContain('900123456-7');
    expect(out).toContain('OZ-X1');
    expect(out).toContain('Generador de Ozono X1');
    expect(out).toContain('TOTAL A PAGAR');
    expect(out).toContain(COP(119000));
  });

  it('escapa el markup del cliente para evitar XSS en la ventana de impresión', () => {
    const { html } = mockPrintWindow();

    printFactura(makeVenta({ cliente_razon_social: '<script>alert(1)</script>' }));
    const out = html();

    expect(out).not.toContain('<script>alert(1)</script>');
    expect(out).toContain('&lt;script&gt;alert(1)&lt;/script&gt;');
  });

  it('muestra las filas de retención solo cuando el valor es mayor que cero', () => {
    const { html } = mockPrintWindow();
    printFactura(makeVenta({ retefuente: 5000, reteica: 1000 }));
    const out = html();

    expect(out).toContain('Retención en la Fuente');
    expect(out).toContain('ReteICA');
    // reteiva quedó en 0 → no debe aparecer
    expect(out).not.toContain('ReteIVA');
  });

  it('omite descuentos y retenciones cuando son cero', () => {
    const { html } = mockPrintWindow();
    printFactura(makeVenta());
    const out = html();

    expect(out).not.toContain('Descuentos');
    expect(out).not.toContain('Retención en la Fuente');
  });

  it('si el navegador bloquea el popup, avisa y no escribe nada', () => {
    const { alertSpy } = mockBlockedPopup();
    const write = vi.fn();
    // Aunque no haya ventana, no debe intentar escribir; comprobamos vía alert.
    printFactura(makeVenta());

    expect(alertSpy).toHaveBeenCalledTimes(1);
    expect(alertSpy.mock.calls[0][0]).toMatch(/ventana emergente/i);
    expect(write).not.toHaveBeenCalled();
  });
});
