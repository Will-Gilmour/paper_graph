# Start all services in unified docker-compose
Write-Host ""
Write-Host "Starting Complete paper_graph Stack..." -ForegroundColor Cyan

# Ensure .env exists (required by docker-compose for pipeline-worker)
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "Creating .env from .env.example (edit .env to set HF_TOKEN, etc.)" -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
    } else {
        Write-Host "WARNING: .env not found. Create it from .env.example and set HF_TOKEN for LLM labeling." -ForegroundColor Yellow
    }
}
Write-Host "  - PostgreSQL database" -ForegroundColor Gray
Write-Host "  - Backend API" -ForegroundColor Gray
Write-Host "  - Frontend UI" -ForegroundColor Gray
Write-Host "  - GPU Pipeline Worker (RAPIDS)" -ForegroundColor Gray
Write-Host ""

# Stop any existing containers
Write-Host "Stopping any existing containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.unified.yml down 2>$null

# Start all services
Write-Host ""
Write-Host "Starting services..." -ForegroundColor Yellow
docker-compose -f docker-compose.unified.yml up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor Green
    Write-Host "  ALL SERVICES STARTED SUCCESSFULLY!" -ForegroundColor Green
    Write-Host "=" * 70 -ForegroundColor Green
    Write-Host ""
    Write-Host "Services:" -ForegroundColor Cyan
    Write-Host "  Frontend:  http://localhost:5173" -ForegroundColor White
    Write-Host "  Backend:   http://localhost:8000" -ForegroundColor White
    Write-Host "  Database:  localhost:5432" -ForegroundColor White
    Write-Host "  Worker:    GPU-enabled, polling for builds" -ForegroundColor White
    Write-Host ""
    Write-Host "Monitor all logs:" -ForegroundColor Yellow
    Write-Host "  docker-compose -f docker-compose.unified.yml logs -f" -ForegroundColor White
    Write-Host ""
    Write-Host "Monitor specific service:" -ForegroundColor Yellow
    Write-Host "  docker-compose -f docker-compose.unified.yml logs -f pipeline-worker" -ForegroundColor White
    Write-Host "  docker-compose -f docker-compose.unified.yml logs -f backend" -ForegroundColor White
    Write-Host ""
    Write-Host "Stop all:" -ForegroundColor Yellow
    Write-Host "  docker-compose -f docker-compose.unified.yml down" -ForegroundColor White
    Write-Host ""
    
    # Show initial status
    Start-Sleep -Seconds 3
    Write-Host "Container Status:" -ForegroundColor Cyan
    docker-compose -f docker-compose.unified.yml ps
    
} else {
    Write-Host ""
    Write-Host "Failed to start services!" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose -f docker-compose.unified.yml logs" -ForegroundColor Yellow
    exit 1
}

