param (
    [switch]$SkipInstall,
    [switch]$SkipMigrate,
    [switch]$SkipSeed,
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"

$PYTHON = "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe"

if (-not (Test-Path $PYTHON)) {
    Write-Error "Python not found at $PYTHON. Please update the path in this script."
    exit 1
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  MediVerify Backend Setup Script" -ForegroundColor Cyan
Write-Host "  Python: $PYTHON" -ForegroundColor DarkGray
Write-Host "============================================" -ForegroundColor Cyan

Set-Location backend

if (-not $SkipInstall) {
    Write-Host "`n[1/4] Installing Python dependencies..." -ForegroundColor Yellow
    & $PYTHON -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Some packages may have failed. Continuing..."
    }
}

if (-not $SkipMigrate) {
    Write-Host "`n[2/4] Running makemigrations..." -ForegroundColor Yellow
    & $PYTHON manage.py makemigrations authentication products inventory verification reports gateway
    Write-Host "`n[2b/4] Running migrate..." -ForegroundColor Yellow
    & $PYTHON manage.py migrate
}

Write-Host "`n[3/4] Creating superuser (regulator / admin123)..." -ForegroundColor Yellow
$create_superuser = @"
from django.contrib.auth import get_user_model
U = get_user_model()
if not U.objects.filter(username='regulator').exists():
    U.objects.create_superuser('regulator','regulator@ppb.go.ke','admin123', role='REGULATOR')
    print('Superuser created.')
else:
    print('Superuser already exists.')
"@
& $PYTHON manage.py shell -c $create_superuser

if (-not $SkipSeed) {
    Write-Host "`n[4/4] Seeding database with sample data..." -ForegroundColor Yellow
    & $PYTHON manage.py seed_data
}

if ($RunTests) {
    Write-Host "`n[5/5] Running test suite..." -ForegroundColor Yellow
    & $PYTHON -m pytest tests/ -v --tb=short
}

Set-Location ..

Write-Host "`n============================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Start backend : cd backend && $PYTHON manage.py runserver" -ForegroundColor White
Write-Host "  Start frontend: cd frontend && npm install && npm run dev" -ForegroundColor White
Write-Host "  Run tests     : cd backend && $PYTHON -m pytest tests/ -v" -ForegroundColor White
Write-Host "  Benchmark     : cd backend && $PYTHON ../evaluation/benchmark.py" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Green
