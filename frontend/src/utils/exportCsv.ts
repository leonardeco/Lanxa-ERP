/**
 * Exportación a CSV compatible con Excel en español (Colombia):
 * - BOM UTF-8 para que Excel respete tildes y eñes.
 * - Separador ';' (el separador de listas del locale es-CO).
 * - Números con coma decimal y sin separador de miles, para que Excel
 *   los reconozca como numéricos.
 */

export type CeldaCsv = string | number | null | undefined;

function formatearCelda(valor: CeldaCsv): string {
  if (valor === null || valor === undefined) return '';
  if (typeof valor === 'number') {
    // coma decimal, sin miles — Excel es-CO lo parsea como número
    return valor.toFixed(2).replace('.', ',');
  }
  const texto = String(valor);
  // Escapar si contiene separador, comillas o saltos de línea
  if (/[;"\n\r]/.test(texto)) {
    return `"${texto.replace(/"/g, '""')}"`;
  }
  return texto;
}

export function generarCsv(encabezados: string[], filas: CeldaCsv[][]): string {
  const lineas = [
    encabezados.map(formatearCelda).join(';'),
    ...filas.map(fila => fila.map(formatearCelda).join(';')),
  ];
  return '﻿' + lineas.join('\r\n');
}

export function descargarCsv(nombreArchivo: string, encabezados: string[], filas: CeldaCsv[][]): void {
  const csv = generarCsv(encabezados, filas);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = nombreArchivo.endsWith('.csv') ? nombreArchivo : `${nombreArchivo}.csv`;
  document.body.appendChild(enlace);
  enlace.click();
  document.body.removeChild(enlace);
  URL.revokeObjectURL(url);
}
