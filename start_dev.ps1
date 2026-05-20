# start_dev.ps1
$ErrorActionPreference = "Stop"
$projectDir = "D:\Backend_AR_Clothes"
$envFile = "$projectDir\.env"

Write-Host "=== Khoi dong moi truong dev ===" -ForegroundColor Cyan

# -- 1. Kill process cu n?u còn ch?y ----------------------------------------
Write-Host "[1/4] Tat tien trinh cu..." -ForegroundColor Yellow
Get-Process -Name "ngrok" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

# -- 2. Ch?y ngrok background -------------------------------------------------
Write-Host "[2/4] Khoi dong ngrok..." -ForegroundColor Yellow
Start-Process -FilePath "C:\ngrok\ngrok.exe" -ArgumentList "http 8000" -WindowStyle Hidden
Start-Sleep -Seconds 4

# -- 3. L?y URL t? ngrok API ? c?p nh?t .env ----------------------------------
Write-Host "[3/4] Lay ngrok URL..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -TimeoutSec 10
    $ngrokUrl = ($response.tunnels | Where-Object { $_.proto -eq "https" })[0].public_url
    
    if (-not $ngrokUrl) {
        throw "Khong lay duoc URL"
    }

    Write-Host "    ngrok URL: $ngrokUrl" -ForegroundColor Green

    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "BASE_URL=") {
        $envContent = $envContent -replace "(?m)^BASE_URL=.*", "BASE_URL=$ngrokUrl"
    } else {
        $envContent += "`nBASE_URL=$ngrokUrl"
    }
    Set-Content -Path $envFile -Value $envContent.TrimEnd()
    Write-Host "    .env da cap nhat" -ForegroundColor Green

} catch {
    Write-Host "    LOI: Khong ket noi duoc ngrok API - $_" -ForegroundColor Red
    Write-Host "    Kiem tra ngrok da cai va dang nhap chua" -ForegroundColor Red
    exit 1
}

# -- 4. Ch?y FastAPI ----------------------------------------------------------
Write-Host "[4/4] Khoi dong FastAPI..." -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Cyan
Write-Host "API:    http://localhost:8000" -ForegroundColor White
Write-Host "Docs:   http://localhost:8000/docs" -ForegroundColor White
Write-Host "ngrok:  $ngrokUrl" -ForegroundColor White
Write-Host "Models: $ngrokUrl/static/models/" -ForegroundColor White
Write-Host "================================" -ForegroundColor Cyan

Set-Location $projectDir
$env:PYTHONPATH = $projectDir
& "$projectDir\venv\Scripts\Activate.ps1"
python -m uvicorn app.main:app --reload --port 8000 --reload-exclude "FitDiT"
