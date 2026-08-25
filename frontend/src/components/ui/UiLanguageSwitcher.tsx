'use client'

import { useUiLocale } from '@/context/UiLocaleContext'

export function UiLanguageSwitcher({ className = '' }: { className?: string }) {
  const { locale, setLocale, t } = useUiLocale()
  return (
    <button
      type="button"
      data-testid="ui-language-switcher"
      onClick={() => setLocale(locale === 'he' ? 'en' : 'he')}
      className={`text-sm font-medium transition-colors hover:opacity-80 ${className}`}
      aria-label={t('common.language')}
    >
      {locale === 'he' ? t('common.switchToEnglish') : t('common.switchToHebrew')}
    </button>
  )
}
