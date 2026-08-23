'use client'

import React, { useState } from 'react'
import { setCookie } from 'cookies-next'
import { apiClient } from '@/lib/api/apiClient'

export default function AdminLoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [tenantSlug, setTenantSlug] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const payload: any = { email, password }
      if (tenantSlug) {
        payload.tenant_slug = tenantSlug
      }

      const data = await apiClient('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify(payload)
      })

      if (data && data.access_token) {
        // Store the token in a cookie
        setCookie('token', data.access_token, { maxAge: 60 * 60 * 24 * 7, path: '/' })
        if (tenantSlug) {
          setCookie('tenantSlug', tenantSlug, { maxAge: 60 * 60 * 24 * 7, path: '/' })
        }

        // Route based on the role the backend actually returned, not a guess
        // from the email — a customer account has no admin permissions and
        // would otherwise land on /admin/dashboard and 403 on every request.
        // Tenant-admin status is per-store (UserStoreMembership), not on the
        // account itself, so it comes back as `store_role`, not `role`.
        // Hard navigation so the next request includes the cookies we just set
        // (router.push can race the RSC read of tenantSlug and bounce back to login).
        if (data.role === 'super_admin') {
          window.location.assign('/super-admin')
        } else if (data.store_role === 'tenant_admin') {
          window.location.assign('/admin/dashboard')
        } else {
          window.location.assign(tenantSlug ? `/store/${tenantSlug}` : '/marketplace')
        }
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4 text-gray-900">
      <div className="max-w-md w-full bg-white p-8 rounded-2xl shadow-lg border border-gray-100">
        <h1 className="text-3xl font-bold text-center mb-8 bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
          Platform Admin Login
        </h1>
        
        {error && (
          <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-2">Email Address</label>
            <input
              id="email"
              type="email"
              required
              className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-blue-600 outline-none transition-all"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="admin@example.com"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-2">Password</label>
            <input
              id="password"
              type="password"
              required
              className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-blue-600 outline-none transition-all"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <div>
            <label htmlFor="tenantSlug" className="block text-sm font-medium mb-2">Store Slug (Optional)</label>
            <input
              id="tenantSlug"
              type="text"
              className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-blue-600 outline-none transition-all"
              value={tenantSlug}
              onChange={e => setTenantSlug(e.target.value)}
              placeholder="e.g. test-tenant (Leave empty for Super Admin)"
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-bold hover:bg-blue-700 active:scale-[0.98] transition-all disabled:opacity-70 disabled:active:scale-100"
          >
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
