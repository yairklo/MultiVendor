/** Slugs that JS template strings produce when a value is missing, e.g. `/store/${undefined}`. */
const SENTINEL_SLUGS = new Set(['undefined', 'null', 'true', 'false', 'NaN'])

/**
 * A store slug we are willing to put in a URL or send to `/api/v1/store/{slug}/…`.
 * Rejects empty values and the stringified JS sentinels that otherwise 404 as "Tenant not found"
 * and surface as an uncaught `ApiError` overlay in the Next.js app.
 */
export function isUsableTenantSlug(slug: unknown): slug is string {
  if (typeof slug !== 'string') return false
  const value = slug.trim()
  if (!value || SENTINEL_SLUGS.has(value)) return false
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value)
}
