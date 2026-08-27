'use client'

import React from 'react'
import {
  LayoutDashboard, Store, CreditCard, LayoutTemplate, Users, ShoppingCart,
  Wallet, Globe, ScrollText, LogOut, Shield,
} from 'lucide-react'
import { AdminNavLink } from '@/components/admin/AdminNavLink'
import { AdminLogoutButton } from '@/components/admin/AdminLogoutButton'
import { AdminMobileNav } from '@/components/admin/AdminMobileNav'

const navItems = [
  { name: 'Overview', href: '/super-admin', icon: LayoutDashboard, exact: true },
  { name: 'Tenants', href: '/super-admin/tenants', icon: Store },
  { name: 'Plans', href: '/super-admin/plans', icon: CreditCard },
  { name: 'Templates', href: '/super-admin/templates', icon: LayoutTemplate },
  { name: 'Users', href: '/super-admin/users', icon: Users },
  { name: 'Orders', href: '/super-admin/orders', icon: ShoppingCart },
  { name: 'Payouts', href: '/super-admin/payouts', icon: Wallet },
  { name: 'Marketplace', href: '/super-admin/marketplace', icon: Globe },
  { name: 'Audit log', href: '/super-admin/audit', icon: ScrollText },
]

function NavLinks() {
  return (
    <nav className="flex-1 space-y-1 p-4">
      {navItems.map((item) => {
        const Icon = item.icon
        return (
          <AdminNavLink key={item.href} href={item.href} exact={item.exact}>
            <Icon className="h-5 w-5" strokeWidth={2} />
            <span>{item.name}</span>
          </AdminNavLink>
        )
      })}
    </nav>
  )
}

export default function SuperAdminLayout({ children }: { children: React.ReactNode }) {
  // The console's copy is English-only (no locale switcher, unlike the
  // storefront) but the root <html> is dir="rtl" lang="he" for the Hebrew
  // storefront. Left inherited, that RTL direction flips this layout's flex
  // order -- the sidebar renders on the right with its border-r drawn at the
  // outer edge of the screen instead of between the sidebar and content.
  // Pin this subtree to ltr until the console itself is localized.
  return (
    <div dir="ltr" lang="en" className="flex min-h-screen bg-background">
      <aside className="hidden w-64 flex-col border-r border-sidebar-border bg-sidebar md:flex">
        <div className="flex h-16 items-center gap-2 border-b border-sidebar-border px-6">
          <Shield className="h-5 w-5 text-primary" strokeWidth={2} />
          <h1 className="font-heading text-xl font-medium tracking-tight text-sidebar-foreground">
            Platform
          </h1>
        </div>
        <NavLinks />
        <div className="border-t border-sidebar-border p-4">
          <AdminLogoutButton className="flex w-full items-center space-x-3 rounded-lg px-3 py-2 text-destructive transition-colors duration-150 hover:bg-destructive/10">
            <LogOut className="h-5 w-5" strokeWidth={2} />
            <span>Log out</span>
          </AdminLogoutButton>
        </div>
      </aside>

      <main className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden">
        <AdminMobileNav
          title="Platform"
          navContent={<NavLinks />}
          logoutButtonCompact={
            <AdminLogoutButton className="text-sm font-medium text-destructive">Log out</AdminLogoutButton>
          }
          logoutButtonDrawer={
            <AdminLogoutButton className="flex w-full items-center space-x-3 rounded-lg px-3 py-2 text-destructive transition-colors duration-150 hover:bg-destructive/10">
              <LogOut className="h-5 w-5" strokeWidth={2} />
              <span>Log out</span>
            </AdminLogoutButton>
          }
        />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-auto p-6 md:p-8">{children}</div>
      </main>
    </div>
  )
}
