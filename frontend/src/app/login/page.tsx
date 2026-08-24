'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { setCookie } from 'cookies-next'
import { apiClient } from '@/lib/api/apiClient'

export default function CustomerLoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [tenantSlug, setTenantSlug] = useState('test-tenant')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const data = await apiClient('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password, tenant_slug: tenantSlug })
      })

      if (data && data.access_token) {
        setCookie('token', data.access_token, { maxAge: 60 * 60 * 24 * 7, path: '/' })
        // Redirect to the test storefront
        router.push(`/store/${tenantSlug}`)
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen grid grid-cols-1 md:grid-cols-2 text-foreground">
      <div className="relative hidden md:flex flex-col justify-between overflow-hidden bg-primary p-10 text-primary-foreground">
        <div
          className="pointer-events-none absolute inset-0 opacity-20"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 20%, white 0, transparent 45%), radial-gradient(circle at 80% 70%, white 0, transparent 40%)',
          }}
        />
        <div className="relative z-10 text-xl font-bold font-heading">MultiVendor</div>
        <div className="relative z-10 space-y-3">
          <h2 className="text-3xl font-bold font-heading leading-tight">
            Welcome back to your marketplace.
          </h2>
          <p className="max-w-sm text-primary-foreground/80">
            Sign in to track orders, manage your account, and pick up where you left off.
          </p>
        </div>
        <div className="relative z-10 text-xs text-primary-foreground/60">
          &copy; {new Date().getFullYear()} MultiVendor
        </div>
      </div>

      <div className="flex items-center justify-center bg-background p-4 md:p-10">
        <div className="w-full max-w-md rounded-2xl border border-border bg-card p-8 shadow-lg animate-in fade-in-0 zoom-in-95 duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]">
          <h1 className="text-2xl font-bold mb-1 text-foreground font-heading">Customer Login</h1>
          <p className="mb-8 text-sm text-muted-foreground">Sign in to continue to your account.</p>

          {error && (
            <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2 text-foreground">Email Address</label>
              <input
                type="email"
                required
                className="w-full px-4 py-3 rounded-lg border border-input focus:ring-2 focus:ring-ring outline-none transition-shadow"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="customer@example.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2 text-foreground">Password</label>
              <input
                type="password"
                required
                className="w-full px-4 py-3 rounded-lg border border-input focus:ring-2 focus:ring-ring outline-none transition-shadow"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-primary-foreground py-3 rounded-lg font-bold transition-all duration-150 hover:bg-primary/90 active:scale-[0.98] disabled:opacity-70"
            >
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
