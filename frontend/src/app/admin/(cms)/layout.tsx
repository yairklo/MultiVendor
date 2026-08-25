'use client'

import React from 'react'
import {
  LayoutDashboard, Package, FolderTree, ShoppingCart, Users, Tag, Star,
  Settings, LogOut, Sparkles, Palette,
} from 'lucide-react'
import { AdminNavLink } from '@/components/admin/AdminNavLink'
import { AdminLogoutButton } from '@/components/admin/AdminLogoutButton'
import { AdminMobileNav } from '@/components/admin/AdminMobileNav'
import { useUiLocale } from '@/context/UiLocaleContext'
import { UiLanguageSwitcher } from '@/components/ui/UiLanguageSwitcher'

function NavLinks() {
  const { t } = useUiLocale()
  const navItems = [
    { name: t('nav.dashboard'), href: '/admin/dashboard', icon: LayoutDashboard },
    { name: t('nav.products'), href: '/admin/products', icon: Package },
    { name: t('nav.categories'), href: '/admin/categories', icon: FolderTree },
    { name: t('nav.orders'), href: '/admin/orders', icon: ShoppingCart },
    { name: t('nav.customers'), href: '/admin/customers', icon: Users },
    { name: t('nav.coupons'), href: '/admin/coupons', icon: Tag },
    { name: t('nav.reviews'), href: '/admin/reviews', icon: Star },
    { name: t('nav.siteDesign'), href: '/admin/ai-layout', icon: Palette },
    { name: t('nav.aiCopilot'), href: '/admin/copilot', icon: Sparkles },
    { name: t('nav.settings'), href: '/admin/settings', icon: Settings },
  ]

  return (
    <nav className="flex-1 p-4 space-y-1">
      {navItems.map((item) => {
        const Icon = item.icon
        return (
          <AdminNavLink key={item.href} href={item.href}>
            <Icon className="w-5 h-5" strokeWidth={2} />
            <span>{item.name}</span>
          </AdminNavLink>
        )
      })}
    </nav>
  )
}

/**
 * Shell for every /admin route. Rendered on the server — proxy.ts middleware (matcher
 * `/admin/:path*`) already redirects unauthenticated requests to /admin/login before this
 * layout ever runs, so there's no need to re-check auth client-side here.
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { t } = useUiLocale()

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-64 flex-col border-e border-sidebar-border bg-sidebar md:flex">
        <div className="flex h-16 items-center justify-between border-b border-sidebar-border px-6">
          <h1 className="font-heading text-xl font-bold bg-gradient-to-r from-primary to-[oklch(0.62_0.19_300)] bg-clip-text text-transparent">
            {t('nav.cmsTitle')}
          </h1>
          <UiLanguageSwitcher className="text-sidebar-foreground/70" />
        </div>
        <NavLinks />
        <div className="border-t border-sidebar-border p-4">
          <AdminLogoutButton className="flex w-full items-center space-x-3 rounded-lg px-3 py-2 text-destructive transition-colors duration-150 hover:bg-destructive/10">
            <LogOut className="w-5 h-5" strokeWidth={2} />
            <span>{t('common.logout')}</span>
          </AdminLogoutButton>
        </div>
      </aside>

      <main className="flex h-screen flex-1 flex-col overflow-hidden">
        <AdminMobileNav
          navContent={<NavLinks />}
          logoutButtonCompact={
            <div className="flex items-center gap-3">
              <UiLanguageSwitcher />
              <AdminLogoutButton className="text-sm font-medium text-destructive">{t('common.logout')}</AdminLogoutButton>
            </div>
          }
          logoutButtonDrawer={
            <AdminLogoutButton className="flex w-full items-center space-x-3 rounded-lg px-3 py-2 text-destructive transition-colors duration-150 hover:bg-destructive/10">
              <LogOut className="w-5 h-5" strokeWidth={2} />
              <span>{t('common.logout')}</span>
            </AdminLogoutButton>
          }
        />

        <div className="flex min-h-0 flex-1 flex-col overflow-auto p-6 md:p-8">{children}</div>
      </main>
    </div>
  )
}
