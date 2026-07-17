import { describe, it, expect } from 'vitest'
import { APP_VERSION, healthUrl, apiHostLabel, API_BASE } from './config'

describe('config', () => {
  it('APP_VERSION es semver x.y.z no vacio', () => {
    expect(APP_VERSION).toMatch(/^\d+\.\d+\.\d+$/)
  })

  it('healthUrl deriva del origen de la API', () => {
    const h = healthUrl()
    expect(h).toMatch(/^https?:\/\//)
    expect(h.endsWith('/health')).toBe(true)
    expect(h.includes('/api')).toBe(false)
  })

  it('apiHostLabel no vacio', () => {
    expect(apiHostLabel().length).toBeGreaterThan(0)
  })

  it('API_BASE apunta a /api', () => {
    expect(API_BASE.includes('/api')).toBe(true)
  })
})
