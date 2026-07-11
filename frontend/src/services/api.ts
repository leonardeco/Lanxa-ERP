import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api',
  withCredentials: true, // envía/recibe la cookie HttpOnly del refresh token
  headers: {
    'Content-Type': 'application/json',
  },
});

let onSessionExpired: () => void = () => {};
export function setOnSessionExpired(handler: () => void) {
  onSessionExpired = handler;
}

// Access token SOLO en memoria (nunca en localStorage) para reducir la superficie
// de XSS: un script inyectado no puede leerlo de un almacén persistente. La
// persistencia de sesión entre recargas la da el refresh token en cookie
// HttpOnly (que JS no puede leer) vía /login/refresh-token. Ver PENDIENTES #30.
let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

api.interceptors.request.use((config) => {
  if (accessToken && config.headers) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

let refreshing: Promise<string | null> | null = null;

function refreshAccessToken(): Promise<string | null> {
  if (!refreshing) {
    refreshing = api
      .post('/login/refresh-token')
      .then((res) => {
        const newToken = res.data.access_token as string;
        setAccessToken(newToken);
        return newToken;
      })
      .catch(() => {
        setAccessToken(null);
        return null;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

api.interceptors.response.use((response) => {
  return response;
}, async (error) => {
  const originalRequest = error.config;
  const isAuthRoute: boolean = originalRequest?.url?.includes('/login/') ?? false;

  if (error.response?.status === 401 && originalRequest && !originalRequest._retry && !isAuthRoute) {
    originalRequest._retry = true;
    const newToken = await refreshAccessToken();
    if (newToken) {
      originalRequest.headers.Authorization = `Bearer ${newToken}`;
      return api(originalRequest);
    }
    // El refresh token también es inválido/expiró: forzar logout real
    onSessionExpired();
  }
  return Promise.reject(error);
});
