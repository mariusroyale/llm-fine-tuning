# Reset Docker containers and wipe database volume (PowerShell)

Write-Host "🛑 Stopping Docker containers..." -ForegroundColor Yellow
docker compose down

Write-Host "🗑️  Removing containers..." -ForegroundColor Yellow
docker compose rm -f

Write-Host "💾 Removing database volume (pgvector_data)..." -ForegroundColor Yellow
$volumeName = "llm-fine-tuning_pgvector_data"
$altVolumeName = "pgvector_data"

try {
    docker volume rm $volumeName 2>$null
    Write-Host "Removed volume: $volumeName" -ForegroundColor Green
} catch {
    try {
        docker volume rm $altVolumeName 2>$null
        Write-Host "Removed volume: $altVolumeName" -ForegroundColor Green
    } catch {
        Write-Host "Volume not found (may already be removed)" -ForegroundColor Yellow
    }
}

Write-Host "🚀 Starting Docker containers..." -ForegroundColor Green
docker compose up -d

Write-Host "⏳ Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "✅ Docker reset complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Wait for containers to be healthy (check with: docker compose ps)"
Write-Host "  2. Re-index your codebase:"
Write-Host "     docker compose exec app python scripts/index_codebase.py -s data/raw --reset"
