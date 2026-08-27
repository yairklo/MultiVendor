'use client'

import React, { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { Menu, X } from 'lucide-react'

export function AdminMobileNav({
  navContent,
  logoutButtonCompact,
  logoutButtonDrawer,
  title = 'Tenant CMS',
}: {
  navContent: React.ReactNode
  logoutButtonCompact: React.ReactNode
  logoutButtonDrawer: React.ReactNode
  title?: string
}) {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  useEffect(() => {
    setOpen(false)
  }, [pathname])

  return (
    <>
      <header className="flex h-16 items-center justify-between border-b border-border bg-card px-4 md:hidden">
        <button aria-label="Open menu" onClick={() => setOpen(true)} className="text-foreground transition-colors duration-150 hover:text-primary">
          <Menu className="w-6 h-6" />
        </button>
        <h1 className="font-heading text-lg font-bold text-foreground">{title}</h1>
        {logoutButtonCompact}
      </header>

      {open && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div
            className="absolute inset-0 bg-black/40 duration-200 animate-in fade-in-0"
            onClick={() => setOpen(false)}
          />
          <div className="relative flex h-full w-64 flex-col bg-sidebar shadow-xl duration-200 animate-in ltr:slide-in-from-left rtl:slide-in-from-right">
            <div className="flex h-16 items-center justify-between border-b border-sidebar-border px-4">
              <h1 className="font-heading text-lg font-bold text-sidebar-foreground">{title}</h1>
              <button
                aria-label="Close menu"
                onClick={() => setOpen(false)}
                className="text-sidebar-foreground/70 transition-colors duration-150 hover:text-sidebar-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            {navContent}
            <div className="border-t border-sidebar-border p-4">{logoutButtonDrawer}</div>
          </div>
        </div>
      )}
    </>
  )
}
