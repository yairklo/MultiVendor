'use client'

import React, { useState } from 'react'
import { setCookie } from 'cookies-next'
import { apiClient } from '@/lib/api/apiClient'
import { useUiLocale } from '@/context/UiLocaleContext'
import { UiLanguageSwitcher } from '@/components/ui/UiLanguageSwitcher'

export default function AdminLoginPage() {
  const { t } = useUiLocale()
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
      setError(err.message || t('auth.loginFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-background text-foreground">
      {/* Branded panel */}
      <div className="relative hidden lg:flex lg:w-1/2 flex-col justify-between overflow-hidden bg-[oklch(0.2_0.03_277)] p-12 text-white">
        <div
          className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-primary/40 blur-3xl"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -bottom-40 -right-24 h-[28rem] w-[28rem] rounded-full bg-[oklch(0.62_0.19_300)]/30 blur-3xl"
          aria-hidden="true"
        />
        <div className="relative z-10">
          <span className="font-heading text-xl font-bold tracking-tight">{t('auth.adminBrand')}</span>
        </div>
        <div className="relative z-10 max-w-md">
          <h1 className="font-heading text-4xl font-bold leading-tight">
            {t('auth.adminHeadline')}
          </h1>
          <p className="mt-4 text-white/70">
            {t('auth.adminSub')}
          </p>
        </div>
        <div className="relative z-10 text-sm text-white/40">
          &copy; {new Date().getFullYear()} Multi-Vendor Platform
        </div>
      </div>

      {/* Form panel */}
      <div className="flex w-full flex-1 items-center justify-center p-4 lg:w-1/2">
        <div className="w-full max-w-md overflow-hidden rounded-2xl border border-border bg-card shadow-xl shadow-primary/5">
          <div className="h-1.5 w-full bg-gradient-to-r from-primary to-[oklch(0.62_0.19_300)]" aria-hidden="true" />
          <div className="p-8">
            <div className="mb-4 flex justify-end">
              <UiLanguageSwitcher className="text-muted-foreground" />
            </div>
            <h1 className="font-heading text-2xl font-bold text-center mb-1 text-foreground">
              {t('auth.adminTitle')}
            </h1>
            <p className="text-sm text-muted-foreground text-center mb-8">
              {t('auth.adminSubtitle')}
            </p>

            {error && (
              <div className="mb-4 p-4 bg-destructive/10 text-destructive rounded-lg text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="email" className="block text-sm font-medium mb-2">{t('auth.email')}</label>
                <input
                  id="email"
                  type="email"
                  required
                  className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="admin@example.com"
                />
              </div>
              <div>
                <label htmlFor="password" className="block text-sm font-medium mb-2">{t('auth.password')}</label>
                <input
                  id="password"
                  type="password"
                  required
                  className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>
              <div>
                <label htmlFor="tenantSlug" className="block text-sm font-medium mb-2">{t('auth.storeSlug')}</label>
                <input
                  id="tenantSlug"
                  type="text"
                  className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
                  value={tenantSlug}
                  onChange={e => setTenantSlug(e.target.value)}
                  placeholder={t('auth.storeSlugPlaceholder')}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary text-primary-foreground py-3 rounded-lg font-bold hover:bg-primary/90 active:scale-[0.98] transition-all disabled:opacity-70 disabled:active:scale-100"
              >
                {loading ? t('auth.authenticating') : t('auth.signIn')}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-muted-foreground">
              {t('auth.noStore')}{' '}
              <a href="/signup?as=seller" className="font-medium text-primary hover:underline">
                {t('auth.signUp')}
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
        <div className="relative z-10 text-sm text-white/40">
          &copy; {new Date().getFullYear()} Multi-Vendor Platform
        </div>
      </div>

      {/* Form panel */}
      <div className="flex w-full flex-1 items-center justify-center p-4 lg:w-1/2">
        <div className="w-full max-w-md overflow-hidden rounded-2xl border border-border bg-card shadow-xl shadow-primary/5">
          <div className="h-1.5 w-full bg-gradient-to-r from-primary to-[oklch(0.62_0.19_300)]" aria-hidden="true" />
          <div className="p-8">
            <h1 className="font-heading text-2xl font-bold text-center mb-1 text-foreground">
              Platform Admin Login
            </h1>
            <p className="text-sm text-muted-foreground text-center mb-8">
              Sign in to manage your store.
            </p>

            {error && (
              <div className="mb-4 p-4 bg-destructive/10 text-destructive rounded-lg text-sm">
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
                  className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
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
                  className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
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
                  className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
                  value={tenantSlug}
                  onChange={e => setTenantSlug(e.target.value)}
                  placeholder="e.g. test-tenant (Leave empty for Super Admin)"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary text-primary-foreground py-3 rounded-lg font-bold hover:bg-primary/90 active:scale-[0.98] transition-all disabled:opacity-70 disabled:active:scale-100"
              >
                {loading ? 'Authenticating...' : 'Sign In'}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-muted-foreground">
              Don&apos;t have a store yet?{' '}
              <a href="/signup?as=seller" className="font-medium text-primary hover:underline">
                Sign up
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
