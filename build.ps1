# DevMind Production Build Script (Windows)
# Builds all components with optimizations and creates production bundle

$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Blue
Write-Host "DevMind Production Build" -ForegroundColor Blue
Write-Host "======================================" -ForegroundColor Blue
Write-Host ""

# Configuration
$BUILD_DIR = "build"
$BUNDLE_NAME = "prod_bundle.tar.gz"
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"

function Print-Status($message) {
    Write-Host "[*] $message" -ForegroundColor Cyan
}

function Print-Success($message) {
    Write-Host "[✓] $message" -ForegroundColor Green
}

function Print-Error($message) {
    Write-Host "[✗] $message" -ForegroundColor Red
}

# Step 1: Clean previous builds
Print-Status "Cleaning previous builds..."
if (Test-Path $BUILD_DIR) {
    Remove-Item -Path $BUILD_DIR -Recurse -Force
}
New-Item -ItemType Directory -Path $BUILD_DIR | Out-Null
Print-Success "Build directory created"

# Step 2: Backend - Install dependencies and run tests
Print-Status "Building backend..."
Set-Location devmind-project

Print-Status "Installing Python dependencies..."
pip install -r requirements.txt --quiet
Print-Success "Dependencies installed"

Print-Status "Running backend tests..."
$testResult = pytest tests/ -v --cov=devmind --cov-report=term-missing --cov-report=html
if ($LASTEXITCODE -ne 0) {
    Print-Error "Backend tests failed"
    exit 1
}
Print-Success "All backend tests passed"

Print-Status "Running linting..."
black --check devmind/
if ($LASTEXITCODE -ne 0) {
    Print-Error "Black formatting check failed (non-critical)"
}
ruff check devmind/
if ($LASTEXITCODE -ne 0) {
    Print-Error "Ruff linting failed (non-critical)"
}
Print-Success "Code quality checks completed"

Set-Location ..

# Step 3: Frontend - Build Next.js app
Print-Status "Building frontend..."
Set-Location devmind-ui

Print-Status "Installing Node dependencies..."
npm ci --quiet
Print-Success "Node dependencies installed"

Print-Status "Building Next.js app..."
npm run build
if ($LASTEXITCODE -ne 0) {
    Print-Error "Frontend build failed"
    exit 1
}
Print-Success "Frontend built successfully"

Set-Location ..

# Step 4: Build Docker images
Print-Status "Building Docker images..."

Print-Status "Building backend image..."
docker build -f docker/backend.Dockerfile -t devmind-backend:latest -t devmind-backend:$TIMESTAMP .
Print-Success "Backend image built"

Print-Status "Building UI image..."
docker build -f docker/ui.Dockerfile -t devmind-ui:latest -t devmind-ui:$TIMESTAMP .
Print-Success "UI image built"

Print-Status "Building Ollama image..."
docker build -f docker/ollama.Dockerfile -t devmind-ollama:latest -t devmind-ollama:$TIMESTAMP .
Print-Success "Ollama image built"

# Step 5: Save Docker images
Print-Status "Saving Docker images..."
New-Item -ItemType Directory -Path "$BUILD_DIR/docker-images" -Force | Out-Null
docker save devmind-backend:latest | gzip > "$BUILD_DIR/docker-images/backend.tar.gz"
docker save devmind-ui:latest | gzip > "$BUILD_DIR/docker-images/ui.tar.gz"
docker save devmind-ollama:latest | gzip > "$BUILD_DIR/docker-images/ollama.tar.gz"
Print-Success "Docker images saved"

# Step 6: Copy configuration files
Print-Status "Copying configuration files..."
New-Item -ItemType Directory -Path "$BUILD_DIR/config" -Force | Out-Null

Copy-Item docker-compose.yml $BUILD_DIR/
Copy-Item .env.example $BUILD_DIR/
Copy-Item -Recurse traefik $BUILD_DIR/
Copy-Item -Recurse monitoring "$BUILD_DIR/config/"
Copy-Item DEPLOYMENT.md $BUILD_DIR/
Copy-Item PERFORMANCE.md $BUILD_DIR/
Copy-Item README.md $BUILD_DIR/ -ErrorAction SilentlyContinue

Print-Success "Configuration files copied"

# Step 7: Create deployment manifests
Print-Status "Creating deployment manifests..."

$installContent = @"
# DevMind Production Deployment

## Quick Start

1. **Load Docker Images**:
   ``````bash
   docker load < docker-images/backend.tar.gz
   docker load < docker-images/ui.tar.gz
   docker load < docker-images/ollama.tar.gz
   ``````

2. **Configure Environment**:
   ``````bash
   cp .env.example .env
   # Edit .env with your configuration
   ``````

3. **Set Permissions** (Linux/Mac):
   ``````bash
   chmod 600 traefik/acme.json
   ``````

4. **Start Services**:
   ``````bash
   docker-compose up -d
   ``````

5. **Verify Deployment**:
   ``````bash
   docker-compose ps
   docker-compose logs -f
   ``````

## Access Points

- Frontend: https://devmind.local
- API: https://api.devmind.local
- API Docs: https://api.devmind.local/docs
- Grafana: https://grafana.devmind.local
- Prometheus: http://localhost:9090

See DEPLOYMENT.md for detailed instructions.
"@

Set-Content -Path "$BUILD_DIR/INSTALL.md" -Value $installContent

$gitCommit = try { git rev-parse --short HEAD } catch { "N/A" }
$buildSize = (Get-ChildItem -Path $BUILD_DIR -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB

$versionContent = @"
DevMind Production Bundle
Version: 1.0.0
Build Date: $(Get-Date)
Commit: $gitCommit

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
- Total Size: $([math]::Round($buildSize, 2)) MB
"@

Set-Content -Path "$BUILD_DIR/VERSION.txt" -Value $versionContent
Print-Success "Deployment manifests created"

# Step 8: Create production bundle
Print-Status "Creating production bundle..."
tar -czf $BUNDLE_NAME -C $BUILD_DIR .
Print-Success "Production bundle created: $BUNDLE_NAME"

# Step 9: Generate checksums
Print-Status "Generating checksums..."
$hash = Get-FileHash -Path $BUNDLE_NAME -Algorithm SHA256
"$($hash.Hash)  $BUNDLE_NAME" | Out-File -FilePath "${BUNDLE_NAME}.sha256"
Print-Success "Checksum generated"

# Step 10: Build summary
Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "Build Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "Bundle: $BUNDLE_NAME"
Write-Host "Size: $([math]::Round((Get-Item $BUNDLE_NAME).Length / 1MB, 2)) MB"
Write-Host "SHA256: $($hash.Hash)"
Write-Host ""
Write-Host "Contents:"
Write-Host "  - Docker images (3)"
Write-Host "  - Configuration files"
Write-Host "  - Deployment guides"
Write-Host "  - docker-compose.yml"
Write-Host ""
Write-Host "To deploy:"
Write-Host "  1. Extract: tar -xzf $BUNDLE_NAME"
Write-Host "  2. Follow: INSTALL.md"
Write-Host ""
Print-Success "Production build completed successfully!"
