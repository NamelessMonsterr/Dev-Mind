# DevMind UI - Build & Deploy Guide

## Local Development

### Setup

```bash
cd devmind-ui
npm install
npm run dev
```

The UI will be available at http://localhost:3000

### Environment Variables

Copy `.env.local.example` to `.env.local`:

```bash
cp .env.local.example .env.local
```

Update `NEXT_PUBLIC_API_URL` if your backend is not on `localhost:8000`.

## Production Build

### Option 1: Local Build

```bash
npm run build
npm start
```

### Option 2: Docker Build

```bash
# Build the image
docker build -t devmind-ui:latest .

# Run the container
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://your-api-url:8000 \
  devmind-ui:latest
```

### Option 3: Docker Compose

In the root directory:

```bash
docker-compose up -d devmind-ui
```

## Deployment Checklist

- [ ] Update `NEXT_PUBLIC_API_URL` to production API URL
- [ ] Build production image with `docker build`
- [ ] Test login/register flow
- [ ] Verify token refresh works
- [ ] Check logout functionality
- [ ] Test protected routes
- [ ] Verify CORS configuration on backend

## Features

### Authentication

- ✅ User Registration
- ✅ User Login (email or username)
- ✅ JWT Token Management
- ✅ Auto Token Refresh
- ✅ Logout
- ✅ Protected Routes
- ✅ User Profile Display

### UI Components

- ✅ Login Page (glassmorphism design)
- ✅ Register Page (glassmorphism design)
- ✅ Sidebar with User Profile
- ✅ Logout Button
- ✅ Loading States
- ✅ Error Handling

## Build Output

The production build creates:

- **Standalone Server**: Optimized Node.js server
- **Static Assets**: Compiled CSS, JS, images
- **Server Components**: Pre-rendered pages

Build size: ~3-5 MB (compressed)  
Image size: ~150 MB (with Node.js)

## Troubleshooting

**Issue**: Login fails with CORS error  
**Solution**: Check `ALLOWED_ORIGINS` in backend `.env`

**Issue**: Token expires immediately  
**Solution**: Check system time sync between frontend/backend

**Issue**: Build fails  
**Solution**: Run `npm install` and ensure Node 18+ is installed
