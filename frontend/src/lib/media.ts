/**
 * Product image URLs come in two shapes: a fully-qualified URL a seller
 * pasted in (still supported), or a `/uploads/...` path our own upload
 * endpoint returns -- the latter is relative to the FastAPI backend, not
 * this Next.js app, so it needs the API base prefixed before it can be used
 * as an <img src> (or anywhere else the browser resolves it against the
 * current origin).
 */
export function resolveImageUrl(url: string | null | undefined): string {
  if (!url) return ''
  if (url.startsWith('/')) {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    return `${apiBase}${url}`
  }
  return url
}
