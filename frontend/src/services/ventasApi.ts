/**
 * Super Ozono Global — API Service para Ventas & Comercial
 * CRUD de Productos, Clientes y Documentos de Venta
 */

import { api } from './api';

const BASE = '/v1/ventas';

// ══════════════════════════════════════════════════════════
// TIPOS
// ══════════════════════════════════════════════════════════

export interface Producto {
  id: number;
  sku: string;
  nombre: string;
  descripcion?: string;
  categoria: string;
  marca: string;
  centro_costo_id?: number;
  unidad_medida: string;
  contenido_neto?: string;
  precio_venta: number;
  precio_costo?: number;
  tarifa_iva: number;
  stock_actual: number;
  stock_minimo: number;
  activo: boolean;
  registro_ica?: string;
  notas?: string;
  created_at: string;
  updated_at?: string;
}

export interface Cliente {
  id: number;
  nit_cc: string;
  dv?: string;
  razon_social: string;
  nombre_comercial?: string;
  tipo_persona: string;
  regimen_iva: string;
  direccion?: string;
  ciudad?: string;
  departamento?: string;
  telefono?: string;
  celular?: string;
  email?: string;
  contacto_nombre?: string;
  contacto_cargo?: string;
  lista_precios: string;
  cupo_credito: number;
  dias_credito: number;
  activo: boolean;
  notas?: string;
  created_at: string;
  updated_at?: string;
}

export interface VentaDetalle {
  id: number;
  producto_id: number;
  cantidad: number;
  precio_unitario: number;
  descuento_porcentaje: number;
  subtotal_linea: number;
  iva_porcentaje: number;
  iva_valor: number;
  total_linea: number;
  notas?: string;
  created_at: string;
  producto_nombre?: string;
  producto_sku?: string;
}

export interface Venta {
  id: number;
  numero: string;
  fecha: string;
  fecha_vencimiento?: string;
  cliente_id: number;
  centro_costo_id?: number;
  vendedor?: string;
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
  cliente_razon_social?: string;
  cliente_nit?: string;
  detalles: VentaDetalle[];
}

export interface VentaDashboard {
  ventas_mes_actual: number;
  ventas_mes_anterior: number;
  cantidad_ventas_mes: number;
  total_clientes_activos: number;
  total_productos_activos: number;
  ticket_promedio: number;
  productos_stock_bajo: number;
  ventas_por_marca: { marca: string; total: number }[];
}

export interface VentaDetalleInput {
  producto_id: number;
  cantidad: number;
  precio_unitario: number;
  descuento_porcentaje: number;
  iva_porcentaje: number;
  notas?: string;
}

export interface VentaInput {
  fecha: string;
  fecha_vencimiento?: string;
  cliente_id: number;
  centro_costo_id?: number;
  vendedor?: string;
  observaciones?: string;
  detalles: VentaDetalleInput[];
}

// ══════════════════════════════════════════════════════════
// DASHBOARD
// ══════════════════════════════════════════════════════════

export const ventasApi = {
  getDashboard: () => api.get<VentaDashboard>(`${BASE}/dashboard`),

  // ── Productos ──
  getProductos: (marca?: string) => {
    const params = marca ? { marca } : {};
    return api.get<Producto[]>(`${BASE}/productos`, { params });
  },
  getProducto: (id: number) => api.get<Producto>(`${BASE}/productos/${id}`),
  createProducto: (data: Omit<Producto, 'id' | 'created_at' | 'updated_at'>) =>
    api.post<Producto>(`${BASE}/productos`, data),
  updateProducto: (id: number, data: Partial<Producto>) =>
    api.put<Producto>(`${BASE}/productos/${id}`, data),
  deleteProducto: (id: number) => api.delete(`${BASE}/productos/${id}`),

  // ── Clientes ──
  getClientes: () => api.get<Cliente[]>(`${BASE}/clientes`),
  getCliente: (id: number) => api.get<Cliente>(`${BASE}/clientes/${id}`),
  createCliente: (data: Omit<Cliente, 'id' | 'created_at' | 'updated_at'>) =>
    api.post<Cliente>(`${BASE}/clientes`, data),
  updateCliente: (id: number, data: Partial<Cliente>) =>
    api.put<Cliente>(`${BASE}/clientes/${id}`, data),
  deleteCliente: (id: number) => api.delete(`${BASE}/clientes/${id}`),

  // ── Ventas ──
  getVentas: (estado?: string) => {
    const params = estado ? { estado } : {};
    return api.get<Venta[]>(`${BASE}/`, { params });
  },
  getVenta: (id: number) => api.get<Venta>(`${BASE}/${id}`),
  createVenta: (data: VentaInput) => api.post<Venta>(`${BASE}/`, data),
  confirmarVenta: (id: number) => api.post<Venta>(`${BASE}/${id}/confirmar`),
  anularVenta: (id: number) => api.post(`${BASE}/${id}/anular`),
};
