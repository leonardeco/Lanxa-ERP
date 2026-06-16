import { api } from './api';

export interface ContabilidadStats {
  total_cuentas_puc: number;
  total_centros_costo: number;
  total_periodos: number;
  total_terceros: number;
  total_parametros_tributarios: number;
  total_parametros_nomina: number;
  empresa_nit: string;
  empresa_razon_social: string;
}

export interface VentasStats {
  ventas_mes_actual: number;
  ventas_mes_anterior: number;
  cantidad_ventas_mes: number;
  total_clientes_activos: number;
  total_productos_activos: number;
  ticket_promedio: number;
  productos_stock_bajo: number;
  ventas_por_marca: { marca: string; total: number }[];
}

export const dashboardApi = {
  getContabilidadStats: () =>
    api.get<ContabilidadStats>('/v1/contabilidad/dashboard').then(r => r.data),
  getVentasStats: () =>
    api.get<VentasStats>('/v1/ventas/dashboard').then(r => r.data),
};
