/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  env: {
    // These will be replaced by Vercel environment variables
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,
    NEXT_PUBLIC_BACKEND_API_KEY: process.env.NEXT_PUBLIC_BACKEND_API_KEY,
  },
  images: {
    domains: ['localhost', 'docuquery-ai-backend.onrender.com'], // Updated with the actual render domain
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: process.env.NEXT_PUBLIC_BACKEND_URL 
          ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/:path*` 
          : 'http://localhost:8000/api/v1/:path*', // Fallback to localhost in development
      },
    ]
  },
  // Ensure the server listens on all network interfaces in Docker
  // The experimental.outputStandalone has been moved to the top-level 'output: "standalone"' key
}

// In docker environment, we need to set the hostname
if (process.env.NODE_ENV === 'production') {
  // This ensures the server binds to 0.0.0.0 instead of localhost in Docker
  nextConfig.experimental = {
    ...(nextConfig.experimental || {}), // Initialize experimental if it's not already defined
    outputFileTracingRoot: undefined,
  }
}

module.exports = nextConfig
