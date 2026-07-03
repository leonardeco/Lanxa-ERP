import { api } from './api';

const BASE = '/v1/compras';

export interface Proveedor {
  id: number;
  nit_cc: string;
  dv?: string;
  razon_social: string;
  nombre_comercial?: string;
  tipo_persona: string;
  regimen_iva: string;
  categoria?: string;
  direccion?: string;
  ciudad?: string;
  departamento?: string;
  telefono?: string;
  celular?: string;
  email?: string;
  contacto_nombre?: string;
  contacto_cargo?: string;
  dias_credito: number;
  activo: boolean;
  notas?: string;
  created_at: string;
  updated_at?: string;
}

export interface CompraDetalle {
  id: number;
  compra_id: number;
  producto_id?: number;
  descripcion: string;
  cantidad: number;
  precio_unitario: number;
  descuento_porcentaje: number;
  iva_porcentaje: number;
  subtotal_linea: number;
  iva_valor: number;
  total_linea: number;
  created_at: string;
}

export interface Compra {
  id: number;
  numero: string;
  fecha: string;
  fecha_vencimiento?: string;
  proveedor_id: number;
  proveedor_razon_social?: string;
  proveedor_nit?: string;
  ref_proveedor?: string;
  subtotal: number;
  descuento_total: number;
  base_gravable: number;
  iva_total: number;
  retefuente: number;
  reteiva: number;
  reteica: number;
  total: number;
  estado: string;
  estado_pago: string;
  observaciones?: string;
  created_at: string;
  updated_at?: string;
  detalles: CompraDetalle[];
}

export interface CompraDetalleInput {
  descripcion: string;
  producto_id?: number;
  cantidad: number;
  precio_unitario: number;
  descuento_porcentaje: number;
  iva_porcentaje: number;
}

export interface CompraInput {
  fecha: string;
  fecha_vencimiento?: string;
  proveedor_id: number;
  ref_proveedor?: string;
  retefuente: number;
  reteiva: number;
  reteica: number;
  observaciones?: string;
  detalles: CompraDetalleInput[];
}

export interface ComprasDashboard {
  total_compras_mes: number;
  total_compras_mes_anterior: number;
  cantidad_compras_mes: number;
  total_proveedores_activos: number;
  cxp_pendiente: number;
  top_proveedores: { proveedor: string | null; total: number }[];
}

export const comprasApi = {
  getDashboard: () => api.get<ComprasDashboard>(`${BASE}/dashboard`),

  getProveedores: () => api.get<Proveedor[]>(`${BASE}/proveedores`),
  createProveedor: (data: Omit<Proveedor, 'id' | 'activo' | 'created_at' | 'updated_at'>) =>
    api.post<Proveedor>(`${BASE}/proveedores`, data),
  updateProveedor: (id: number, data: Partial<Proveedor>) =>
    api.put<Proveedor>(`${BASE}/proveedores/${id}`, data),
  deleteProveedor: (id: number) => api.delete(`${BASE}/proveedores/${id}`),

  getCompras: () => api.get<Compra[]>(`${BASE}/`),
  getCompra: (id: number) => api.get<Compra>(`${BASE}/${id}`),
  createCompra: (data: CompraInput) => api.post<Compra>(`${BASE}/`, data),
  confirmarCompra: (id: number) => api.post<Compra>(`${BASE}/${id}/confirmar`),
  anularCompra: (id: number) => api.post<Compra>(`${BASE}/${id}/anular`),
  crearDevolucion: (compraId: number, data: DevolucionCompraInput) =>
    api.post<DevolucionCompra>(`${BASE}/${compraId}/devoluciones`, data).then(r => r.data),

};

// ── Devoluciones a proveedor (ND-####) ────────────────────

export interface DevolucionCompraInput {
  motivo: string;
  detalles: { compra_detalle_id: number; cantidad: string }[];
}

export interface DevolucionCompra {
  id: number;
  numero: string;
  compra_id: number;
  fecha: string;
  motivo: string;
  subtotal: number;
  iva_total: number;
  total: number;
}
