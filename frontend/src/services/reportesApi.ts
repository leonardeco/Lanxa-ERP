import { api } from './api';

const BASE = '/v1/reportes';

export interface AgingBucket {
  bucket: string;
  cantidad: number;
  total: number;
}

export interface AgingDetalle {
  id: number;
  numero: string;
  tercero: string;
  nit: string;
  saldo_pendiente: number;
  dias_vencido: number;
  bucket: string;
  fecha_vencimiento?: string;
}

export interface AgingReporte {
  buckets: AgingBucket[];
  detalle: AgingDetalle[];
  total_pendiente: number;
}

export interface AgingCarteraResponse {
  cxc: AgingReporte;
  cxp: AgingReporte;
}

export interface TotalPorGrupo {
  nombre: string;
  total: number;
  cantidad: number;
}

export interface ComprasPeriodoResponse {
  fecha_desde: string;
  fecha_hasta: string;
  total: number;
  cantidad_documentos: number;
  por_proveedor: TotalPorGrupo[];
}

export interface VentasPeriodoResponse {
  fecha_desde: string;
  fecha_hasta: string;
  total: number;
  cantidad_documentos: number;
  por_cliente: TotalPorGrupo[];
  por_marca: TotalPorGrupo[];
}

export interface RetencionesPeriodoResponse {
  fecha_desde: string;
  fecha_hasta: string;
  compras_retefuente: number;
  compras_reteiva: number;
  compras_reteica: number;
  ventas_retefuente: number;
  ventas_reteiva: number;
  ventas_reteica: number;
  total_retefuente: number;
  total_reteiva: number;
  total_reteica: number;
}

export const reportesApi = {
  getAgingCartera: () =>
    api.get<AgingCarteraResponse>(`${BASE}/aging-cartera`).then(r => r.data),

  getComprasPeriodo: (fecha_desde?: string, fecha_hasta?: string) =>
    api.get<ComprasPeriodoResponse>(`${BASE}/compras-periodo`, { params: { fecha_desde, fecha_hasta } }).then(r => r.data),

  getVentasPeriodo: (fecha_desde?: string, fecha_hasta?: string) =>
    api.get<VentasPeriodoResponse>(`${BASE}/ventas-periodo`, { params: { fecha_desde, fecha_hasta } }).then(r => r.data),

  getRetencionesPeriodo: (fecha_desde?: string, fecha_hasta?: string) =>
    api.get<RetencionesPeriodoResponse>(`${BASE}/retenciones-periodo`, { params: { fecha_desde, fecha_hasta } }).then(r => r.data),
};

// ── Estados financieros (motor de asientos) ─────────────

export interface CuentaSaldo {
  codigo_puc: string;
  nombre: string;
  saldo: number;
}

export interface GrupoEstadoFinanciero {
  clase: string;
  total: number;
  cuentas: CuentaSaldo[];
}

export interface EstadoResultadosResponse {
  fecha_desde: string;
  fecha_hasta: string;
  ingresos: GrupoEstadoFinanciero;
  costos: GrupoEstadoFinanciero;
  gastos: GrupoEstadoFinanciero;
  utilidad_bruta: number;
  utilidad_neta: number;
}

export interface BalanceGeneralResponse {
  fecha_corte: string;
  activo: GrupoEstadoFinanciero;
  pasivo: GrupoEstadoFinanciero;
  patrimonio: GrupoEstadoFinanciero;
  resultado_del_ejercicio: number;
  total_activo: number;
  total_pasivo_patrimonio: number;
  cuadrado: boolean;
}

export const estadosFinancierosApi = {
  getEstadoResultados: (fecha_desde?: string, fecha_hasta?: string) =>
    api.get<EstadoResultadosResponse>(`${BASE}/estado-resultados`, { params: { fecha_desde, fecha_hasta } }).then(r => r.data),

  getBalanceGeneral: (fecha_corte?: string) =>
    api.get<BalanceGeneralResponse>(`${BASE}/balance-general`, { params: { fecha_corte } }).then(r => r.data),
};
