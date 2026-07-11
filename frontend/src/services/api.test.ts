import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { api, getAccessToken, setAccessToken } from './api';

// El interceptor de request de axios queda registrado en `handlers`; tomamos
// el primero (el que inyecta el Authorization) para probarlo de forma aislada.
type RequestHandler = { fulfilled: (config: { headers: Record<string, unknown> }) => { headers: Record<string, unknown> } };

function requestInterceptor() {
  const { handlers } = api.interceptors.request as unknown as { handlers: RequestHandler[] };
  return handlers[0].fulfilled;
}

describe('api — access token en memoria (#30)', () => {
  beforeEach(() => {
    setAccessToken(null);
    localStorage.clear();
  });
  afterEach(() => {
    setAccessToken(null);
  });

  it('getAccessToken/setAccessToken guardan el token en memoria', () => {
    expect(getAccessToken()).toBeNull();
    setAccessToken('jwt-abc');
    expect(getAccessToken()).toBe('jwt-abc');
  });

  it('nunca persiste el token en localStorage (superficie de XSS reducida)', () => {
    setAccessToken('jwt-abc');
    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.length).toBe(0);
  });

  it('el interceptor de request inyecta el header Authorization desde memoria', () => {
    setAccessToken('jwt-abc');
    const config = requestInterceptor()({ headers: {} });
    expect(config.headers.Authorization).toBe('Bearer jwt-abc');
  });

  it('el interceptor no agrega Authorization cuando no hay token', () => {
    setAccessToken(null);
    const config = requestInterceptor()({ headers: {} });
    expect(config.headers.Authorization).toBeUndefined();
  });

  it('setAccessToken(null) limpia el token y el header deja de enviarse', () => {
    setAccessToken('jwt-abc');
    setAccessToken(null);
    expect(getAccessToken()).toBeNull();
    const config = requestInterceptor()({ headers: {} });
    expect(config.headers.Authorization).toBeUndefined();
  });
});
