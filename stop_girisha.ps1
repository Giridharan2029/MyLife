Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Stop-Process -Name wscript -Force -ErrorAction SilentlyContinue
Write-Host "Girisha background assistant stopped successfully." -ForegroundColor Green
