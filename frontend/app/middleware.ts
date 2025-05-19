import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Define public routes that don't require authentication
const publicRoutes = ['/login', '/register']

// Define cookie name for token (must match the one in auth-context.tsx)
const TOKEN_COOKIE = 'docuquery_token'

export function middleware(request: NextRequest) {
  const token = request.cookies.get(TOKEN_COOKIE)
  const { pathname } = request.nextUrl

  // Allow access to public routes without authentication
  if (publicRoutes.includes(pathname)) {
    // If user is already authenticated, redirect to home
    if (token) {
      return NextResponse.redirect(new URL('/', request.url))
    }
    return NextResponse.next()
  }

  // For all other routes, require authentication
  if (!token) {
    // Store the original URL to redirect back after login
    const url = new URL('/login', request.url)
    url.searchParams.set('callbackUrl', pathname)
    return NextResponse.redirect(url)
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
     * - public folder
     */
    '/((?!api|_next/static|_next/image|favicon.ico|public).*)',
  ],
} 