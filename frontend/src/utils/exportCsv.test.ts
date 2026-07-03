import { describe, it, expect } from 'vitest';
import { generarCsv } from './exportCsv';

describe('generarCsv', () => {
  it('genera BOM, separador ; y CRLF (formato Excel es-CO)', () => {
    const csv = generarCsv(['Código', 'Nombre'], [['130505', 'Clientes']]);
    expect(csv.startsWith('﻿')).toBe(true);
    expect(csv).toContain('Código;Nombre');
    expect(csv).toContain('\r\n130505;Clientes');
  });

  it('formatea números con coma decimal y dos decimales', () => {
    const csv = generarCsv(['Saldo'], [[238000], [1234.5]]);
    expect(csv).toContain('238000,00');
    expect(csv).toContain('1234,50');
  });

  it('escapa textos con separador, comillas y saltos de línea', () => {
    const csv = generarCsv(['Notas'], [['tiene; separador'], ['dijo "hola"'], ['línea\nnueva']]);
    expect(csv).toContain('"tiene; separador"');
    expect(csv).toContain('"dijo ""hola"""');
    expect(csv).toContain('"línea\nnueva"');
  });

  it('celdas null/undefined quedan vacías', () => {
    const csv = generarCsv(['A', 'B', 'C'], [[null, undefined, 'x']]);
    expect(csv).toContain(';;x');
  });
});
