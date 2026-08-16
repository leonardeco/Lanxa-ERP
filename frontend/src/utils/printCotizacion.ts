import type { Cotizacion } from '../services/ventasApi';
import { esc } from './htmlEscape';

const COP = (n: number | string) =>
  Number(n).toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 0 });

const EMPRESA = {
  nombre: 'LANXA S.A.S.',
  nit: '',
  ciudad: '',
  email: 'admin@lanxa.local',
};

export function printCotizacion(cot: Cotizacion) {
  const fmt = (f: string) => new Date(f + 'T00:00:00').toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' });

  const filasDetalle = cot.detalles.map(d => `
    <tr>
      <td class="code">${esc(d.producto_sku ?? '')}</td>
      <td>${esc(d.producto_nombre ?? '')}</td>
      <td class="num">${Number(d.cantidad)}</td>
      <td class="num">${COP(d.precio_unitario)}</td>
      <td class="num">${Number(d.descuento_porcentaje)}%</td>
      <td class="num">${Number(d.iva_porcentaje)}%</td>
      <td class="num bold">${COP(d.total_linea)}</td>
    </tr>`).join('');

  const filasTotales = [
    ['Subtotal', cot.subtotal],
    Number(cot.descuento_total) > 0 ? ['Descuentos', -Number(cot.descuento_total)] : null,
    ['Base gravable', cot.base_gravable],
    ['IVA', cot.iva_total],
  ].filter((row): row is (string | number)[] => row !== null).map(([label, val]) =>
    `<tr><td>${label}</td><td class="num">${COP(val as number)}</td></tr>`
  ).join('');

  const html = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>${cot.numero}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, sans-serif; font-size: 11px; color: #1a1a1a; background: #fff; padding: 24px; }
    .page { max-width: 800px; margin: 0 auto; }
    .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #1a7a5e; padding-bottom: 16px; margin-bottom: 16px; }
    .empresa-nombre { font-size: 15px; font-weight: 800; color: #1a7a5e; }
    .empresa-sub { color: #555; font-size: 10px; margin-top: 2px; }
    .doc-box { border: 2px solid #1a7a5e; border-radius: 6px; padding: 10px 16px; text-align: center; min-width: 180px; }
    .doc-numero { font-size: 18px; font-weight: 900; color: #1a7a5e; letter-spacing: 1px; }
    .doc-tipo { font-size: 9px; color: #555; text-transform: uppercase; letter-spacing: 1px; }
    .doc-fecha { font-size: 10px; margin-top: 4px; }
    .doc-estado { display: inline-block; margin-top: 6px; padding: 2px 8px; border-radius: 10px; font-size: 9px; font-weight: 700; background: #e0f2ec; color: #1a7a5e; }
    .seccion { margin-bottom: 14px; }
    .seccion-titulo { font-size: 9px; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 0.8px; border-bottom: 1px solid #e0e0e0; padding-bottom: 3px; margin-bottom: 6px; }
    .cliente-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 24px; }
    .campo-label { font-size: 9px; color: #888; }
    .campo-valor { font-size: 11px; font-weight: 600; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 14px; }
    th { background: #1a7a5e; color: #fff; font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; padding: 6px 8px; text-align: left; }
    td { padding: 5px 8px; border-bottom: 1px solid #f0f0f0; font-size: 10px; vertical-align: top; }
    tr:nth-child(even) td { background: #f9f9f9; }
    .code { font-family: 'Courier New', monospace; }
    .num { text-align: right; white-space: nowrap; }
    .bold { font-weight: 700; }
    .totales-wrap { display: flex; justify-content: flex-end; margin-bottom: 14px; }
    .totales-box { border: 1px solid #e0e0e0; border-radius: 4px; min-width: 260px; overflow: hidden; }
    .totales-box table { margin: 0; }
    .totales-box td { padding: 4px 12px; border-bottom: 1px solid #f0f0f0; }
    .totales-box tr:last-child td { border-bottom: none; }
    .total-final { background: #1a7a5e !important; color: #fff !important; font-size: 13px; font-weight: 800; }
    .total-final td { padding: 7px 12px; }
    .vigencia-box { background: #fff8e6; border: 1px solid #f0d78c; border-radius: 4px; padding: 8px 12px; font-size: 10px; color: #7a5c00; margin-bottom: 14px; }
    .obs { background: #f8f8f8; border-radius: 4px; padding: 8px 12px; font-size: 10px; color: #555; margin-bottom: 32px; }
    .firmas { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 40px; }
    .firma-linea { border-top: 1px solid #888; padding-top: 4px; font-size: 9px; color: #888; text-align: center; }
    .footer { text-align: center; font-size: 9px; color: #aaa; border-top: 1px solid #eee; padding-top: 10px; margin-top: 10px; }
    @media print {
      body { padding: 0; }
      @page { margin: 14mm 12mm; size: letter portrait; }
    }
  </style>
</head>
<body>
<div class="page">

  <div class="header">
    <div>
      <div class="empresa-nombre">${EMPRESA.nombre}</div>
      <div class="empresa-sub">NIT: ${EMPRESA.nit}</div>
      <div class="empresa-sub">${EMPRESA.ciudad}</div>
      <div class="empresa-sub">${EMPRESA.email}</div>
    </div>
    <div class="doc-box">
      <div class="doc-tipo">Cotización</div>
      <div class="doc-numero">${esc(cot.numero)}</div>
      <div class="doc-fecha">Fecha: ${fmt(cot.fecha)}</div>
      ${cot.vendedor ? `<div class="doc-fecha">Vendedor: ${esc(cot.vendedor)}</div>` : ''}
      <div class="doc-estado">${esc(cot.estado)}</div>
    </div>
  </div>

  <div class="seccion">
    <div class="seccion-titulo">Datos del Cliente</div>
    <div class="cliente-grid">
      <div>
        <div class="campo-label">Razón Social</div>
        <div class="campo-valor">${esc(cot.cliente_razon_social ?? '—')}</div>
      </div>
      <div>
        <div class="campo-label">NIT / CC</div>
        <div class="campo-valor">${esc(cot.cliente_nit ?? '—')}</div>
      </div>
    </div>
  </div>

  <div class="vigencia-box">
    ⏳ <strong>Vigencia:</strong> esta cotización es válida por ${cot.vigencia_dias} días,
    hasta el <strong>${fmt(cot.fecha_vencimiento)}</strong>. Pasada esa fecha los precios
    y disponibilidad están sujetos a confirmación.
  </div>

  <div class="seccion">
    <div class="seccion-titulo">Detalle de Productos Cotizados</div>
    <table>
      <thead>
        <tr>
          <th>SKU</th>
          <th>Descripción</th>
          <th class="num">Cant.</th>
          <th class="num">P. Unitario</th>
          <th class="num">Desc.</th>
          <th class="num">IVA</th>
          <th class="num">Total Línea</th>
        </tr>
      </thead>
      <tbody>${filasDetalle}</tbody>
    </table>
  </div>

  <div class="totales-wrap">
    <div class="totales-box">
      <table>
        <tbody>
          ${filasTotales}
          <tr class="total-final">
            <td>TOTAL COTIZADO</td>
            <td class="num">${COP(cot.total)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  ${cot.observaciones ? `<div class="seccion"><div class="seccion-titulo">Observaciones</div><div class="obs">${esc(cot.observaciones)}</div></div>` : ''}

  <div class="firmas">
    <div class="firma-linea">Elaborada por — ${EMPRESA.nombre}</div>
    <div class="firma-linea">Aceptación del Cliente (firma y fecha)</div>
  </div>

  <div class="footer">
    Este documento es una cotización comercial y no constituye factura de venta.
    <br>${EMPRESA.nombre} · NIT ${EMPRESA.nit} · ${EMPRESA.ciudad}
    &nbsp;·&nbsp; Documento generado el ${new Date().toLocaleString('es-CO')}
  </div>

</div>
<script>window.onload = function() { window.print(); }</script>
</body>
</html>`;

  const win = window.open('', '_blank', 'width=900,height=700');
  if (!win) {
    alert('El navegador bloqueó la ventana emergente. Permite las ventanas emergentes para este sitio.');
    return;
  }
  win.document.write(html);
  win.document.close();
}
