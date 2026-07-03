import { api } from './api';

export interface CuentaPUC {
  id: number;
  codigo_puc: string;
  nombre: string;
  clase: string;
  naturaleza: string;
  nivel: string;
  requiere_tercero: boolean;
  requiere_centro_costo: boolean;
  activo: boolean;
}

export interface CentroCosto {
  id: number;
  codigo: string;
  nombre: string;
  tipo: string;
  marca_asociada: string | null;
  responsable: string | null;
  activo: boolean;
  notas: string | null;
}

export interface Periodo {
  id: number;
  anio: number;
  mes: number;
  periodo: string;
  estado: string;
  fecha_cierre: string | null;
}

export interface ParametroTributario {
  id: number;
  concepto: string;
  tarifa_valor: number | null;
  base_aplica: string | null;
  cuenta_puc: string | null;
  notas: string | null;
  activo: boolean;
}

export interface ParametroNomina {
  id: number;
  concepto: string;
  valor_porcentaje: number | null;
  tipo: string | null;
  notas: string | null;
  activo: boolean;
}

const BASE = '/v1/contabilidad';

export const contabilidadApi = {
  // PUC
  getPuc: () => api.get<CuentaPUC[]>(`${BASE}/puc`).then(r => r.data),
  createPuc: (data: Omit<CuentaPUC, 'id'>) => api.post<CuentaPUC>(`${BASE}/puc`, data).then(r => r.data),
  updatePuc: (id: number, data: Partial<CuentaPUC>) => api.put<CuentaPUC>(`${BASE}/puc/${id}`, data).then(r => r.data),
  togglePuc: (id: number) => api.patch<CuentaPUC>(`${BASE}/puc/${id}/toggle`).then(r => r.data),

  // Centros de Costo
  getCentros: () => api.get<CentroCosto[]>(`${BASE}/centros-costo`).then(r => r.data),
  createCentro: (data: Omit<CentroCosto, 'id'>) => api.post<CentroCosto>(`${BASE}/centros-costo`, data).then(r => r.data),
  updateCentro: (id: number, data: Partial<CentroCosto>) => api.put<CentroCosto>(`${BASE}/centros-costo/${id}`, data).then(r => r.data),
  toggleCentro: (id: number) => api.patch<CentroCosto>(`${BASE}/centros-costo/${id}/toggle`).then(r => r.data),

  // Períodos
  getPeriodos: () => api.get<Periodo[]>(`${BASE}/periodos`).then(r => r.data),
  createPeriodo: (anio: number, mes: number) => api.post<Periodo>(`${BASE}/periodos`, { anio, mes }).then(r => r.data),
  togglePeriodo: (id: number) => api.patch<Periodo>(`${BASE}/periodos/${id}/toggle`).then(r => r.data),

  // Tributarios
  getTributarios: () => api.get<ParametroTributario[]>(`${BASE}/parametros-tributarios`).then(r => r.data),
  updateTributario: (id: number, data: Partial<ParametroTributario>) => api.put<ParametroTributario>(`${BASE}/parametros-tributarios/${id}`, data).then(r => r.data),
  toggleTributario: (id: number) => api.patch<ParametroTributario>(`${BASE}/parametros-tributarios/${id}/toggle`).then(r => r.data),

  // Nómina
  getNomina: () => api.get<ParametroNomina[]>(`${BASE}/parametros-nomina`).then(r => r.data),
  updateNomina: (id: number, data: Partial<ParametroNomina>) => api.put<ParametroNomina>(`${BASE}/parametros-nomina/${id}`, data).then(r => r.data),
  toggleNomina: (id: number) => api.patch<ParametroNomina>(`${BASE}/parametros-nomina/${id}/toggle`).then(r => r.data),
};

// ── Libro diario (asientos contables) ────────────────────

export interface MovimientoAsiento {
  id: number;
  cuenta_id: number;
  cuenta_codigo?: string;
  cuenta_nombre?: string;
  centro_costo_id?: number;
  debito: number;
  credito: number;
  descripcion?: string;
}

export interface Asiento {
  id: number;
  fecha: string;
  descripcion: string;
  tipo_documento?: string;
  modulo_origen?: string;
  documento_ref?: string;
  usuario_id?: number;
  periodo_id?: number;
  anulado: boolean;
  reversado: boolean;
  created_at?: string;
  movimientos: MovimientoAsiento[];
  total_debito: number;
  total_credito: number;
}

export const asientosApi = {
  getAsientos: (params?: { modulo_origen?: string; documento_ref?: string }) =>
    api.get<Asiento[]>(`${BASE}/asientos`, { params }).then(r => r.data),
  getAsiento: (id: number) => api.get<Asiento>(`${BASE}/asientos/${id}`).then(r => r.data),
};

// ── Auxiliar por tercero (estado de cuenta) ──────────────

export interface TerceroItem {
  id: number;
  nit_cc: string;
  razon_social: string;
  tipo: string;
}

export interface MovimientoAuxiliar {
  fecha: string;
  asiento_id: number;
  documento_ref?: string;
  descripcion: string;
  cuenta_codigo: string;
  cuenta_nombre: string;
  debito: number;
  credito: number;
  saldo_acumulado: number;
}

export interface AuxiliarTercero {
  tercero_id: number;
  nit_cc: string;
  razon_social: string;
  tipo: string;
  movimientos: MovimientoAuxiliar[];
  total_debitos: number;
  total_creditos: number;
  saldo_final: number;
}

export const tercerosApi = {
  getTerceros: () => api.get<TerceroItem[]>(`${BASE}/terceros`).then(r => r.data),
  getAuxiliar: (terceroId: number, params?: { fecha_desde?: string; fecha_hasta?: string; cuenta?: string }) =>
    api.get<AuxiliarTercero>(`${BASE}/terceros/${terceroId}/auxiliar`, { params }).then(r => r.data),
};
