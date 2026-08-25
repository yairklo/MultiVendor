export function isValidDigitalFileUrl(value: string): boolean {
  const url = value.trim()
  if (!url) return true
  const lower = url.toLowerCase()
  if (lower.startsWith('javascript:') || lower.startsWith('data:') || lower.startsWith('vbscript:')) {
    return false
  }
  return url.startsWith('/') || lower.startsWith('http://') || lower.startsWith('https://')
}

export function fileLabelFromUrl(url: string): string {
  const trimmed = url.trim()
  if (!trimmed) return ''
  try {
    const withoutQuery = trimmed.split('?')[0]
    const last = decodeURIComponent(withoutQuery.split('/').pop() || '')
    if (last) return last
  } catch {
    // malformed percent-encoding — fall through
  }
  return trimmed
}
