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
  lotes_por_vencer: number;
  lotes_vencidos: number;
}

export type EstadoLote = 'vigente' | 'por_vencer' | 'vencido' | 'sin_vencimiento';

export interface Lote {
  id: number;
  producto_id: number;
  producto_nombre?: string;
  producto_sku?: string;
  codigo_lote: string;
  fecha_vencimiento?: string;
  cantidad_actual: number;
  costo_unitario?: number;
  origen?: string;
  activo: boolean;
  estado: EstadoLote;
  dias_para_vencer?: number;
}

export interface LotesFiltro {
  producto_id?: number;
  estado?: EstadoLote;
  dias?: number;
  incluir_agotados?: boolean;
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
  codigo_lote?: string;
  fecha_vencimiento?: string;
}

export interface ErrorFilaImport {
  fila: number;
  columna: string;
  mensaje: string;
}

export interface PreviewImport {
  total_filas: number;
  validas: number;
  errores: ErrorFilaImport[];
}

export interface ResumenImport {
  importados: number;
}

export const inventarioApi = {
  getDashboard: () => api.get<InventarioDashboard>(`${BASE}/dashboard`),

  getLotes: (filtros?: LotesFiltro) =>
    api.get<Lote[]>(`${BASE}/lotes`, { params: filtros ?? {} }),

  getMovimientos: (filtros?: MovimientosFiltro) =>
    api.get<MovimientoInventario[]>(`${BASE}/movimientos`, { params: filtros ?? {} }),

  getMovimientosPorProducto: (productoId: number) =>
    api.get<MovimientoInventario[]>(`${BASE}/movimientos/${productoId}`),

  crearAjuste: (data: AjusteInventarioInput) =>
    api.post<MovimientoInventario>(`${BASE}/ajustes`, data),

  descargarPlantilla: () =>
    api.get(`${BASE}/plantilla`, { responseType: 'blob' }),

  validarImport: (file: File) => {
    const fd = new FormData();
    fd.append('archivo', file);
    return api.post<PreviewImport>(`${BASE}/importar`, fd, {
      params: { commit: false },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  confirmarImport: (file: File) => {
    const fd = new FormData();
    fd.append('archivo', file);
    return api.post<ResumenImport>(`${BASE}/importar`, fd, {
      params: { commit: true },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};
