# DevMind Production Deployment Guide

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Domain name (for Let's Encrypt SSL)
- Minimum 8GB RAM, 4 CPU cores
- NVIDIA GPU (optional, for Ollama)

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/devmind.git
cd devmind
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
nano .env
```

### 3. Set ACME Permissions

```bash
chmod 600 traefik/acme.json
```

### 4. Start Stack

```bash
docker-compose up -d
```

### 5. Verify Services

```bash
docker-compose ps
docker-compose logs -f
```

## 📊 Service URLs

- **Frontend**: https://devmind.local
- **Backend API**: https://api.devmind.local
- **API Docs**: https://api.devmind.local/docs
- **Traefik Dashboard**: http://localhost:8080
- **Grafana**: https://grafana.devmind.local
- **Prometheus**: http://localhost:9090

## 🔐 Security Configuration

### JWT Authentication

```python
# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Add to .env as JWT_SECRET_KEY
```

### API Key

```bash
# Generate API key
openssl rand -hex 32
# Add to .env as API_KEY
```

### HTTPS/SSL

- Traefik automatically provisions Let's Encrypt certificates
- Ensure DNS points to your server
- Update `ACME_EMAIL` in `.env`

## 📈 Monitoring

### Prometheus Metrics

Access at: http://localhost:9090

**Available Metrics**:

- `devmind_searches_total` - Total searches
- `devmind_search_latency_seconds` - Search latency
- `devmind_llm_latency_seconds` - LLM generation time
- `devmind_ingestion_jobs_total` - Ingestion jobs
- `devmind_vector_index_size` - Index sizes

### Grafana Dashboards

Access at: https://grafana.devmind.local

1. Login (admin / ${GRAFANA_PASSWORD})
2. Import DevMind dashboard
3. Monitor system health

## 🔧 Production Optimizations

### Backend (FastAPI)

- **Workers**: Set to CPU count: `--workers 4`
- **Gunicorn**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker`
- **Memory**: Limit per worker: `--limit-max-requests 1000`

### Frontend (Next.js)

- Production build: `npm run build`
- Output: Standalone mode (configured)
- CDN: Serve static assets via CDN

### Database

- **Postgres**: Connection pooling enabled
- **Redis**: Used for caching search results
- **Qdrant**: Persistent storage volume

### Scaling

```yaml
# Horizontal scaling
docker-compose up -d --scale backend=3
# Load balancing via Traefik
# Automatic round-robin
```

## 🛡️ Security Checklist

- [x] HTTPS enforced (Traefik)
- [x] JWT authentication (optional)
- [x] API key authentication (optional)
- [x] Rate limiting (SlowAPI)
- [x] CORS restricted (production domains only)
- [x] Security headers (Traefik)
- [x] Secrets in environment variables
- [x] Health checks for all services
- [x] Logs structured (JSON format)

## 🔄 CI/CD Deployment

### GitHub Actions

Automatically:

1. Run tests on PR
2. Build Docker images on merge to main
3. Push to GitHub Container Registry
4. Deploy to production server

### Manual Deployment

```bash
# Pull latest images
docker-compose pull

# Restart services
docker-compose up -d

# Check logs
docker-compose logs -f backend ui
```

## 📝 Maintenance

### Backup

```bash
# Backup volumes
docker run --rm -v devmind_postgres-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz /data

# Backup Qdrant
docker run --rm -v devmind_qdrant-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/qdrant-backup.tar.gz /data
```

### Restore

```bash
# Restore PostgreSQL
docker run --rm -v devmind_postgres-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/postgres-backup.tar.gz -C /

# Restore Qdrant
docker run --rm -v devmind_qdrant-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/qdrant-backup.tar.gz -C /
```

### Update

```bash
# Pull latest code
git pull origin main

# Rebuild images
docker-compose build

# Restart with new images
docker-compose up -d
```

## 🐛 Troubleshooting

### Backend Not Starting

```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Missing ANTHROPIC_API_KEY
# - Database connection failed
# - Port already in use
```

### SSL Certificate Issues

```bash
# Check Traefik logs
docker-compose logs traefik

# Verify DNS
nslookup devmind.local

# Check ACME file permissions
ls -la traefik/acme.json
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Increase workers
# Edit docker-compose.yml backend command

# Scale horizontally
docker-compose up -d --scale backend=3
```

## 📞 Support

- **Documentation**: https://github.com/yourusername/devmind/wiki
- **Issues**: https://github.com/yourusername/devmind/issues
- **Discussions**: https://github.com/yourusername/devmind/discussions

---

**DevMind is production-ready! 🚀**
