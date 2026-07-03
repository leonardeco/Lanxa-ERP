import { test, expect, type Page } from '@playwright/test';

/**
 * Smoke E2E: login real contra el backend (BD e2e recién sembrada por los
 * seeders del lifespan) y navegación por los módulos principales.
 */

const ADMIN_EMAIL = 'admin@superozonoglobal.com';
const ADMIN_PASSWORD = 'Admin2026!';

async function login(page: Page) {
  await page.goto('/');
  await page.getByPlaceholder('usuario@superozonoglobal.com').fill(ADMIN_EMAIL);
  await page.getByPlaceholder('••••••••').fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: 'Acceder al Sistema' }).click();
  await expect(page.getByText('Cerrar Sesión')).toBeVisible({ timeout: 15_000 });
}

test('login con credenciales malas muestra el error del backend', async ({ page }) => {
  await page.goto('/');
  await page.getByPlaceholder('usuario@superozonoglobal.com').fill('nadie@test.com');
  await page.getByPlaceholder('••••••••').fill('clave-mala');
  await page.getByRole('button', { name: 'Acceder al Sistema' }).click();
  await expect(page.getByText('Correo o contraseña incorrectos')).toBeVisible();
});

test('login correcto entra al Dashboard con el menú completo de Admin', async ({ page }) => {
  await login(page);
  await expect(page.getByRole('heading', { name: 'Dashboard General' })).toBeVisible();
  // Menú de Admin: módulos operativos y administración visibles
  await expect(page.getByText('Ventas & Comercial')).toBeVisible();
  await expect(page.getByText('Reportes & BI')).toBeVisible();
  await expect(page.getByText('Usuarios & Accesos')).toBeVisible();
});

test('navegar a Ventas muestra el catálogo con búsqueda', async ({ page }) => {
  await login(page);
  await page.getByText('Ventas & Comercial').click();
  // El módulo abre en su dashboard: pasar a la pestaña Productos
  await page.getByRole('button', { name: /📦 Productos/ }).click();
  await expect(page.getByText('Catálogo de Productos')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByPlaceholder('Buscar por SKU, nombre o marca…')).toBeVisible();
});

test('reportes financieros cargan: P&L, Balance cuadrado y Libro Diario', async ({ page }) => {
  await login(page);
  await page.getByText('Reportes & BI').click();

  await page.getByRole('button', { name: /Estado de Resultados/ }).click();
  await expect(page.getByText('Utilidad neta')).toBeVisible({ timeout: 10_000 });

  await page.getByRole('button', { name: /Balance General/ }).click();
  // BD recién sembrada sin movimientos: 0 = 0 → la ecuación contable cuadra
  await expect(page.getByText('✓ Cuadrado')).toBeVisible({ timeout: 10_000 });

  await page.getByRole('button', { name: /Libro Diario/ }).click();
  await expect(page.getByText(/Sin asientos/)).toBeVisible({ timeout: 10_000 });
});

test('logout regresa a la pantalla de login', async ({ page }) => {
  await login(page);
  await page.getByText('Cerrar Sesión').click();
  await expect(page.getByRole('button', { name: 'Acceder al Sistema' })).toBeVisible();
});
