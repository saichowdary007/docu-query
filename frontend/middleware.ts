import { NextResponse, NextRequest } from 'next/server'

// Define protected routes that require authentication
const protectedRoutes: string[] = [
  // Add routes that require authentication
  // For example: '/profile', '/dashboard', etc.
]

// Define auth routes (login/register pages)
const authRoutes: string[] = [
  '/login',
  '/register',
  '/forgot-password',
]

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const token = request.cookies.get('docuquery_token')?.value
  
  // Check if the route is protected and user is not authenticated
  if (protectedRoutes.some(route => pathname.startsWith(route)) && !token) {
    // Redirect to login page
    return NextResponse.redirect(new URL('/login', request.url))
  }
  
  // Check if user is trying to access auth routes while already authenticated
  if (authRoutes.includes(pathname) && token) {
    // Redirect to home page
    return NextResponse.redirect(new URL('/', request.url))
  }
  
  // Continue with the request
  return NextResponse.next()
}

// Configure the paths middleware should run on
export const config = {
  matcher: [
    /*
     * Match all request paths except for:
     * - api routes
     * - static files (images, js, css, etc.)
     * - favicon.ico
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
} 