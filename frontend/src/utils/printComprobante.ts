import type { CxC, CxP, Pago } from '../services/carteraApi';
import { esc } from './htmlEscape';

const COP = (n: number | string) =>
  Number(n).toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 0 });

const EMPRESA = {
  nombre: 'LANXA S.A.S.',
  nit: '',
  ciudad: '',
  email: 'admin@lanxa.local',
};

export function printComprobante(tipo: 'CxC' | 'CxP', documento: CxC | CxP, pago: Pago) {
  const esCxC = tipo === 'CxC';
  const docTitulo = esCxC ? 'Recibo de Caja' : 'Comprobante de Egreso';

  const terceroNombre = esCxC ? (documento as CxC).nombre_cliente : (documento as CxP).razon_social;
  const terceroNit = esCxC ? (documento as CxC).cliente_nit : (documento as CxP).proveedor_nit;
  const numeroDocumento = esCxC ? (documento as CxC).numero_factura : (documento as CxP).numero_documento;
  const concepto = esCxC ? undefined : (documento as CxP).concepto;

  const fechaFmt = new Date(pago.fecha).toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' });
  const estadoResultante = Number(pago.saldo_nuevo) <= 0 ? 'Pagado' : 'Parcial';

  const html = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>${pago.numero_comprobante}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, sans-serif; font-size: 11px; color: #1a1a1a; background: #fff; padding: 24px; }
    .page { max-width: 800px; margin: 0 auto; }
    .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #2563eb; padding-bottom: 16px; margin-bottom: 16px; }
    .empresa-nombre { font-size: 15px; font-weight: 800; color: #2563eb; }
    .empresa-sub { color: #555; font-size: 10px; margin-top: 2px; }
    .doc-box { border: 2px solid #2563eb; border-radius: 6px; padding: 10px 16px; text-align: center; min-width: 220px; }
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
    td { padding: 5px 8px; border-bottom: 1px solid #f0f0f0; font-size: 11px; }
    .num { text-align: right; white-space: nowrap; }
    .totales-wrap { display: flex; justify-content: flex-end; margin-bottom: 14px; }
    .totales-box { border: 1px solid #e0e0e0; border-radius: 4px; min-width: 280px; overflow: hidden; }
    .totales-box table { margin: 0; }
    .totales-box td { padding: 6px 12px; border-bottom: 1px solid #f0f0f0; }
    .totales-box tr:last-child td { border-bottom: none; }
    .total-final { background: #2563eb !important; color: #fff !important; font-size: 13px; font-weight: 800; }
    .total-final td { padding: 8px 12px; }
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
      <div class="doc-tipo">${docTitulo}</div>
      <div class="doc-numero">${esc(pago.numero_comprobante)}</div>
      <div class="doc-fecha">Fecha: ${fechaFmt}</div>
      <div class="doc-fecha">Doc. relacionado: ${esc(numeroDocumento)}</div>
      <div class="doc-estado">${estadoResultante}</div>
    </div>
  </div>

  <div class="seccion">
    <div class="seccion-titulo">${esCxC ? 'Recibido de' : 'Pagado a'}</div>
    <div class="info-grid">
      <div>
        <div class="campo-label">${esCxC ? 'Cliente' : 'Proveedor'}</div>
        <div class="campo-valor">${esc(terceroNombre ?? '—')}</div>
      </div>
      <div>
        <div class="campo-label">NIT / CC</div>
        <div class="campo-valor">${esc(terceroNit ?? '—')}</div>
      </div>
      ${concepto ? `<div style="grid-column: 1 / -1;"><div class="campo-label">Concepto</div><div class="campo-valor">${esc(concepto)}</div></div>` : ''}
    </div>
  </div>

  <div class="totales-wrap">
    <div class="totales-box">
      <table>
        <tbody>
          <tr><td>Saldo anterior</td><td class="num">${COP(pago.saldo_anterior)}</td></tr>
          <tr><td>${esCxC ? 'Valor recibido' : 'Valor pagado'}</td><td class="num">${COP(pago.valor)}</td></tr>
          <tr class="total-final">
            <td>SALDO PENDIENTE</td>
            <td class="num">${COP(pago.saldo_nuevo)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  ${pago.notas ? `<div class="seccion"><div class="seccion-titulo">Notas / Referencia de pago</div><div style="background:#f8f8f8;padding:8px 12px;font-size:10px;color:#555;border-radius:4px;">${esc(pago.notas)}</div></div>` : ''}

  <div class="firmas">
    <div class="firma-linea">${esCxC ? `Recibido por — ${EMPRESA.nombre}` : 'Firma de quien autoriza el pago'}</div>
    <div class="firma-linea">${esCxC ? 'Firma de quien entrega' : `Recibido por — ${esc(terceroNombre ?? '')}`}</div>
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
