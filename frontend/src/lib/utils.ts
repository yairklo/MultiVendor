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
