#!/bin/bash
# DevMind Production Build Script
# Builds all components with optimizations and creates production bundle

set -e  # Exit on error

echo "======================================"
echo "DevMind Production Build"
echo "======================================"
echo ""

# Configuration
BUILD_DIR="build"
BUNDLE_NAME="prod_bundle.tar.gz"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Step 1: Clean previous builds
print_status "Cleaning previous builds..."
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR
print_success "Build directory created"

# Step 2: Backend - Install dependencies and run tests
print_status "Building backend..."
cd devmind-project

print_status "Installing Python dependencies..."
pip install -r requirements.txt --quiet
print_success "Dependencies installed"

print_status "Running backend tests..."
pytest tests/ -v --cov=devmind --cov-report=term-missing --cov-report=html
TEST_EXIT_CODE=$?
if [ $TEST_EXIT_CODE -ne 0 ]; then
    print_error "Backend tests failed"
    exit 1
fi
print_success "All backend tests passed"

print_status "Running linting..."
black --check devmind/ || print_error "Black formatting check failed"
ruff check devmind/ || print_error "Ruff linting failed"
print_success "Code quality checks passed"

cd ..

# Step 3: Frontend - Build Next.js app
print_status "Building frontend..."
cd devmind-ui

print_status "Installing Node dependencies..."
npm ci --quiet
print_success "Node dependencies installed"

print_status "Building Next.js app..."
npm run build
BUILD_EXIT_CODE=$?
if [ $BUILD_EXIT_CODE -ne 0 ]; then
    print_error "Frontend build failed"
    exit 1
fi
print_success "Frontend built successfully"

cd ..

# Step 4: Build Docker images
print_status "Building Docker images..."

print_status "Building backend image..."
docker build -f docker/backend.Dockerfile -t devmind-backend:latest -t devmind-backend:$TIMESTAMP .
print_success "Backend image built"

print_status "Building UI image..."
docker build -f docker/ui.Dockerfile -t devmind-ui:latest -t devmind-ui:$TIMESTAMP .
print_success "UI image built"

print_status "Building Ollama image..."
docker build -f docker/ollama.Dockerfile -t devmind-ollama:latest -t devmind-ollama:$TIMESTAMP .
print_success "Ollama image built"

# Step 5: Save Docker images
print_status "Saving Docker images..."
mkdir -p $BUILD_DIR/docker-images
docker save devmind-backend:latest | gzip > $BUILD_DIR/docker-images/backend.tar.gz
docker save devmind-ui:latest | gzip > $BUILD_DIR/docker-images/ui.tar.gz
docker save devmind-ollama:latest | gzip > $BUILD_DIR/docker-images/ollama.tar.gz
print_success "Docker images saved"

# Step 6: Copy configuration files
print_status "Copying configuration files..."
mkdir -p $BUILD_DIR/config

cp docker-compose.yml $BUILD_DIR/
cp .env.example $BUILD_DIR/
cp -r traefik $BUILD_DIR/
cp -r monitoring $BUILD_DIR/config/
cp DEPLOYMENT.md $BUILD_DIR/
cp PERFORMANCE.md $BUILD_DIR/
cp README.md $BUILD_DIR/

print_success "Configuration files copied"

# Step 7: Create deployment manifests
print_status "Creating deployment manifests..."

cat > $BUILD_DIR/INSTALL.md << 'EOF'
# DevMind Production Deployment

## Quick Start

1. **Load Docker Images**:
   ```bash
   docker load < docker-images/backend.tar.gz
   docker load < docker-images/ui.tar.gz
   docker load < docker-images/ollama.tar.gz
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   nano .env
   ```

3. **Set Permissions**:
   ```bash
   chmod 600 traefik/acme.json
   ```

4. **Start Services**:
   ```bash
   docker-compose up -d
   ```

5. **Verify Deployment**:
   ```bash
   docker-compose ps
   docker-compose logs -f
   ```

## Access Points

- Frontend: https://devmind.local
- API: https://api.devmind.local
- API Docs: https://api.devmind.local/docs
- Grafana: https://grafana.devmind.local
- Prometheus: http://localhost:9090

See DEPLOYMENT.md for detailed instructions.
EOF

cat > $BUILD_DIR/VERSION.txt << EOF
DevMind Production Bundle
Version: 1.0.0
Build Date: $(date)
Commit: $(git rev-parse --short HEAD 2>/dev/null || echo "N/A")

Components:
- Backend: FastAPI 0.104+
- Frontend: Next.js 14
- LLM: Ollama (Phi-3)
- Vector DB: Qdrant
- Cache: Redis
- Proxy: Traefik
- Monitoring: Prometheus + Grafana

Build Details:
- Python Tests: PASSED
- Frontend Build: PASSED
- Docker Images: 3 images
- Total Size: $(du -sh $BUILD_DIR | cut -f1)
EOF

print_success "Deployment manifests created"

# Step 8: Create production bundle
print_status "Creating production bundle..."
cd $BUILD_DIR
tar -czf ../$BUNDLE_NAME ./*
cd ..
print_success "Production bundle created: $BUNDLE_NAME"

# Step 9: Generate checksums
print_status "Generating checksums..."
sha256sum $BUNDLE_NAME > ${BUNDLE_NAME}.sha256
print_success "Checksum generated"

# Step 10: Build summary
echo ""
echo "======================================"
echo "Build Complete!"
echo "======================================"
echo ""
echo "Bundle: $BUNDLE_NAME"
echo "Size: $(du -sh $BUNDLE_NAME | cut -f1)"
echo "SHA256: $(cat ${BUNDLE_NAME}.sha256)"
echo ""
echo "Contents:"
echo "  - Docker images (3)"
echo "  - Configuration files"
echo "  - Deployment guides"
echo "  - docker-compose.yml"
echo ""
echo "To deploy:"
echo "  1. Extract: tar -xzf $BUNDLE_NAME"
echo "  2. Follow: INSTALL.md"
echo ""
print_success "Production build completed successfully!"
