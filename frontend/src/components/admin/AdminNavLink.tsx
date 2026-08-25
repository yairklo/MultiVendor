'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import React from 'react'

export function AdminNavLink({
  href,
  children,
  exact = false,
}: {
  href: string
  children: React.ReactNode
  exact?: boolean
}) {
  const pathname = usePathname()
  const isActive = exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`)

  return (
    <Link
      href={href}
      className={`group relative flex items-center space-x-3 rounded-lg py-2 pr-3 pl-4 transition-colors duration-150 ${
        isActive
          ? 'bg-primary/10 font-medium text-primary'
          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
      }`}
    >
      <span
        className={`absolute inset-y-1 left-0 w-1 rounded-full bg-primary transition-transform duration-200 ${
          isActive ? 'scale-y-100' : 'scale-y-0'
        }`}
        aria-hidden="true"
      />
      {children}
    </Link>
  )
}
