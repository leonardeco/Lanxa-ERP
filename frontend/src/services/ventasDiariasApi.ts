/**
 * Super Ozono Global — API Service para Ventas Diarias (Run 6)
 */
import { api } from './api';

const BASE = '/v1/ventas-diarias';

// Los campos Decimal del backend (Pydantic `Decimal` sin field_serializer
// custom, ver ventas_diarias/schemas.py) viajan como string en el JSON —
// usar Number(...) antes de sumar.
export interface VentaDiariaDetalle {
  id: number;
  producto_id: number;
  cantidad: string;
  venta?: string;
  abono_1?: string;
  abono_2?: string;
  saldo: string;
  pesos_c?: string;
  valor_flete?: string;
}

export interface VentaDiariaDetalleInput {
  producto_id: number;
  cantidad: number;
  venta?: number;
  abono_1?: number;
  abono_2?: number;
}

export interface VentaDiaria {
  id: number;
  fecha: string;
  asesor?: string;
  guia?: string;
  codigo_guia?: string;
  cliente_id: number;
  estado: string;
  forma_pago?: string;
  notas?: string;
  detalles: VentaDiariaDetalle[];
}

export interface VentaDiariaInput {
  fecha: string;
  asesor?: string;
  guia?: string;
  codigo_guia?: string;
  cliente_id: number;
  estado: string;
  forma_pago?: string;
  notas?: string;
  detalles: VentaDiariaDetalleInput[];
}

export interface ResumenMensual {
  anio: number;
  mes: number;
  total_venta: string;
  total_abonado: string;
  total_saldo: string;
  cantidad_entregado: number;
  cantidad_devolucion: number;
}

export const ventasDiariasApi = {
  list: (params?: { fecha_desde?: string; fecha_hasta?: string; estado?: string; asesor?: string }) =>
    api.get<VentaDiaria[]>(`${BASE}/`, { params }),

  get: (id: number) => api.get<VentaDiaria>(`${BASE}/${id}`),

  create: (data: VentaDiariaInput) => api.post<VentaDiaria>(`${BASE}/`, data),

  resumenMensual: (anio: number, mes: number) =>
    api.get<ResumenMensual>(`${BASE}/resumen/${anio}/${mes}`),
};
