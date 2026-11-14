# Placement: infrastructure/scheduler/register_scheduled_import.ps1
# Creates (or replaces) a daily Windows scheduled task that imports Tanitjobs offers
# into this machine's local database. No administrator rights needed: the task runs
# as the current user, only while that user is logged in. A missed run (PC off)
# starts as soon as possible after the next login.
#
#   powershell -ExecutionPolicy Bypass -File infrastructure\scheduler\register_scheduled_import.ps1
#   powershell -ExecutionPolicy Bypass -File infrastructure\scheduler\register_scheduled_import.ps1 -At 13:30
#   powershell -ExecutionPolicy Bypass -File infrastructure\scheduler\register_scheduled_import.ps1 -Remove

param(
    [string]$At = "07:00",
    [string]$TaskName = "MaharaMatch Tanitjobs import",
    [switch]$Remove
)
$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed the scheduled task '$TaskName' (if it existed)."
    exit 0
}

$script = Join-Path $PSScriptRoot "run_scheduled_import.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`"" `
    -WorkingDirectory (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Principal $principal -Description "Mahara Match: daily Tanitjobs import into the local database (infrastructure/scheduler)." `
    -Force | Out-Null
$next = (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
Write-Host "Scheduled task '$TaskName' runs every day at $At (next run: $next)."
Write-Host "Run it now with: Start-ScheduledTask -TaskName '$TaskName'"
