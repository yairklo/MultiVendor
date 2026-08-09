import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function proxy(request: NextRequest) {
  const token = request.cookies.get('token')?.value
  const { pathname } = request.nextUrl

  // Protected paths
  const isAdmin = pathname.startsWith('/admin') && !pathname.startsWith('/admin/login')
  const isSuperAdmin = pathname.startsWith('/super-admin')
  const isCrm = pathname.startsWith('/crm')

  if ((isAdmin || isSuperAdmin || isCrm) && !token) {
    // Redirect unauthenticated users to the admin login page
    return NextResponse.redirect(new URL('/admin/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/admin/:path*',
    '/super-admin/:path*',
    '/crm/:path*'
  ]
}
