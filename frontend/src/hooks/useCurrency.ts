import { useStorefrontTheme } from '@/context/StorefrontThemeContext'

export function useCurrency() {
  const { currency } = useStorefrontTheme()

  const formatCurrency = (amount: number) => {
    try {
      const locale = 'he-IL'
      return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currency,
      }).format(amount)
    } catch {
      // Fallback
      return `${amount} ${currency}`
    }
  }

  return { formatCurrency, currency }
}
