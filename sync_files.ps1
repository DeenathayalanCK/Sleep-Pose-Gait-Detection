# Run this from E:\Sleep-monitoring-system to verify all files are up to date
# Usage: .\sync_files.ps1

$files = @(
    "app\main.py",
    "app\config.py",
    "app\api\routes.py",
    "app\api\server.py",
    "app\database\db.py",
    "app\database\models.py",
    "app\database\repository.py",
    "app\detection\sleep_pose_detector.py",
    "app\detection\posture_classifier.py",
    "app\engine\fatigue_engine.py",
    "app\engine\state_analyzer.py",
    "app\utils\annotator.py",
    "app\services\snapshot_service.py",
    "app\services\event_logger.py",
    "app\llm\ollama_client.py",
    "frontend\src\components\Events.jsx",
    "frontend\src\components\LiveStatus.jsx",
    "docker-compose.yml",
    ".env"
)

Write-Host "`n=== File Check ===" -ForegroundColor Cyan
foreach ($f in $files) {
    if (Test-Path $f) {
        $age = (Get-Item $f).LastWriteTime
        Write-Host "  OK  $f  ($age)" -ForegroundColor Green
    } else {
        Write-Host "  MISSING  $f" -ForegroundColor Red
    }
}

Write-Host "`n=== Checking for stale main.py ===" -ForegroundColor Cyan
$mainContent = Get-Content "app\main.py" -Raw -ErrorAction SilentlyContinue
if ($mainContent -match "log_event") {
    Write-Host "  STALE: app\main.py still contains log_event call - replace it!" -ForegroundColor Red
} else {
    Write-Host "  OK: app\main.py is up to date" -ForegroundColor Green
}

Write-Host "`nDone." -ForegroundColor Cyan