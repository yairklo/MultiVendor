import { describe, it, expect } from 'vitest'
import { isUsableTenantSlug } from '../tenantSlug'

describe('isUsableTenantSlug', () => {
  it('accepts real store slugs', () => {
    expect(isUsableTenantSlug('store1')).toBe(true)
    expect(isUsableTenantSlug('tenant-a')).toBe(true)
  })

  it('rejects missing values and JS sentinels that become /store/undefined', () => {
    expect(isUsableTenantSlug(undefined)).toBe(false)
    expect(isUsableTenantSlug(null)).toBe(false)
    expect(isUsableTenantSlug('')).toBe(false)
    expect(isUsableTenantSlug('undefined')).toBe(false)
    expect(isUsableTenantSlug('null')).toBe(false)
  })
})
