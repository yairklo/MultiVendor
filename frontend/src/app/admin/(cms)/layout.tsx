'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { deleteCookie, getCookie } from 'cookies-next'
import {
  LayoutDashboard, Package, FolderTree, ShoppingCart, Users, Tag, Star,
  Settings, LogOut, Menu, X, Sparkles, Palette,
} from 'lucide-react'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const [authorized, setAuthorized] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  useEffect(() => {
    if (!getCookie('token')) {
      router.replace('/admin/login')
      return
    }
    setAuthorized(true)
  }, [router])

  useEffect(() => {
    setMobileNavOpen(false)
  }, [pathname])

  if (!authorized) return null

  const navItems = [
    { name: 'Dashboard', href: '/admin/dashboard', icon: LayoutDashboard },
    { name: 'Products', href: '/admin/products', icon: Package },
    { name: 'Categories', href: '/admin/categories', icon: FolderTree },
    { name: 'Orders', href: '/admin/orders', icon: ShoppingCart },
    { name: 'Customers', href: '/admin/customers', icon: Users },
    { name: 'Coupons', href: '/admin/coupons', icon: Tag },
    { name: 'Reviews', href: '/admin/reviews', icon: Star },
    { name: 'Templates', href: '/admin/templates', icon: Palette },
    { name: 'AI Layout', href: '/admin/ai-layout', icon: Sparkles },
    { name: 'Settings', href: '/admin/settings', icon: Settings },
  ]

  const handleLogout = () => {
    deleteCookie('token')
    deleteCookie('tenantSlug')
    router.push('/admin/login')
  }

  const navLinks = (onNavigate?: () => void) => (
    <nav className="flex-1 p-4 space-y-1">
      {navItems.map((item) => {
        const isActive = pathname.startsWith(item.href)
        const Icon = item.icon
        return (
          <Link
            key={item.name}
            href={item.href}
            onClick={onNavigate}
            className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
              isActive
                ? 'bg-blue-50 text-blue-700 font-medium'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
            }`}
          >
            <Icon className="w-5 h-5" strokeWidth={2} />
            <span>{item.name}</span>
          </Link>
        )
      })}
    </nav>
  )

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar Navigation (desktop) */}
      <aside className="w-64 bg-white border-r border-gray-200 flex-col hidden md:flex">
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            Tenant CMS
          </h1>
        </div>
        {navLinks()}
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={handleLogout}
            className="w-full flex items-center space-x-3 px-3 py-2 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
          >
            <LogOut className="w-5 h-5" strokeWidth={2} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Mobile nav drawer */}
      {mobileNavOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileNavOpen(false)} />
          <div className="relative w-64 bg-white h-full flex flex-col shadow-xl">
            <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200">
              <h1 className="text-lg font-bold text-gray-900">Tenant CMS</h1>
              <button aria-label="Close menu" onClick={() => setMobileNavOpen(false)}>
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            {navLinks(() => setMobileNavOpen(false))}
            <div className="p-4 border-t border-gray-200">
              <button
                onClick={handleLogout}
                className="w-full flex items-center space-x-3 px-3 py-2 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
              >
                <LogOut className="w-5 h-5" strokeWidth={2} />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Mobile Header */}
        <header className="md:hidden h-16 bg-white border-b border-gray-200 flex items-center px-4 justify-between">
          <button aria-label="Open menu" onClick={() => setMobileNavOpen(true)}>
            <Menu className="w-6 h-6 text-gray-700" />
          </button>
          <h1 className="text-lg font-bold text-gray-900">Tenant CMS</h1>
          <button onClick={handleLogout} className="text-sm text-red-600 font-medium">Logout</button>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-auto p-6 md:p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
