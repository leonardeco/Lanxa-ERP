/**
 * Super Ozono Global — API Service para el log de Auditoría (solo lectura)
 */

import { api } from './api';

export interface CambioCampo {
  antes: unknown;
  despues: unknown;
}

export interface RegistroAuditoria {
  id: number;
  fecha: string;
  usuario_id?: number;
  usuario_email?: string;
  accion: string;
  entidad: string;
  entidad_id?: number;
  descripcion: string;
  cambios?: Record<string, CambioCampo> | null;
  ip?: string | null;
}

export interface AuditoriaFiltros {
  entidad?: string;
  accion?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
  limit?: number;
}

export const auditoriaApi = {
  getRegistros: (filtros: AuditoriaFiltros = {}) =>
    api.get<RegistroAuditoria[]>('/v1/auditoria', { params: filtros }),
};
