import fs from 'fs'
import path from 'path'

export function getE2eApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL.replace(/\/$/, '')
  }
  try {
    const env = fs.readFileSync(path.join(__dirname, '..', '.env.local'), 'utf8')
    const match = env.match(/^NEXT_PUBLIC_API_BASE_URL=(.+)$/m)
    if (match) return match[1].trim().replace(/\/$/, '')
  } catch {
    // Fall through to the documented default.
  }
  return 'http://localhost:8000'
}
