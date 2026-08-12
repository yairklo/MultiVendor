import { useStorefrontTheme } from '@/context/StorefrontThemeContext'

export function useCurrency() {
  const { currency, defaultLanguage } = useStorefrontTheme()

  const formatCurrency = (amount: number) => {
    try {
      const locale = defaultLanguage === 'he' ? 'he-IL' : 'en-US'
      return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currency,
      }).format(amount)
    } catch (e) {
      // Fallback
      return `${amount} ${currency}`
    }
  }

  return { formatCurrency, currency }
}
