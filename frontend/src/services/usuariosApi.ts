import { api } from './api';

export interface Usuario {
  id: number;
  email: string;
  nombre_completo: string;
  rol: string;
  is_active: boolean;
}

export interface UsuarioCreate {
  email: string;
  nombre_completo: string;
  rol: string;
  is_active: boolean;
  password: string;
}

export interface UsuarioUpdate {
  nombre_completo?: string;
  rol?: string;
  is_active?: boolean;
}

export const ROLES = ['Superadmin', 'Contabilidad', 'Ventas', 'Bodega', 'RRHH', 'Solo lectura'] as const;

export const usuariosApi = {
  list: () => api.get<Usuario[]>('/v1/usuarios').then(r => r.data),
  create: (data: UsuarioCreate) => api.post<Usuario>('/v1/usuarios', data).then(r => r.data),
  update: (id: number, data: UsuarioUpdate) => api.put<Usuario>(`/v1/usuarios/${id}`, data).then(r => r.data),
  toggle: (id: number) => api.patch<Usuario>(`/v1/usuarios/${id}/toggle`).then(r => r.data),
  changePassword: (current_password: string, new_password: string) =>
    api.put('/v1/usuarios/me/password', { current_password, new_password }).then(r => r.data),
};
