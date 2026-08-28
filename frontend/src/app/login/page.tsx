'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { setCookie } from 'cookies-next'
import { apiClient, ApiError } from '@/lib/api/apiClient'
import { useUiLocale } from '@/context/UiLocaleContext'
import { UiLanguageSwitcher } from '@/components/ui/UiLanguageSwitcher'
import { errorMessage } from '@/lib/errors'

export default function CustomerLoginPage() {
  const router = useRouter()
  const { t } = useUiLocale()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [tenantSlug] = useState('test-tenant')
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
    } catch (err) {
      // The backend's 401 detail ("Invalid credentials") is a fixed,
      // untranslated English string -- show the localized copy instead of
      // relaying it as-is into an otherwise-translated UI. Anything else
      // (network failure, 5xx) is unexpected enough that the raw message is
      // more useful than a generic one.
      setError(err instanceof ApiError && err.status === 401 ? t('auth.loginFailed') : errorMessage(err) || t('auth.loginFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen grid grid-cols-1 md:grid-cols-2 text-foreground">
      <div className="relative hidden md:flex flex-col justify-between bg-sidebar p-10 text-sidebar-foreground md:p-14">
        <div className="font-heading text-2xl font-medium">{t('auth.customerBrand')}</div>
        <div className="space-y-4">
          <h2 className="font-heading text-5xl font-medium leading-[1.1]">
            {t('auth.customerHeadline')}
          </h2>
          <p className="max-w-sm text-sidebar-foreground/70">
            {t('auth.customerSub')}
          </p>
        </div>
        <div className="text-[11px] uppercase tracking-[0.16em] text-sidebar-foreground/45">
          &copy; {new Date().getFullYear()} {t('marketplace.brand')}
        </div>
      </div>

      <div className="flex items-center justify-center bg-background p-6 md:p-12">
        <div className="w-full max-w-md motion-safe:animate-in motion-safe:fade-in-0 motion-safe:duration-300">
          <div className="mb-8 flex justify-end">
            <UiLanguageSwitcher className="text-muted-foreground" />
          </div>
          <h1 className="mb-2 font-heading text-4xl font-medium text-foreground">{t('auth.customerTitle')}</h1>
          <p className="mb-10 text-sm text-muted-foreground">{t('auth.customerSubtitle')}</p>

          {error && (
            <div className="mb-4 border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="mb-2 block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">{t('auth.email')}</label>
              <input
                type="email"
                required
                className="w-full border-0 border-b border-foreground/30 bg-transparent py-2 outline-none transition-colors focus:border-foreground"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="customer@example.com"
              />
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between">
                <label className="block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">{t('auth.password')}</label>
                <a href="/forgot-password" className="text-xs font-medium text-primary hover:underline">
                  {t('auth.forgotPasswordLink')}
                </a>
              </div>
              <input
                type="password"
                required
                className="w-full border-0 border-b border-foreground/30 bg-transparent py-2 outline-none transition-colors focus:border-foreground"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
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

          <p className="mt-6 text-center text-sm text-muted-foreground">
            {t('auth.noAccount')}{' '}
            <a href="/signup" className="font-medium text-primary hover:underline">
              {t('auth.signUp')}
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}
