'use client'

import { useStorefrontTheme } from '@/context/StorefrontThemeContext'
import { resolveImageUrl } from '@/lib/media'

export function StorefrontBrandBackdrop({ children }: { children: React.ReactNode }) {
  const { bannerUrl } = useStorefrontTheme()
  if (!bannerUrl) return <>{children}</>
  return (
    <div className="relative flex min-h-screen flex-col">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-cover bg-center opacity-[0.08]"
        style={{ backgroundImage: `url("${resolveImageUrl(bannerUrl)}")` }}
      />
      <div className="relative flex min-h-screen flex-col">{children}</div>
    </div>
  )
}
