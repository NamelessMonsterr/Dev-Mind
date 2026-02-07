# DevMind UI - README

## Overview

Next.js 14 web application for DevMind. Provides modern, responsive interface for code search, AI chat, and system management.

## Features

- **Real-time Chat**: WebSocket streaming with provider selection
- **Semantic Search**: Code search with syntax highlighting
- **Job Management**: Monitor ingestion jobs
- **Stats Dashboard**: System metrics and analytics
- **Dark Theme**: VSCode-inspired design

## Quick Start

```bash
# Install dependencies
npm install

# Development
npm run dev

# Open browser
open http://localhost:3000
```

## Pages

- `/` - Home with feature cards
- `/chat` - AI-powered chat
- `/search` - Semantic code search
- `/ingest` - File ingestion management
- `/stats` - System statistics
- `/settings` - Configuration

## Build

```bash
# Production build
npm run build

# Start production server
npm start

# Or use standalone (Docker)
node .next/standalone/server.js
```

## Configuration

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Development

```bash
# Format code
npm run format

# Lint
npm run lint

# Type check
npm run type-check
```

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS
- **UI Components**: ShadCN UI
- **Code Highlighting**: Prism.js
- **WebSocket**: Native WebSocket API

## Project Structure

```
devmind-ui/
├── app/             # Next.js app routes
├── components/      # React components
├── lib/             # API clients and utilities
├── public/          # Static assets
└── styles/          # Global styles
```

## Documentation

See parent README.md for full documentation.
