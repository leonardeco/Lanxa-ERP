import { api } from './api';

export interface CxC {
  id: number;
  numero_factura: string;
  fecha_emision: string;
  cliente_nit: string;
  nombre_cliente: string;
  marca?: string;
  valor_factura: number;
  abonos: number;
  saldo_pendiente: number;
  fecha_vencimiento?: string;
  estado: string;
  dias_vencido: number;
  notas?: string;
  created_at: string;
}

export interface CxP {
  id: number;
  numero_documento: string;
  fecha: string;
  proveedor_nit: string;
  razon_social: string;
  concepto?: string;
  valor: number;
  abonos: number;
  saldo_pendiente: number;
  fecha_vencimiento?: string;
  estado: string;
  dias_vencido: number;
  notas?: string;
  created_at: string;
}

export interface CarteraStats {
  total_cxc: number;
  total_cxp: number;
  cxc_pendiente: number;
  cxc_vencida: number;
  cxp_pendiente: number;
  cxp_vencida: number;
}

const BASE = '/v1/contabilidad/cartera';

export const carteraApi = {
  stats: () => api.get<CarteraStats>(`${BASE}/stats`).then(r => r.data),

  listCxC: (estado?: string) =>
    api.get<CxC[]>(`${BASE}/cxc`, { params: estado ? { estado } : {} }).then(r => r.data),
  createCxC: (data: Omit<CxC, 'id' | 'abonos' | 'saldo_pendiente' | 'dias_vencido' | 'created_at'>) =>
    api.post<CxC>(`${BASE}/cxc`, data).then(r => r.data),
  updateCxC: (id: number, data: Partial<CxC>) =>
    api.put<CxC>(`${BASE}/cxc/${id}`, data).then(r => r.data),
  abonarCxC: (id: number, valor: number, notas?: string) =>
    api.post<CxC>(`${BASE}/cxc/${id}/abonar`, { valor, notas }).then(r => r.data),
  anularCxC: (id: number) =>
    api.patch<CxC>(`${BASE}/cxc/${id}/anular`).then(r => r.data),

  listCxP: (estado?: string) =>
    api.get<CxP[]>(`${BASE}/cxp`, { params: estado ? { estado } : {} }).then(r => r.data),
  createCxP: (data: Omit<CxP, 'id' | 'abonos' | 'saldo_pendiente' | 'dias_vencido' | 'created_at'>) =>
    api.post<CxP>(`${BASE}/cxp`, data).then(r => r.data),
  updateCxP: (id: number, data: Partial<CxP>) =>
    api.put<CxP>(`${BASE}/cxp/${id}`, data).then(r => r.data),
  abonarCxP: (id: number, valor: number, notas?: string) =>
    api.post<CxP>(`${BASE}/cxp/${id}/abonar`, { valor, notas }).then(r => r.data),
  anularCxP: (id: number) =>
    api.patch<CxP>(`${BASE}/cxp/${id}/anular`).then(r => r.data),
};
