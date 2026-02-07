/** @type {import('next').NextConfig} */
const nextConfig = {
  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000",
  },
  
  // Enable standalone output for Docker
  output: 'standalone',
  
  // Performance optimizations
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  
  // Image optimization
  images: {
    domains: [],
    unoptimized: false,
  },
  
  // Disable telemetry
  telemetry: false,
  
  // Production optimizations
  swcMinify: true,
  
  // Compress responses
  compress: true,
  
  // Strict mode
  reactStrictMode: true,
};

module.exports = nextConfig;
