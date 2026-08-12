'use client'

import React, { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { Menu, X } from 'lucide-react'

export function AdminMobileNav({
  navContent,
  logoutButtonCompact,
  logoutButtonDrawer,
}: {
  navContent: React.ReactNode
  logoutButtonCompact: React.ReactNode
  logoutButtonDrawer: React.ReactNode
}) {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  useEffect(() => {
    setOpen(false)
  }, [pathname])

  return (
    <>
      <header className="md:hidden h-16 bg-white border-b border-gray-200 flex items-center px-4 justify-between">
        <button aria-label="Open menu" onClick={() => setOpen(true)}>
          <Menu className="w-6 h-6 text-gray-700" />
        </button>
        <h1 className="text-lg font-bold text-gray-900">Tenant CMS</h1>
        {logoutButtonCompact}
      </header>

      {open && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <div className="relative w-64 bg-white h-full flex flex-col shadow-xl">
            <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200">
              <h1 className="text-lg font-bold text-gray-900">Tenant CMS</h1>
              <button aria-label="Close menu" onClick={() => setOpen(false)}>
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            {navContent}
            <div className="p-4 border-t border-gray-200">{logoutButtonDrawer}</div>
          </div>
        </div>
      )}
    </>
  )
}
