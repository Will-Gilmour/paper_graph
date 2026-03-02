# Stop all services
Write-Host ""
Write-Host "Stopping all paper_graph services..." -ForegroundColor Yellow
Write-Host ""

docker-compose -f docker-compose.unified.yml down

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "All services stopped successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Error stopping services!" -ForegroundColor Red
    exit 1
}

