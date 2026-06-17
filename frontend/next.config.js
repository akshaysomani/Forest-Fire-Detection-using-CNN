/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      // Node.js/Express backend (PostgreSQL users API)
      {
        source: '/api/users/:path*',
        destination: 'http://localhost:5000/api/users/:path*',
      },
      {
        source: '/api/health',
        destination: 'http://localhost:5000/api/health',
      },
      // Python/FastAPI backend (existing)
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
