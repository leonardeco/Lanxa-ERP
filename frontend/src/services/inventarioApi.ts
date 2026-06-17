import { api } from './api';

const BASE = '/v1/inventario';

export interface MovimientoInventario {
  id: number;
  producto_id: number;
  producto_nombre?: string;
  producto_sku?: string;
  tipo: string;
  origen: string;
  cantidad: number;
  stock_antes: number;
  stock_despues: number;
  costo_unitario?: number;
  compra_id?: number;
  venta_id?: number;
  motivo?: string;
  usuario_id?: number;
  fecha: string;
  created_at: string;
}

export interface TopProductoValor {
  producto: string;
  sku: string;
  valor: number;
}

export interface InventarioDashboard {
  valor_total_inventario: number;
  productos_stock_bajo: number;
  movimientos_mes: number;
  top_productos_por_valor: TopProductoValor[];
}

export interface MovimientosFiltro {
  producto_id?: number;
  tipo?: string;
  origen?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
}

export interface AjusteInventarioInput {
  producto_id: number;
  tipo: 'Entrada' | 'Salida';
  cantidad: number;
  motivo?: string;
}

export const inventarioApi = {
  getDashboard: () => api.get<InventarioDashboard>(`${BASE}/dashboard`),

  getMovimientos: (filtros?: MovimientosFiltro) =>
    api.get<MovimientoInventario[]>(`${BASE}/movimientos`, { params: filtros ?? {} }),

  getMovimientosPorProducto: (productoId: number) =>
    api.get<MovimientoInventario[]>(`${BASE}/movimientos/${productoId}`),

  crearAjuste: (data: AjusteInventarioInput) =>
    api.post<MovimientoInventario>(`${BASE}/ajustes`, data),
};
