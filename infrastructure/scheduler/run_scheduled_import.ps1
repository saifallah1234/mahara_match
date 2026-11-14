# Placement: infrastructure/scheduler/run_scheduled_import.ps1
# One scheduled Tanitjobs import. Called by the Windows scheduled task that
# register_scheduled_import.ps1 creates; can also be run by hand to test it.
# Output: logs/imports/scheduled-<date>.log (one file per day, appended).

param([string]$Source = "tanitjobs")
$ErrorActionPreference = "Continue"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repo
$logDir = Join-Path $repo "logs\imports"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir ("scheduled-{0:yyyy-MM-dd}.log" -f (Get-Date))
function Write-Log([string]$message) { "{0:yyyy-MM-dd HH:mm:ss} $message" -f (Get-Date) | Out-File -Append -Encoding utf8 $log }

Write-Log "Scheduled import of $Source starting."

# The database runs in Docker (infrastructure/postgres). Docker Desktop must be running.
docker info --format "{{.ServerVersion}}" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Log "Docker is not running: skipped."; exit 1 }
docker start mahara-postgres 2>$null | Out-Null

$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) { Write-Log "uv not found on PATH: skipped."; exit 1 }

$env:PYTHONIOENCODING = "utf-8"
# cmd.exe appends the bytes as they are (UTF-8); PowerShell 5.1 redirection would write UTF-16.
cmd.exe /d /c "`"$uv`" run --frozen python -m pipelines.ingestion.offer_import $Source --scheduled --headless >> `"$log`" 2>&1"
$code = $LASTEXITCODE
Write-Log "Scheduled import of $Source finished with exit code $code."
exit $code
