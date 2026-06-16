import type { Compra } from '../services/comprasApi';

const COP = (n: number | string) =>
  Number(n).toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 0 });

const EMPRESA = {
  nombre: 'TECNOLOGÍA E INNOVACIÓN SUPER OZONO S.A.S.',
  nit: '901.841.798-5',
  ciudad: 'Armenia, Quindío — Colombia',
  email: 'info@superozonoglobal.com',
};

export function printCompra(compra: Compra) {
  const fechaFmt = new Date(compra.fecha + 'T00:00:00').toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' });

  const filasDetalle = compra.detalles.map(d => `
    <tr>
      <td>${d.descripcion}</td>
      <td class="num">${Number(d.cantidad)}</td>
      <td class="num">${COP(d.precio_unitario)}</td>
      <td class="num">${Number(d.descuento_porcentaje)}%</td>
      <td class="num">${Number(d.iva_porcentaje)}%</td>
      <td class="num bold">${COP(d.total_linea)}</td>
    </tr>`).join('');

  const filasTotales = [
    ['Subtotal', compra.subtotal],
    Number(compra.descuento_total) > 0 ? ['Descuentos', -Number(compra.descuento_total)] : null,
    ['Base gravable', compra.base_gravable],
    ['IVA', compra.iva_total],
    Number(compra.retefuente) > 0 ? ['ReteFuente (aplicada)', -Number(compra.retefuente)] : null,
    Number(compra.reteiva) > 0 ? ['ReteIVA (aplicada)', -Number(compra.reteiva)] : null,
    Number(compra.reteica) > 0 ? ['ReteICA (aplicada)', -Number(compra.reteica)] : null,
  ].filter(Boolean).map(([label, val]) =>
    `<tr><td>${label}</td><td class="num">${COP(val as number)}</td></tr>`
  ).join('');

  const html = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>${compra.numero}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, sans-serif; font-size: 11px; color: #1a1a1a; background: #fff; padding: 24px; }
    .page { max-width: 800px; margin: 0 auto; }
    .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #2563eb; padding-bottom: 16px; margin-bottom: 16px; }
    .empresa-nombre { font-size: 15px; font-weight: 800; color: #2563eb; }
    .empresa-sub { color: #555; font-size: 10px; margin-top: 2px; }
    .doc-box { border: 2px solid #2563eb; border-radius: 6px; padding: 10px 16px; text-align: center; min-width: 200px; }
    .doc-numero { font-size: 18px; font-weight: 900; color: #2563eb; letter-spacing: 1px; }
    .doc-tipo { font-size: 9px; color: #555; text-transform: uppercase; letter-spacing: 1px; }
    .doc-fecha { font-size: 10px; margin-top: 4px; }
    .doc-estado { display: inline-block; margin-top: 6px; padding: 2px 8px; border-radius: 10px; font-size: 9px; font-weight: 700; background: #dbeafe; color: #2563eb; }
    .seccion { margin-bottom: 14px; }
    .seccion-titulo { font-size: 9px; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 0.8px; border-bottom: 1px solid #e0e0e0; padding-bottom: 3px; margin-bottom: 6px; }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 24px; }
    .campo-label { font-size: 9px; color: #888; }
    .campo-valor { font-size: 11px; font-weight: 600; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 14px; }
    th { background: #2563eb; color: #fff; font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; padding: 6px 8px; text-align: left; }
    td { padding: 5px 8px; border-bottom: 1px solid #f0f0f0; font-size: 10px; }
    tr:nth-child(even) td { background: #f9f9f9; }
    .num { text-align: right; white-space: nowrap; }
    .bold { font-weight: 700; }
    .totales-wrap { display: flex; justify-content: flex-end; margin-bottom: 14px; }
    .totales-box { border: 1px solid #e0e0e0; border-radius: 4px; min-width: 260px; overflow: hidden; }
    .totales-box table { margin: 0; }
    .totales-box td { padding: 4px 12px; border-bottom: 1px solid #f0f0f0; }
    .totales-box tr:last-child td { border-bottom: none; }
    .total-final { background: #2563eb !important; color: #fff !important; font-size: 13px; font-weight: 800; }
    .total-final td { padding: 7px 12px; }
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
      <div class="doc-tipo">Documento de Compra</div>
      <div class="doc-numero">${compra.numero}</div>
      <div class="doc-fecha">Fecha: ${fechaFmt}</div>
      ${compra.ref_proveedor ? `<div class="doc-fecha">Ref. Proveedor: ${compra.ref_proveedor}</div>` : ''}
      <div class="doc-estado">${compra.estado}</div>
    </div>
  </div>

  <div class="seccion">
    <div class="seccion-titulo">Datos del Proveedor</div>
    <div class="info-grid">
      <div>
        <div class="campo-label">Razón Social</div>
        <div class="campo-valor">${compra.proveedor_razon_social ?? '—'}</div>
      </div>
      <div>
        <div class="campo-label">NIT / CC</div>
        <div class="campo-valor">${compra.proveedor_nit ?? '—'}</div>
      </div>
    </div>
  </div>

  <div class="seccion">
    <div class="seccion-titulo">Detalle de Ítems</div>
    <table>
      <thead>
        <tr>
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
            <td>TOTAL A PAGAR</td>
            <td class="num">${COP(compra.total)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  ${compra.observaciones ? `<div class="seccion"><div class="seccion-titulo">Observaciones</div><div style="background:#f8f8f8;padding:8px 12px;font-size:10px;color:#555;border-radius:4px;">${compra.observaciones}</div></div>` : ''}

  <div class="firmas">
    <div class="firma-linea">Autorizado por — ${EMPRESA.nombre}</div>
    <div class="firma-linea">Firma y Sello del Proveedor</div>
  </div>

  <div class="footer">
    ${EMPRESA.nombre} · NIT ${EMPRESA.nit} · Generado el ${new Date().toLocaleString('es-CO')}
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
