'use client'

import React, { useState } from 'react'
import { setCookie } from 'cookies-next'
import { apiClient, ApiError } from '@/lib/api/apiClient'
import { useUiLocale } from '@/context/UiLocaleContext'
import { UiLanguageSwitcher } from '@/components/ui/UiLanguageSwitcher'
import { errorMessage } from '@/lib/errors'

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
      const payload: Record<string, unknown> = { email, password }
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
          setError(t('auth.needStoreSlug'))
        }
      } else {
        setError(t('auth.loginFailed'))
      }
    } catch (err) {
      // See customer login page for why 401 gets the localized copy instead
      // of the backend's fixed, untranslated "Invalid credentials" string.
      setError(err instanceof ApiError && err.status === 401 ? t('auth.loginFailed') : errorMessage(err) || t('auth.loginFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-background text-foreground">
      <div className="relative hidden lg:flex lg:w-1/2 flex-col justify-between bg-sidebar p-12 text-sidebar-foreground lg:p-16">
        <span className="font-heading text-2xl font-medium tracking-tight">{t('auth.adminBrand')}</span>
        <div className="max-w-md">
          <h1 className="font-heading text-5xl font-medium leading-[1.1]">
            {t('auth.adminHeadline')}
          </h1>
          <p className="mt-5 text-sidebar-foreground/70">
            {t('auth.adminSub')}
          </p>
        </div>
        <div className="text-[11px] uppercase tracking-[0.16em] text-sidebar-foreground/45">
          &copy; {new Date().getFullYear()} {t('marketplace.brand')}
        </div>
      </div>

      <div className="flex w-full flex-1 items-center justify-center p-6 lg:w-1/2 lg:p-12">
        <div className="w-full max-w-md">
          <div className="mb-8 flex justify-end">
            <UiLanguageSwitcher className="text-muted-foreground" />
          </div>
          <h1 className="mb-2 font-heading text-4xl font-medium text-foreground">
            {t('auth.adminTitle')}
          </h1>
          <p className="mb-10 text-sm text-muted-foreground">
            {t('auth.adminSubtitle')}
          </p>

            {error && (
              <div className="mb-4 border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="email" className="mb-2 block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">{t('auth.email')}</label>
                <input
                  id="email"
                  type="email"
                  required
                  className="w-full border-0 border-b border-foreground/30 bg-transparent py-2 outline-none transition-colors focus:border-foreground"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="admin@example.com"
                />
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <label htmlFor="password" className="block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">{t('auth.password')}</label>
                  <a href="/forgot-password" className="text-xs font-medium text-foreground/70 hover:underline">
                    {t('auth.forgotPasswordLink')}
                  </a>
                </div>
                <input
                  id="password"
                  type="password"
                  required
                  className="w-full border-0 border-b border-foreground/30 bg-transparent py-2 outline-none transition-colors focus:border-foreground"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>
              <div>
                <label htmlFor="tenantSlug" className="mb-2 block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">{t('auth.storeSlug')}</label>
                <input
                  id="tenantSlug"
                  type="text"
                  className="w-full border-0 border-b border-foreground/30 bg-transparent py-2 outline-none transition-colors focus:border-foreground"
                  value={tenantSlug}
                  onChange={e => setTenantSlug(e.target.value)}
                  placeholder={t('auth.storeSlugPlaceholder')}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="mt-4 w-full bg-foreground py-3 text-sm font-medium tracking-wide text-background transition-opacity hover:opacity-90 active:scale-[0.98] disabled:opacity-70"
              >
                {loading ? t('auth.authenticating') : t('auth.signIn')}
              </button>
            </form>

            <p className="mt-6 text-sm text-muted-foreground">
              {t('auth.noStore')}{' '}
              <a href="/signup?as=seller" className="font-medium text-foreground underline-offset-4 hover:underline">
                {t('auth.signUp')}
              </a>
            </p>
        </div>
      </div>
    </div>
  )
}
