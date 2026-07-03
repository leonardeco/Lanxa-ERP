import { defineConfig } from '@playwright/test';

/**
 * Smoke E2E — levanta backend (puerto 8100, BD e2e propia) y frontend
 * (puerto 5273, sin TLS) y prueba los flujos criticos en Chromium.
 *
 *   npm run test:e2e
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5273',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command:
        'cd ..\\backend && (if exist e2e.db del e2e.db) && venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8100',
      url: 'http://localhost:8100/health',
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        DATABASE_URL: 'sqlite+aiosqlite:///./e2e.db',
        SECRET_KEY: 'clave-solo-para-e2e-0123456789abcdef0123456789abcdef',
        DEBUG: 'true',
        CORS_ORIGINS: 'http://localhost:5273',
      },
    },
    {
      command: 'npx vite --port 5273 --strictPort',
      url: 'http://localhost:5273',
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        E2E: '1',
        VITE_API_URL: 'http://localhost:8100/api',
      },
    },
  ],
});
