# DevMind Production Build

This directory contains production build scripts and configuration for creating deployable bundles.

## Quick Build

### Linux/Mac:

```bash
chmod +x build.sh
./build.sh
```

### Windows:

```powershell
.\build.ps1
```

## Build Process

The build script performs the following steps:

1. **Clean**: Remove previous builds
2. **Backend**:
   - Install Python dependencies
   - Run tests (pytest with coverage)
   - Run linting (black, ruff)
3. **Frontend**:
   - Install Node dependencies
   - Build Next.js app (standalone mode)
4. **Docker**:
   - Build 3 Docker images (backend, UI, Ollama)
   - Tag with timestamp
5. **Bundle**:
   - Save Docker images as tar.gz
   - Copy configuration files
   - Create deployment manifests
   - Package as `prod_bundle.tar.gz`
6. **Verify**:
   - Generate SHA256 checksum
   - Create build summary

## Output

After successful build, you'll have:

```
prod_bundle.tar.gz          # Production bundle (compressed)
prod_bundle.tar.gz.sha256   # Checksum file
build/                      # Build directory (can be deleted)
```

## Bundle Contents

```
prod_bundle.tar.gz
├── docker-images/
│   ├── backend.tar.gz      # FastAPI backend image
│   ├── ui.tar.gz           # Next.js frontend image
│   └── ollama.tar.gz       # Ollama LLM image
├── config/
│   └── monitoring/         # Prometheus/Grafana configs
├── traefik/                # Reverse proxy config
├── docker-compose.yml      # Service orchestration
├── .env.example            # Environment template
├── INSTALL.md              # Installation guide
├── DEPLOYMENT.md           # Detailed deployment docs
├── PERFORMANCE.md          # Performance optimization guide
└── VERSION.txt             # Build version info
```

## Deployment

1. **Transfer bundle to server**:

   ```bash
   scp prod_bundle.tar.gz user@server:/opt/devmind/
   ```

2. **Extract on server**:

   ```bash
   cd /opt/devmind
   tar -xzf prod_bundle.tar.gz
   ```

3. **Follow installation**:
   ```bash
   cat INSTALL.md
   ```

## Build Requirements

### Software:

- Python 3.11+
- Node.js 18+
- Docker 24+
- Git

### Disk Space:

- ~10GB for build process
- ~2GB for final bundle

### Time:

- ~15-20 minutes (depending on hardware)

## Customization

### Skip Tests:

Edit build script and comment out:

```bash
# pytest tests/ ...
```

### Custom Image Tags:

Change in build script:

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker build ... -t devmind-backend:$TIMESTAMP
```

### Include Additional Files:

Add to "Copy configuration files" section:

```bash
cp your-file.txt $BUILD_DIR/
```

## Verification

After build, verify:

```bash
# Check bundle size
ls -lh prod_bundle.tar.gz

# Verify checksum
sha256sum -c prod_bundle.tar.gz.sha256

# List contents
tar -tzf prod_bundle.tar.gz | head -20
```

## Troubleshooting

### Build Fails at Tests:

- Check test output
- Ensure all dependencies installed
- Run tests manually: `pytest tests/ -v`

### Docker Build Fails:

- Check Docker daemon is running
- Ensure sufficient disk space
- Check Dockerfile syntax

### Bundle Too Large:

- Normal size: 1.5-2.5GB
- If larger, check for:
  - Cached build artifacts
  - Unnecessary files in context

## CI/CD Integration

The build script can be integrated into CI/CD:

```yaml
# GitHub Actions example
- name: Build production bundle
  run: |
    chmod +x build.sh
    ./build.sh

- name: Upload artifact
  uses: actions/upload-artifact@v3
  with:
    name: devmind-production
    path: prod_bundle.tar.gz
```

## Support

For issues:

1. Check build logs
2. Review DEPLOYMENT.md
3. Check component-specific READMEs

---

**DevMind Production Build System v1.0.0**
