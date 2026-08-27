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
      className={`group relative flex items-center gap-3 rounded-sm py-2 pe-3 ps-4 text-sm transition-colors duration-150 ${
        isActive
          ? 'bg-sidebar-accent font-medium text-sidebar-accent-foreground'
          : 'text-sidebar-foreground/65 hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground'
      }`}
    >
      <span
        className={`absolute inset-y-1 start-0 w-0.5 bg-sidebar-primary transition-transform duration-200 ${
          isActive ? 'scale-y-100' : 'scale-y-0'
        }`}
        aria-hidden="true"
      />
      {children}
    </Link>
  )
}
