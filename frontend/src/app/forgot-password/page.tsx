'use client'

import React, { useState } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { useUiLocale } from '@/context/UiLocaleContext'
import { UiLanguageSwitcher } from '@/components/ui/UiLanguageSwitcher'

export default function ForgotPasswordPage() {
  const { t } = useUiLocale()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await apiClient('/api/v1/auth/password-reset/request', {
        method: 'POST',
        body: JSON.stringify({ email }),
      })
    } finally {
      // The backend always returns success here regardless of whether the
      // email is registered, so there's nothing account-specific to branch
      // on -- show the same confirmation even if the request itself failed
      // (e.g. a network blip), rather than leaking which emails exist.
      setLoading(false)
      setSent(true)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6 text-foreground">
      <div className="w-full max-w-md motion-safe:animate-in motion-safe:fade-in-0 motion-safe:duration-300">
        <div className="mb-8 flex justify-end">
          <UiLanguageSwitcher className="text-muted-foreground" />
        </div>

        {sent ? (
          <div>
            <h1 className="mb-2 font-heading text-4xl font-medium text-foreground">{t('auth.resetLinkSentTitle')}</h1>
            <p className="mb-10 text-sm text-muted-foreground">{t('auth.resetLinkSentMessage')}</p>
            <a href="/login" className="text-sm font-medium text-primary hover:underline">
              {t('auth.backToLogin')}
            </a>
          </div>
        ) : (
          <>
            <h1 className="mb-2 font-heading text-4xl font-medium text-foreground">{t('auth.forgotPasswordTitle')}</h1>
            <p className="mb-10 text-sm text-muted-foreground">{t('auth.forgotPasswordSubtitle')}</p>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="mb-2 block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">{t('auth.email')}</label>
                <input
                  type="email"
                  required
                  className="w-full border-0 border-b border-foreground/30 bg-transparent py-2 outline-none transition-colors focus:border-foreground"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="mt-4 w-full bg-foreground py-3 text-sm font-medium tracking-wide text-background transition-opacity hover:opacity-90 active:scale-[0.98] disabled:opacity-70"
              >
                {loading ? t('auth.sendingResetLink') : t('auth.sendResetLink')}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-muted-foreground">
              <a href="/login" className="font-medium text-primary hover:underline">
                {t('auth.backToLogin')}
              </a>
            </p>
          </>
        )}
      </div>
    </div>
  )
}
