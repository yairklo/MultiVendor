'use client'

import { useRouter } from 'next/navigation'
import { clearAuthTokens } from '@/lib/auth/tokenStorage'
import React from 'react'

export function AdminLogoutButton({ className, children }: { className?: string; children: React.ReactNode }) {
  const router = useRouter()

  const handleLogout = () => {
    clearAuthTokens()
    router.push('/admin/login')
  }

  return (
    <button onClick={handleLogout} className={className}>
      {children}
    </button>
  )
}
