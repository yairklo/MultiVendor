'use client'

import React, { Suspense, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { setCookie } from 'cookies-next'
import { apiClient } from '@/lib/api/apiClient'
import { useUiLocale } from '@/context/UiLocaleContext'
import { UiLanguageSwitcher } from '@/components/ui/UiLanguageSwitcher'

type SignupMode = 'customer' | 'seller'

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
}

export default function SignupPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-background" />}>
      <SignupForm />
    </Suspense>
  )
}

function SignupForm() {
  const router = useRouter()
  const { t } = useUiLocale()
  const searchParams = useSearchParams()
  const initialMode: SignupMode = searchParams.get('as') === 'seller' ? 'seller' : 'customer'
  const [mode, setMode] = useState<SignupMode>(initialMode)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Customer fields
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  // Seller fields
  const [storeName, setStoreName] = useState('')
  const [storeSlug, setStoreSlug] = useState('')
  const [slugTouched, setSlugTouched] = useState(false)
  const [adminFullName, setAdminFullName] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [adminPassword, setAdminPassword] = useState('')

  const handleStoreNameChange = (value: string) => {
    setStoreName(value)
    if (!slugTouched) {
      setStoreSlug(slugify(value))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (mode === 'customer') {
        const data = await apiClient('/api/v1/auth/register', {
          method: 'POST',
          body: JSON.stringify({ email, password, full_name: fullName }),
        })
        if (data && data.access_token) {
          setCookie('token', data.access_token, { maxAge: 60 * 60 * 24 * 7, path: '/' })
          router.push('/marketplace')
        }
      } else {
        const data = await apiClient('/api/v1/auth/register-tenant', {
          method: 'POST',
          body: JSON.stringify({
            store_name: storeName,
            store_slug: storeSlug,
            admin_email: adminEmail,
            admin_password: adminPassword,
            admin_full_name: adminFullName,
          }),
        })
        if (data && data.access_token) {
          setCookie('token', data.access_token, { maxAge: 60 * 60 * 24 * 7, path: '/' })
          // The admin dashboard resolves which store to render from this
          // cookie server-side (see lib/api/serverApiClient.ts) — without it
          // the RSC request falls back to whatever tenantSlug is already
          // set, same as admin/login/page.tsx.
          setCookie('tenantSlug', storeSlug, { maxAge: 60 * 60 * 24 * 7, path: '/' })
          // Hard navigation so the next (RSC) request carries the cookies we
          // just set — same reasoning as admin/login/page.tsx.
          window.location.assign('/admin/dashboard')
        }
      }
    } catch (err: any) {
      setError(err.message || t('auth.registrationFailed'))
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
          <span className="font-heading text-xl font-bold tracking-tight">MultiVendor</span>
        </div>
        <div className="relative z-10 max-w-md">
          <h1 className="font-heading text-4xl font-bold leading-tight">
            {mode === 'seller'
              ? t('auth.signupSellerHeadline')
              : t('auth.signupCustomerHeadline')}
          </h1>
          <p className="mt-4 text-white/70">
            {mode === 'seller'
              ? t('auth.signupSellerSub')
              : t('auth.signupCustomerSub')}
          </p>
        </div>
        <div className="relative z-10 text-sm text-white/40">
          &copy; {new Date().getFullYear()} MultiVendor
        </div>
      </div>

      {/* Form panel */}
      <div className="flex w-full flex-1 items-center justify-center p-4 lg:w-1/2">
        <div className="w-full max-w-md overflow-hidden rounded-2xl border border-border bg-card shadow-xl shadow-primary/5">
          <div className="h-1.5 w-full bg-gradient-to-r from-primary to-[oklch(0.62_0.19_300)]" aria-hidden="true" />
          <div className="p-8">
            <div className="mb-2 flex justify-end">
              <UiLanguageSwitcher className="text-muted-foreground" />
            </div>
            <h1 className="font-heading text-2xl font-bold text-center mb-1 text-foreground">
              {t('auth.signupTitle')}
            </h1>
            <p className="text-sm text-muted-foreground text-center mb-6">
              {t('auth.signupSubtitle')}
            </p>

            <div className="mb-6 grid grid-cols-2 gap-1 rounded-lg bg-muted p-1">
              <button
                type="button"
                onClick={() => setMode('customer')}
                className={`rounded-md py-2 text-sm font-medium transition-all ${
                  mode === 'customer'
                    ? 'bg-card text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {t('auth.customer')}
              </button>
              <button
                type="button"
                onClick={() => setMode('seller')}
                className={`rounded-md py-2 text-sm font-medium transition-all ${
                  mode === 'seller'
                    ? 'bg-card text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {t('auth.seller')}
              </button>
            </div>

            {error && (
              <div className="mb-4 p-4 bg-destructive/10 text-destructive rounded-lg text-sm">
                {error}
              </div>
            )}

            {mode === 'customer' ? (
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label htmlFor="fullName" className="block text-sm font-medium mb-2">{t('auth.fullName')}</label>
                  <input
                    id="fullName"
                    type="text"
                    required
                    className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
                    value={fullName}
                    onChange={e => setFullName(e.target.value)}
                    placeholder="Jane Doe"
                  />
                </div>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium mb-2">{t('auth.email')}</label>
                  <input
                    id="email"
                    type="email"
                    required
                    className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="you@example.com"
                  />
                </div>
                <div>
                  <label htmlFor="password" className="block text-sm font-medium mb-2">{t('auth.password')}</label>
                  <input
                    id="password"
                    type="password"
                    required
                    minLength={8}
                    className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder={t('auth.passwordHint')}
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-primary text-primary-foreground py-3 rounded-lg font-bold hover:bg-primary/90 active:scale-[0.98] transition-all disabled:opacity-70 disabled:active:scale-100"
                >
                  {loading ? t('auth.creatingAccount') : t('auth.createAccount')}
                </button>
              </form>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label htmlFor="storeName" className="block text-sm font-medium mb-2">{t('auth.storeName')}</label>
                  <input
                    id="storeName"
                    type="text"
                    required
                    minLength={3}
                    maxLength={100}
                    className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
                    value={storeName}
                    onChange={e => handleStoreNameChange(e.target.value)}
                    placeholder="Nike Israel"
                  />
                </div>
                <div>
                  <label htmlFor="storeSlug" className="block text-sm font-medium mb-2">{t('auth.storeUrl')}</label>
                  <input
                    id="storeSlug"
                    type="text"
                    required
                    minLength={2}
                    maxLength={50}
                    pattern="[a-z0-9\-]+"
                    title="Lowercase letters, numbers, and hyphens only"
                    className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
                    value={storeSlug}
                    onChange={e => {
                      setSlugTouched(true)
                      setStoreSlug(slugify(e.target.value))
                    }}
                    placeholder="nike-israel"
                  />
                </div>
                <div>
                  <label htmlFor="adminFullName" className="block text-sm font-medium mb-2">{t('auth.yourFullName')}</label>
                  <input
                    id="adminFullName"
                    type="text"
                    required
                    className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
                    value={adminFullName}
                    onChange={e => setAdminFullName(e.target.value)}
                    placeholder="Jane Doe"
                  />
                </div>
                <div>
                  <label htmlFor="adminEmail" className="block text-sm font-medium mb-2">{t('auth.email')}</label>
                  <input
                    id="adminEmail"
                    type="email"
                    required
                    className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
                    value={adminEmail}
                    onChange={e => setAdminEmail(e.target.value)}
                    placeholder="you@example.com"
                  />
                </div>
                <div>
                  <label htmlFor="adminPassword" className="block text-sm font-medium mb-2">{t('auth.password')}</label>
                  <input
                    id="adminPassword"
                    type="password"
                    required
                    minLength={8}
                    className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:ring-2 focus:ring-ring outline-none transition-all"
                    value={adminPassword}
                    onChange={e => setAdminPassword(e.target.value)}
                    placeholder={t('auth.passwordHint')}
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-primary text-primary-foreground py-3 rounded-lg font-bold hover:bg-primary/90 active:scale-[0.98] transition-all disabled:opacity-70 disabled:active:scale-100"
                >
                  {loading ? t('auth.creatingStore') : t('auth.createStore')}
                </button>
              </form>
            )}

            <p className="mt-6 text-center text-sm text-muted-foreground">
              {t('auth.hasAccount')}{' '}
              <a href="/login" className="font-medium text-primary hover:underline">
                {t('auth.logIn')}
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
