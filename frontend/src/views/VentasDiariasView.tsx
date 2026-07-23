/**
 * Ventas Diarias View — Peru/Ecuador: contraentrega por guia
 */
import { useState, useEffect, useCallback } from 'react';
import { ventasDiariasApi, type VentaDiaria, type ResumenMensual } from '../services/ventasDiariasApi';
import { ventasApi, type Producto, type Cliente } from '../services/ventasApi';
import Toast from '../components/Toast';
import ErrorState from '../components/ErrorState';

const ESTADOS = ['Pendiente', 'Entregado', 'En destino', 'Devolución'];

export default function VentasDiariasView() {
  const [ventas, setVentas] = useState<VentaDiaria[]>([]);
  const [resumen, setResumen] = useState<ResumenMensual | null>(null);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [mostrarForm, setMostrarForm] = useState(false);

  const hoy = new Date();
  const [anio] = useState(hoy.getFullYear());
  const [mes] = useState(hoy.getMonth() + 1);

  const cargar = useCallback(() => {
    setLoading(true);
    setError(false);
    Promise.all([
      ventasDiariasApi.list(filtroEstado ? { estado: filtroEstado } : undefined),
      ventasDiariasApi.resumenMensual(anio, mes),
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
  }, [filtroEstado, anio, mes]);

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

      {resumen && (
        <div className="kpi-row">
          <div className="kpi-tile"><span>Venta del mes</span><strong>{resumen.total_venta}</strong></div>
          <div className="kpi-tile"><span>Recaudado</span><strong>{resumen.total_abonado}</strong></div>
          <div className="kpi-tile"><span>Saldo pendiente</span><strong>{resumen.total_saldo}</strong></div>
          <div className="kpi-tile"><span>Entregados</span><strong>{resumen.cantidad_entregado}</strong></div>
          <div className="kpi-tile"><span>Devoluciones</span><strong>{resumen.cantidad_devolucion}</strong></div>
        </div>
      )}

      <div className="toolbar">
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
