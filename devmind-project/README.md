# DevMind Backend - README

## Overview

FastAPI-based backend for the DevMind intelligent code assistant. Provides RESTful API and WebSocket endpoints for semantic search, file ingestion, and AI-powered chat.

## Features

- **Embedding Service**: Sentence Transformers with multi-model support
- **File Ingestion**: Tree-sitter AST parsing for multiple languages
- **Hybrid Retrieval**: Vector (Qdrant) + Keyword (BM25) search
- **LLM Orchestration**: Multi-provider support (Ollama, Claude)
- **Real-time Chat**: WebSocket streaming for chat responses
- **Monitoring**: Prometheus metrics built-in

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn main:app --reload --port 8000
```

## API Endpoints

### System

- `GET /health` - Health check
- `GET /stats` - System statistics
- `GET /metrics` - Prometheus metrics

### Embedding

- `POST /embed` - Generate embeddings

### Search

- `POST /search` - Semantic search

### Ingestion

- `POST /ingest/start` - Start ingestion job
- `GET /ingest/status/{job_id}` - Check job status
- `GET /ingest/jobs` - List all jobs

### Chat

- `POST /chat` - Synchronous chat
- `WebSocket /chat/stream` - Streaming chat
- `POST /chat/explain` - Explain code
- `POST /chat/debug` - Debug assistance

## Configuration

```bash
# .env
ANTHROPIC_API_KEY=your_key
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
QDRANT_HOST=localhost
REDIS_URL=redis://localhost:6379
```

## Development

```bash
# Run tests
pytest tests/ -v --cov=devmind

# Lint
black devmind/
ruff check devmind/

# Type check
mypy devmind/
```

## Architecture

```
devmind/
├── api/             # FastAPI routes and models
├── core/            # Dependency injection, cache
├── embeddings/      # Embedding service
├── ingestion/       # File scanning and processing
├── processing/      # Code/doc processors
├── chunking/        # Text chunking
├── retrieval/       # Search engine
├── vectorstore/     # Vector DB clients
└── llm/             # LLM providers and chat
```

## Documentation

See parent README.md for full documentation.
