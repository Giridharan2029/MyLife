if (-not $env:GEMINI_API_KEY) {
    Write-Host "Please set `$env:GEMINI_API_KEY before running." -ForegroundColor Yellow
}
python speech_to_speech.py
