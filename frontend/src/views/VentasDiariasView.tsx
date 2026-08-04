/**
 * Ventas Diarias View — Peru/Ecuador: contraentrega por guia
 */
import { useState, useEffect, useCallback } from 'react';
import { ventasDiariasApi, type VentaDiaria, type ResumenMensual } from '../services/ventasDiariasApi';
import { ventasApi, type Producto, type Cliente } from '../services/ventasApi';
import Toast from '../components/Toast';
import ErrorState from '../components/ErrorState';

const ESTADOS = ['Pendiente', 'Entregado', 'En destino', 'Devolución'];

const PAISES = [
  { label: '🇨🇴 Colombia', tenant_id: 1 },
  { label: '🇵🇪 Perú',     tenant_id: 2 },
  { label: '🇪🇨 Ecuador',  tenant_id: 3 },
];

// Mes anterior al actual (donde hay datos del Excel)
function ultimoMesConDatos() {
  const hoy = new Date();
  const mes = hoy.getMonth(); // getMonth() devuelve 0-based, si es 0 usamos dic del año anterior
  return {
    anio: mes === 0 ? hoy.getFullYear() - 1 : hoy.getFullYear(),
    mes: mes === 0 ? 12 : mes,
  };
}

const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

export default function VentasDiariasView({ defaultTenantId = 2 }: { defaultTenantId?: number }) {
  const [ventas, setVentas] = useState<VentaDiaria[]>([]);
  const [resumen, setResumen] = useState<ResumenMensual | null>(null);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [filtroFechaDesde, setFiltroFechaDesde] = useState('');
  const [filtroFechaHasta, setFiltroFechaHasta] = useState('');
  const [paisTenantId, setPaisTenantId] = useState<number>(defaultTenantId);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [mostrarForm, setMostrarForm] = useState(false);

  const defMes = ultimoMesConDatos();
  const [anio, setAnio] = useState(defMes.anio);
  const [mes, setMes] = useState(defMes.mes);

  const cargar = useCallback(() => {
    setLoading(true);
    setError(false);
    const params: { estado?: string; ver_tenant_id?: number; fecha_desde?: string; fecha_hasta?: string } = {};
    if (filtroEstado) params.estado = filtroEstado;
    if (filtroFechaDesde) params.fecha_desde = filtroFechaDesde;
    if (filtroFechaHasta) params.fecha_hasta = filtroFechaHasta;
    params.ver_tenant_id = paisTenantId;
    Promise.all([
      ventasDiariasApi.list(params),
      ventasDiariasApi.resumenMensual(anio, mes, paisTenantId),
      ventasApi.getProductos(),
      ventasApi.getClientes(),
    ])
      .then(([v, r, p, c]) => {
        setVentas(v.data);
        setResumen(r.data);
        setProductos(p.data);
        setClientes(c.data);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [filtroEstado, filtroFechaDesde, filtroFechaHasta, anio, mes, paisTenantId]);

  useEffect(() => { cargar(); }, [cargar]);

  const crearVentaRapida = async (form: {
    fecha: string; asesor: string; guia: string; cliente_id: number;
    producto_id: number; cantidad: number; venta: number; abono_1: number; estado: string;
  }) => {
    try {
      await ventasDiariasApi.create({
        fecha: form.fecha,
        asesor: form.asesor || undefined,
        guia: form.guia || undefined,
        cliente_id: form.cliente_id,
        estado: form.estado,
        detalles: [{
          producto_id: form.producto_id,
          cantidad: form.cantidad,
          venta: form.venta,
          abono_1: form.abono_1 || undefined,
        }],
      });
      setToast({ message: 'Venta diaria registrada', type: 'success' });
      setMostrarForm(false);
      cargar();
    } catch {
      setToast({ message: 'Error al registrar la venta diaria', type: 'error' });
    }
  };

  if (loading) return <div className="empty-state fade-in"><div className="empty-state-text">Cargando ventas diarias...</div></div>;
  if (error) return <ErrorState mensaje="Error al cargar ventas diarias" onRetry={cargar} />;

  return (
    <div className="fade-in">
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

      {/* KPI del mes seleccionado */}
      {resumen && (
        <div className="kpi-row">
          <div className="kpi-tile"><span>Venta {MESES[mes-1]} {anio}</span><strong>{Number(resumen.total_venta).toLocaleString('es-CO', {style:'currency',currency:'COP',maximumFractionDigits:0})}</strong></div>
          <div className="kpi-tile"><span>Recaudado</span><strong>{Number(resumen.total_abonado).toLocaleString('es-CO', {style:'currency',currency:'COP',maximumFractionDigits:0})}</strong></div>
          <div className="kpi-tile"><span>Saldo pendiente</span><strong style={{color: Number(resumen.total_saldo) > 0 ? 'var(--amber-400)' : undefined}}>{Number(resumen.total_saldo).toLocaleString('es-CO', {style:'currency',currency:'COP',maximumFractionDigits:0})}</strong></div>
          <div className="kpi-tile"><span>Entregados</span><strong style={{color:'var(--oz-green-400)'}}>{resumen.cantidad_entregado}</strong></div>
          <div className="kpi-tile"><span>Devoluciones</span><strong style={{color:'var(--red-400)'}}>{resumen.cantidad_devolucion}</strong></div>
        </div>
      )}

      <div className="toolbar" style={{flexWrap:'wrap', gap: 8}}>
        {/* Selector de mes/año para KPIs */}
        <div style={{display:'flex', alignItems:'center', gap:6, background:'rgba(0,0,0,0.2)', borderRadius:8, padding:'4px 10px'}}>
          <span style={{fontSize:'0.75rem', color:'var(--neutral-400)'}}>KPI:</span>
          <select value={mes} onChange={e => setMes(Number(e.target.value))} style={{fontSize:'0.8rem', padding:'3px 6px'}}>
            {MESES.map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
          </select>
          <select value={anio} onChange={e => setAnio(Number(e.target.value))} style={{fontSize:'0.8rem', padding:'3px 6px'}}>
            {[2024,2025,2026].map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>

        {/* Filtro por fecha */}
        <div style={{display:'flex', alignItems:'center', gap:6, background:'rgba(0,0,0,0.2)', borderRadius:8, padding:'4px 10px'}}>
          <span style={{fontSize:'0.75rem', color:'var(--neutral-400)'}}>Desde:</span>
          <input type="date" value={filtroFechaDesde} onChange={e => setFiltroFechaDesde(e.target.value)} style={{fontSize:'0.8rem', padding:'3px 6px'}} />
          <span style={{fontSize:'0.75rem', color:'var(--neutral-400)'}}>Hasta:</span>
          <input type="date" value={filtroFechaHasta} onChange={e => setFiltroFechaHasta(e.target.value)} style={{fontSize:'0.8rem', padding:'3px 6px'}} />
        </div>

        <select value={filtroEstado} onChange={e => setFiltroEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS.map(e => <option key={e} value={e}>{e}</option>)}
        </select>
        <button onClick={() => setMostrarForm(true)}>+ Nueva venta diaria</button>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Fecha</th><th>Asesor</th><th>Guía</th><th>Cliente</th>
            <th>Producto</th><th>Venta</th><th>Saldo</th><th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {ventas.map(v => (
            <tr key={v.id}>
              <td>{v.fecha}</td>
              <td>{v.asesor}</td>
              <td>{v.guia}</td>
              <td>{clientes.find(c => c.id === v.cliente_id)?.razon_social ?? v.cliente_id}</td>
              <td>{v.detalles.map(d => productos.find(p => p.id === d.producto_id)?.nombre ?? d.producto_id).join(', ')}</td>
              <td>{v.detalles.reduce((acc, d) => acc + Number(d.venta ?? 0), 0)}</td>
              <td>{v.detalles.reduce((acc, d) => acc + Number(d.saldo), 0)}</td>
              <td>{v.estado}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {mostrarForm && (
        <VentaDiariaForm
          productos={productos}
          clientes={clientes}
          onCancel={() => setMostrarForm(false)}
          onSubmit={crearVentaRapida}
        />
      )}
    </div>
  );
}

function VentaDiariaForm({ productos, clientes, onCancel, onSubmit }: {
  productos: Producto[];
  clientes: Cliente[];
  onCancel: () => void;
  onSubmit: (form: {
    fecha: string; asesor: string; guia: string; cliente_id: number;
    producto_id: number; cantidad: number; venta: number; abono_1: number; estado: string;
  }) => void;
}) {
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [asesor, setAsesor] = useState('');
  const [guia, setGuia] = useState('');
  const [clienteId, setClienteId] = useState(clientes[0]?.id ?? 0);
  const [productoId, setProductoId] = useState(productos[0]?.id ?? 0);
  const [cantidad, setCantidad] = useState(1);
  const [venta, setVenta] = useState(0);
  const [abono1, setAbono1] = useState(0);
  const [estado, setEstado] = useState('Pendiente');

  const saldo = venta - abono1;

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h3>Nueva venta diaria</h3>
        <label>Fecha <input type="date" value={fecha} onChange={e => setFecha(e.target.value)} /></label>
        <label>Asesor <input value={asesor} onChange={e => setAsesor(e.target.value)} /></label>
        <label>Guía <input value={guia} onChange={e => setGuia(e.target.value)} /></label>
        <label>Cliente
          <select value={clienteId} onChange={e => setClienteId(Number(e.target.value))}>
            {clientes.map(c => <option key={c.id} value={c.id}>{c.razon_social}</option>)}
          </select>
        </label>
        <label>Producto
          <select value={productoId} onChange={e => setProductoId(Number(e.target.value))}>
            {productos.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select>
        </label>
        <label>Cantidad <input type="number" value={cantidad} onChange={e => setCantidad(Number(e.target.value))} /></label>
        <label>Venta <input type="number" value={venta} onChange={e => setVenta(Number(e.target.value))} /></label>
        <label>Abono <input type="number" value={abono1} onChange={e => setAbono1(Number(e.target.value))} /></label>
        <div>Saldo calculado: {saldo}</div>
        <label>Estado
          <select value={estado} onChange={e => setEstado(e.target.value)}>
            {ESTADOS_FORM.map(e => <option key={e} value={e}>{e}</option>)}
          </select>
        </label>
        <div className="modal-actions">
          <button onClick={onCancel}>Cancelar</button>
          <button onClick={() => onSubmit({
            fecha, asesor, guia, cliente_id: clienteId, producto_id: productoId,
            cantidad, venta, abono_1: abono1, estado,
          })}>Guardar</button>
        </div>
      </div>
    </div>
  );
}

const ESTADOS_FORM = ['Pendiente', 'Entregado', 'En destino', 'Devolución'];
