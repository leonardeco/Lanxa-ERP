import type { Venta } from '../services/ventasApi';
import { esc } from './htmlEscape';

const COP = (n: number | string) =>
  Number(n).toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 0 });

const EMPRESA = {
  nombre: 'TECNOLOGÍA E INNOVACIÓN SUPER OZONO S.A.S.',
  nit: '901.841.798-5',
  ciudad: 'Armenia, Quindío — Colombia',
  email: 'info@superozonoglobal.com',
};

export function printFactura(venta: Venta) {
  const fechaFmt = new Date(venta.fecha + 'T00:00:00').toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' });

  const filasDetalle = venta.detalles.map(d => `
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
    ['Subtotal', venta.subtotal],
    Number(venta.descuento_total) > 0 ? ['Descuentos', -Number(venta.descuento_total)] : null,
    ['Base gravable', venta.base_gravable],
    ['IVA', venta.iva_total],
    Number(venta.retefuente) > 0 ? ['Retención en la Fuente', -Number(venta.retefuente)] : null,
    Number(venta.reteiva) > 0 ? ['ReteIVA', -Number(venta.reteiva)] : null,
    Number(venta.reteica) > 0 ? ['ReteICA', -Number(venta.reteica)] : null,
  ].filter((row): row is (string | number)[] => row !== null).map(([label, val]) =>
    `<tr><td>${label}</td><td class="num">${COP(val as number)}</td></tr>`
  ).join('');

  const html = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>${venta.numero}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, sans-serif; font-size: 11px; color: #1a1a1a; background: #fff; padding: 24px; }
    .page { max-width: 800px; margin: 0 auto; }

    /* Header */
    .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #1a7a5e; padding-bottom: 16px; margin-bottom: 16px; }
    .empresa-nombre { font-size: 15px; font-weight: 800; color: #1a7a5e; }
    .empresa-sub { color: #555; font-size: 10px; margin-top: 2px; }
    .doc-box { border: 2px solid #1a7a5e; border-radius: 6px; padding: 10px 16px; text-align: center; min-width: 180px; }
    .doc-numero { font-size: 18px; font-weight: 900; color: #1a7a5e; letter-spacing: 1px; }
    .doc-tipo { font-size: 9px; color: #555; text-transform: uppercase; letter-spacing: 1px; }
    .doc-fecha { font-size: 10px; margin-top: 4px; }
    .doc-estado { display: inline-block; margin-top: 6px; padding: 2px 8px; border-radius: 10px; font-size: 9px; font-weight: 700; background: #e0f2ec; color: #1a7a5e; }

    /* Cliente */
    .seccion { margin-bottom: 14px; }
    .seccion-titulo { font-size: 9px; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 0.8px; border-bottom: 1px solid #e0e0e0; padding-bottom: 3px; margin-bottom: 6px; }
    .cliente-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 24px; }
    .campo { }
    .campo-label { font-size: 9px; color: #888; }
    .campo-valor { font-size: 11px; font-weight: 600; }

    /* Tabla de productos */
    table { width: 100%; border-collapse: collapse; margin-bottom: 14px; }
    th { background: #1a7a5e; color: #fff; font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; padding: 6px 8px; text-align: left; }
    td { padding: 5px 8px; border-bottom: 1px solid #f0f0f0; font-size: 10px; vertical-align: top; }
    tr:nth-child(even) td { background: #f9f9f9; }
    .code { font-family: 'Courier New', monospace; }
    .num { text-align: right; white-space: nowrap; }
    .bold { font-weight: 700; }

    /* Totales */
    .totales-wrap { display: flex; justify-content: flex-end; margin-bottom: 14px; }
    .totales-box { border: 1px solid #e0e0e0; border-radius: 4px; min-width: 260px; overflow: hidden; }
    .totales-box table { margin: 0; }
    .totales-box td { padding: 4px 12px; border-bottom: 1px solid #f0f0f0; }
    .totales-box tr:last-child td { border-bottom: none; }
    .total-final { background: #1a7a5e !important; color: #fff !important; font-size: 13px; font-weight: 800; }
    .total-final td { padding: 7px 12px; }

    /* Observaciones y firma */
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

  <!-- Encabezado -->
  <div class="header">
    <div>
      <div class="empresa-nombre">${EMPRESA.nombre}</div>
      <div class="empresa-sub">NIT: ${EMPRESA.nit}</div>
      <div class="empresa-sub">${EMPRESA.ciudad}</div>
      <div class="empresa-sub">${EMPRESA.email}</div>
    </div>
    <div class="doc-box">
      <div class="doc-tipo">Documento de Venta</div>
      <div class="doc-numero">${esc(venta.numero)}</div>
      <div class="doc-fecha">Fecha: ${fechaFmt}</div>
      ${venta.vendedor ? `<div class="doc-fecha">Vendedor: ${esc(venta.vendedor)}</div>` : ''}
      <div class="doc-estado">${esc(venta.estado)}</div>
    </div>
  </div>

  <!-- Cliente -->
  <div class="seccion">
    <div class="seccion-titulo">Datos del Cliente</div>
    <div class="cliente-grid">
      <div class="campo">
        <div class="campo-label">Razón Social</div>
        <div class="campo-valor">${esc(venta.cliente_razon_social ?? '—')}</div>
      </div>
      <div class="campo">
        <div class="campo-label">NIT / CC</div>
        <div class="campo-valor">${esc(venta.cliente_nit ?? '—')}</div>
      </div>
    </div>
  </div>

  <!-- Líneas de detalle -->
  <div class="seccion">
    <div class="seccion-titulo">Detalle de Productos</div>
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

  <!-- Totales -->
  <div class="totales-wrap">
    <div class="totales-box">
      <table>
        <tbody>
          ${filasTotales}
          <tr class="total-final">
            <td>TOTAL A PAGAR</td>
            <td class="num">${COP(venta.total)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  ${venta.observaciones ? `<div class="seccion"><div class="seccion-titulo">Observaciones</div><div class="obs">${esc(venta.observaciones)}</div></div>` : ''}

  <!-- Firmas -->
  <div class="firmas">
    <div class="firma-linea">Firma Autorizada — ${EMPRESA.nombre}</div>
    <div class="firma-linea">Firma y Sello del Cliente</div>
  </div>

  <div class="footer">
    ${EMPRESA.nombre} · NIT ${EMPRESA.nit} · ${EMPRESA.ciudad}
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
