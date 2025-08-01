import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { checkMissingEnvVars } from '@/lib/env-config'

export function middleware(request: NextRequest) {
  // Skip middleware for the env-check page itself to avoid infinite redirects
  if (request.nextUrl.pathname === '/env-check') {
    return NextResponse.next()
  }

  // Skip middleware for API routes, static files, and Next.js internals
  if (
    request.nextUrl.pathname.startsWith('/api/') ||
    request.nextUrl.pathname.startsWith('/_next/') ||
    request.nextUrl.pathname.includes('.')
  ) {
    return NextResponse.next()
  }

  // Check if any required environment variables are missing
  const missingEnvVars = checkMissingEnvVars()

  // If any env variables are missing, redirect to env-check page
  if (missingEnvVars.length > 0) {
    return NextResponse.redirect(new URL('/env-check', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}