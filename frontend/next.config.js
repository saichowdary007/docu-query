/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://backend:8000/api/v1/:path*', // Use Docker service name instead of localhost
      },
    ]
  },
}

module.exports = nextConfig
