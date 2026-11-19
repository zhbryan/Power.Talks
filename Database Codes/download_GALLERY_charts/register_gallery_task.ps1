<#
.SYNOPSIS
    Register "Power.Talks GALLERY Charts" as its own Windows scheduled task.

.DESCRIPTION
    Creates (or updates) a scheduled task that runs run_gallery_routine.bat,
    kept separate from the existing "Power.Talks Daily Refresh" task:

      * a different start time, so the two never overlap -- the chart routine
        reads thousands of documents, and the daily
        refresh must not be racing it;
      * its own AI budget, so a long chart backfill cannot drain the quota the
        nightly summarizers rely on.

    Every argument is quoted, including the path to the .bat. An unquoted path
    containing spaces is what silently broke an earlier recording task in this
    project.

.PARAMETER Time
    Daily start time, 24h HH:mm. Default 04:30 -- late enough that the 1 AM
    daily refresh has finished (it has run to ~03:50 without its gap backfill,
    and past 06:00 with it), and before the working day.

.PARAMETER AiBudget
    AI calls (one per document) one run may spend. Default 400.

.PARAMETER MaxDocs
    Cap on documents processed per run (0 = no cap). Use it to pace a first
    backfill over several nights.

.PARAMETER NoAi
    Register the task to run with --no-ai (prefilter only, spends no quota).

.PARAMETER Unregister
    Remove the task instead of creating it.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\register_gallery_task.ps1

.EXAMPLE
    # pace the first backfill: 600 documents a night at 4:30 AM
    powershell -ExecutionPolicy Bypass -File .\register_gallery_task.ps1 -MaxDocs 600

.NOTES
    Run from an elevated PowerShell. Verify afterwards with:
        Get-ScheduledTask -TaskName "Power.Talks GALLERY Charts" | Get-ScheduledTaskInfo
    Run it once by hand with:
        Start-ScheduledTask -TaskName "Power.Talks GALLERY Charts"
#>
[CmdletBinding()]
param(
    [string] $Time       = "04:30",
    [int]    $AiBudget   = 400,
    [int]    $MaxDocs    = 0,
    [switch] $NoAi,
    [switch] $Unregister
)

$ErrorActionPreference = "Stop"

$TaskName = "Power.Talks GALLERY Charts"
$Bat = Join-Path $PSScriptRoot "run_gallery_routine.bat"
$WorkDir = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent   # project root

if ($Unregister) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed scheduled task '$TaskName'."
    } else {
        Write-Host "No scheduled task named '$TaskName'."
    }
    return
}

if (-not (Test-Path $Bat)) { throw "Not found: $Bat" }

# Build the argument string the task passes to the .bat.
$taskArgs = @()
if ($NoAi) { $taskArgs += "--no-ai" }
else       { $taskArgs += "--ai-budget"; $taskArgs += "$AiBudget" }
if ($MaxDocs -gt 0) { $taskArgs += "--max-docs"; $taskArgs += "$MaxDocs" }
$argString = ($taskArgs -join " ")

# cmd.exe /c "<quoted bat>" <args> -- the quotes around the .bat path are the
# point: this project has already lost a scheduled task to an unquoted path
# with a space in it.
$action = New-ScheduledTaskAction -Execute "cmd.exe" `
    -Argument "/c `"$Bat`" $argString" `
    -WorkingDirectory $WorkDir

$trigger = New-ScheduledTaskTrigger -Daily -At $Time

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 6)

# Interactive logon token: the run needs a real user session, and
# the AI backend needs the logged-in Claude subscription. A task registered to
# run "whether user is logged on or not" has neither.
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description ("Power.Talks: extract charts from ERCOT stakeholder PDFs and " +
                  "into Documents Database\GALLERY and index " +
                  "them in the gallery schema. Separate from the 1 AM daily " +
                  "refresh.") `
    -Force | Out-Null

Write-Host "Registered '$TaskName'"
Write-Host "  runs daily at $Time"
Write-Host "  command: cmd.exe /c `"$Bat`" $argString"
Write-Host "  logs:    Documents Database\GALLERY\routine_log\"
Write-Host ""
Write-Host "Run it once now with:"
Write-Host "  Start-ScheduledTask -TaskName `"$TaskName`""
