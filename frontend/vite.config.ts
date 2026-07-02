/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'

const certsDir = path.resolve(__dirname, '../certs')
const keyPath = path.join(certsDir, 'server.key')
const certPath = path.join(certsDir, 'server.crt')
const hasCerts = fs.existsSync(keyPath) && fs.existsSync(certPath)

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
  },
})
