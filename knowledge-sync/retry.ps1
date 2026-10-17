param([Parameter(Mandatory)][string]$TaskName, [Parameter(Mandatory)][long]$Epoch)
$ErrorActionPreference = 'Stop'
$at = [DateTimeOffset]::FromUnixTimeSeconds($Epoch).LocalDateTime
$trigger = New-ScheduledTaskTrigger -Once -At $at
Set-ScheduledTask -TaskName $TaskName -Trigger $trigger | Out-Null
