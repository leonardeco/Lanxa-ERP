/** Versión de la app (alinear con backend APP_VERSION en cada release). */
export const APP_VERSION = '0.3.0';

/** Base de la API, p. ej. https://192.168.1.131:8000/api */
export const API_BASE: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? 'https://127.0.0.1:8000/api';

/** URL del health check (sin /api). */
export function healthUrl(): string {
  try {
    const u = new URL(API_BASE);
    // .../api → origen + /health
    const origin = u.origin;
    return `${origin}/health`;
  } catch {
    return 'https://127.0.0.1:8000/health';
  }
}

/** Host mostrado al usuario (IP o localhost). */
export function apiHostLabel(): string {
  try {
    return new URL(API_BASE).host;
  } catch {
    return 'servidor';
  }
}
