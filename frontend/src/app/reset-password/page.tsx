'use client'

import React, { Suspense, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { apiClient, ApiError } from '@/lib/api/apiClient'
import { useUiLocale } from '@/context/UiLocaleContext'
import { UiLanguageSwitcher } from '@/components/ui/UiLanguageSwitcher'
import { errorMessage } from '@/lib/errors'

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-background" />}>
      <ResetPasswordForm />
    </Suspense>
  )
}

function ResetPasswordForm() {
  const { t } = useUiLocale()
  const searchParams = useSearchParams()
  const token = searchParams.get('token')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!token) {
      setError(t('auth.missingResetToken'))
      return
    }
    if (password !== confirmPassword) {
      setError(t('auth.passwordsDontMatch'))
      return
    }

    setLoading(true)
    try {
      await apiClient('/api/v1/auth/password-reset/confirm', {
        method: 'POST',
        body: JSON.stringify({ token, new_password: password }),
      })
      setSuccess(true)
    } catch (err) {
      setError(err instanceof ApiError && err.status === 400 ? t('auth.invalidResetLink') : errorMessage(err) || t('auth.resetPasswordFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6 text-foreground">
      <div className="w-full max-w-md motion-safe:animate-in motion-safe:fade-in-0 motion-safe:duration-300">
        <div className="mb-8 flex justify-end">
          <UiLanguageSwitcher className="text-muted-foreground" />
        </div>

        {success ? (
          <div>
            <h1 className="mb-2 font-heading text-4xl font-medium text-foreground">{t('auth.resetPasswordSuccessTitle')}</h1>
            <p className="mb-10 text-sm text-muted-foreground">{t('auth.resetPasswordSuccessMessage')}</p>
            <a href="/login" className="text-sm font-medium text-primary hover:underline">
              {t('auth.backToLogin')}
            </a>
          </div>
        ) : (
          <>
            <h1 className="mb-2 font-heading text-4xl font-medium text-foreground">{t('auth.resetPasswordTitle')}</h1>
            <p className="mb-10 text-sm text-muted-foreground">{t('auth.resetPasswordSubtitle')}</p>

            {!token && (
              <div className="mb-4 border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {t('auth.invalidResetLink')}
              </div>
            )}

            {error && (
              <div className="mb-4 border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="mb-2 block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">{t('auth.newPassword')}</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  className="w-full border-0 border-b border-foreground/30 bg-transparent py-2 outline-none transition-colors focus:border-foreground"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>
              <div>
                <label className="mb-2 block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">{t('auth.confirmPassword')}</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  className="w-full border-0 border-b border-foreground/30 bg-transparent py-2 outline-none transition-colors focus:border-foreground"
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !token}
                className="mt-4 w-full bg-foreground py-3 text-sm font-medium tracking-wide text-background transition-opacity hover:opacity-90 active:scale-[0.98] disabled:opacity-70"
              >
                {loading ? t('auth.resettingPassword') : t('auth.resetPasswordButton')}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
