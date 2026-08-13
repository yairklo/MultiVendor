'use client'

import { useRouter } from 'next/navigation'
import { deleteCookie } from 'cookies-next'
import React from 'react'

export function AdminLogoutButton({ className, children }: { className?: string; children: React.ReactNode }) {
  const router = useRouter()

  const handleLogout = () => {
    deleteCookie('token')
    deleteCookie('tenantSlug')
    router.push('/admin/login')
  }

  return (
    <button onClick={handleLogout} className={className}>
      {children}
    </button>
  )
}
