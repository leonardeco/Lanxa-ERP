/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'

const certsDir = path.resolve(__dirname, '../certs')
const keyPath = path.join(certsDir, 'server.key')
const certPath = path.join(certsDir, 'server.crt')
// E2E=1: Playwright corre todo en http local (evita mixed-content y certificados)
const hasCerts = !process.env.E2E && fs.existsSync(keyPath) && fs.existsSync(certPath)

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: hasCerts
    ? { https: { key: fs.readFileSync(keyPath), cert: fs.readFileSync(certPath) } }
    : undefined,
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    exclude: ['node_modules/**', 'e2e/**'],
  },
})
