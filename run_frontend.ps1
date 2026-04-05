# Start Streamlit frontend for greenhouse environment
# Opens at http://localhost:8501

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🌱 Starting Greenhouse Web Interface" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 Web UI:  http://localhost:8501" -ForegroundColor Yellow
Write-Host "🛑 Stop:    Press Ctrl+C" -ForegroundColor Yellow
Write-Host ""

Set-Location $PSScriptRoot
streamlit run app.py --logger.level=error
