/**
 * Lanxa ERP — API Service para Ventas & Comercial
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
  controla_lote?: boolean;
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
  // Perfil tributario del comprador — qué retenciones practica
  retiene_fuente: boolean;
  retiene_iva: boolean;
  retiene_ica: boolean;
  tarifa_reteica?: number | null;
  habeas_data_aceptado?: boolean;
  habeas_data_fecha?: string | null;
  activo: boolean;
  notas?: string;
  created_at: string;
  updated_at?: string;
}

export interface EmpresaInfo {
  nit: string;
  razon_social: string;
  ciudad: string;
  dian_resolucion_numero: string;
  dian_resolucion_fecha: string;
  dian_prefijo: string;
  dian_rango_desde: string;
  dian_rango_hasta: string;
  dian_vigencia_hasta: string;
  habeas_data_texto: string;
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
  getEmpresa: () => api.get<EmpresaInfo>(`${BASE}/empresa`),

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
  /** Plantilla CSV de retenciones (#4) — blob descarga */
  descargarPlantillaRetenciones: () =>
    api.get(`${BASE}/clientes/plantilla-retenciones`, { responseType: 'blob' }),
  importarRetenciones: (file: File) => {
    const form = new FormData();
    form.append('archivo', file);
    return api.post<{
      actualizados: number;
      sin_cambio: number;
      no_encontrados: string[];
      errores: string[];
      filas_leidas: number;
    }>(`${BASE}/clientes/importar-retenciones`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // ── Ventas ──
  getVentas: (estado?: string) => {
    const params = estado ? { estado } : {};
    return api.get<Venta[]>(`${BASE}/`, { params });
  },
  getVenta: (id: number) => api.get<Venta>(`${BASE}/${id}`),
  createVenta: (data: VentaInput) => api.post<Venta>(`${BASE}/`, data),
  confirmarVenta: (id: number) => api.post<Venta>(`${BASE}/${id}/confirmar`),
  anularVenta: (id: number) => api.post(`${BASE}/${id}/anular`),
  crearDevolucion: (ventaId: number, data: DevolucionInput) =>
    api.post<Devolucion>(`${BASE}/${ventaId}/devoluciones`, data).then(r => r.data),
  getDevoluciones: (ventaId: number) =>
    api.get<Devolucion[]>(`${BASE}/${ventaId}/devoluciones`).then(r => r.data),

  // ── Cotizaciones ──
  getCotizaciones: (estado?: string) => {
    const params = estado ? { estado } : {};
    return api.get<Cotizacion[]>(`${BASE}/cotizaciones`, { params });
  },
  getCotizacion: (id: number) => api.get<Cotizacion>(`${BASE}/cotizaciones/${id}`),
  createCotizacion: (data: CotizacionInput) => api.post<Cotizacion>(`${BASE}/cotizaciones`, data),
  enviarCotizacion: (id: number) => api.post<Cotizacion>(`${BASE}/cotizaciones/${id}/enviar`),
  aprobarCotizacion: (id: number) => api.post<Cotizacion>(`${BASE}/cotizaciones/${id}/aprobar`),
  rechazarCotizacion: (id: number, motivo?: string) =>
    api.post<Cotizacion>(`${BASE}/cotizaciones/${id}/rechazar`, motivo ? { motivo } : {}),
  convertirCotizacion: (id: number) => api.post<Cotizacion>(`${BASE}/cotizaciones/${id}/convertir`),
  updateCotizacion: (id: number, data: CotizacionInput) =>
    api.put<Cotizacion>(`${BASE}/cotizaciones/${id}`, data),
  deleteCotizacion: (id: number) => api.delete<void>(`${BASE}/cotizaciones/${id}`),
};

// ── Cotizaciones ─────────────────────────────────────────

export interface CotizacionInput {
  fecha: string;
  vigencia_dias: number;
  cliente_id: number;
  vendedor?: string;
  observaciones?: string;
  detalles: VentaDetalleInput[];
}

export interface Cotizacion {
  id: number;
  numero: string;
  fecha: string;
  vigencia_dias: number;
  fecha_vencimiento: string;
  cliente_id: number;
  vendedor?: string;
  subtotal: number;
  descuento_total: number;
  base_gravable: number;
  iva_total: number;
  total: number;
  estado: string;
  motivo_rechazo?: string;
  venta_id?: number;
  venta_numero?: string;
  vencida: boolean;
  observaciones?: string;
  created_at: string;
  updated_at?: string;
  cliente_razon_social?: string;
  cliente_nit?: string;
  detalles: VentaDetalle[];
}

// ── Devoluciones (Nota crédito) ───────────────────────────

export interface DevolucionInput {
  motivo: string;
  detalles: { venta_detalle_id: number; cantidad: string }[];
}

export interface Devolucion {
  id: number;
  numero: string;
  venta_id: number;
  fecha: string;
  motivo: string;
  subtotal: number;
  iva_total: number;
  total: number;
}
