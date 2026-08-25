import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * The API serializes timestamps from naive UTC datetimes (no "Z"/offset
 * suffix). `new Date(iso)` treats a string like that as local time instead of
 * UTC, so relative "time ago" displays drift by the browser's UTC offset.
 * Force UTC when the string doesn't already carry a timezone designator.
 */
export function parseServerDate(iso: string): Date {
  const hasTimezone = /Z$|[+-]\d{2}:?\d{2}$/.test(iso)
  return new Date(hasTimezone ? iso : `${iso}Z`)
}

const EN_MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
] as const

function calendarDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split('-').map(Number)
    return new Date(year, month - 1, day)
  }
  const date = parseServerDate(value)
  return Number.isNaN(date.getTime()) ? null : date
}

/** Locale-stable date text so SSR HTML matches hydration (no Intl / host locale). */
export function formatUiDate(
  value: string | Date | null | undefined,
  locale: 'he' | 'en' = 'he',
): string {
  const date = calendarDate(value)
  if (!date) return '—'
  const day = date.getDate()
  const year = date.getFullYear()
  if (locale === 'en') {
    return `${EN_MONTHS[date.getMonth()]} ${day}, ${year}`
  }
  return `${day}.${date.getMonth() + 1}.${year}`
}

export function formatUiDateTime(
  value: string | Date | null | undefined,
  locale: 'he' | 'en' = 'he',
): string {
  const date = calendarDate(value)
  if (!date) return '—'
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${formatUiDate(date, locale)} ${hh}:${mm}`
}

export function formatUiChartDay(
  value: string | Date | null | undefined,
  locale: 'he' | 'en' = 'he',
): string {
  const date = calendarDate(value)
  if (!date) return ''
  if (locale === 'en') return `${EN_MONTHS[date.getMonth()]} ${date.getDate()}`
  return `${date.getDate()}.${date.getMonth() + 1}`
}
