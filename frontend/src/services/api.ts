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

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
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
        localStorage.setItem('token', newToken);
        return newToken;
      })
      .catch(() => {
        localStorage.removeItem('token');
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
