# DevMind Build Verification Script
# Quick check of build prerequisites

Write-Host "=====================================" -ForegroundColor Blue
Write-Host "DevMind Build System Verification" -ForegroundColor Blue
Write-Host "=====================================" -ForegroundColor Blue
Write-Host ""

$allGood = $true

# Check Python
Write-Host "Checking Python..." -NoNewline
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.1[1-9]") {
        Write-Host " ✓ $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host " ✗ Need Python 3.11+ (found: $pythonVersion)" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host " ✗ Python not found" -ForegroundColor Red
    $allGood = $false
}

# Check Node.js
Write-Host "Checking Node.js..." -NoNewline
try {
    $nodeVersion = node --version 2>&1
    if ($nodeVersion -match "v1[8-9]" -or $nodeVersion -match "v2[0-9]") {
        Write-Host " ✓ $nodeVersion" -ForegroundColor Green
    } else {
        Write-Host " ✗ Need Node.js 18+ (found: $nodeVersion)" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host " ✗ Node.js not found" -ForegroundColor Red
    $allGood = $false
}

# Check Docker
Write-Host "Checking Docker..." -NoNewline
try {
    $dockerVersion = docker --version 2>&1
    if ($dockerVersion -match "Docker version") {
        Write-Host " ✓ $dockerVersion" -ForegroundColor Green
    } else {
        Write-Host " ✗ Docker not found" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host " ✗ Docker not found" -ForegroundColor Red
    $allGood = $false
}

# Check Docker Compose
Write-Host "Checking Docker Compose..." -NoNewline
try {
    $composeVersion = docker-compose --version 2>&1
    Write-Host " ✓ $composeVersion" -ForegroundColor Green
} catch {
    Write-Host " ⚠ Docker Compose not found (optional)" -ForegroundColor Yellow
}

# Check build files
Write-Host ""
Write-Host "Checking build files..." -ForegroundColor Cyan
$buildFiles = @(
    "build.ps1",
    "build.sh",
    "docker-compose.yml",
    "docker\backend.Dockerfile",
    "docker\ui.Dockerfile",
    "docker\ollama.Dockerfile",
    "devmind-project\requirements.txt",
    "devmind-ui\package.json"
)

foreach ($file in $buildFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file missing" -ForegroundColor Red
        $allGood = $false
    }
}

# Summary
Write-Host ""
Write-Host "=====================================" -ForegroundColor Blue
if ($allGood) {
    Write-Host "✓ All prerequisites met!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can run the build:" -ForegroundColor Cyan
    Write-Host "  .\build.ps1" -ForegroundColor Yellow
} else {
    Write-Host "✗ Some requirements missing" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install missing components and try again." -ForegroundColor Yellow
}
Write-Host "=====================================" -ForegroundColor Blue
