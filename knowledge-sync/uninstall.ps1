param([string]$Name = 'knowledge-base')
$ErrorActionPreference = 'Stop'
if ($Name -notmatch '^[a-zA-Z0-9-]+$') { throw 'Invalid task name.' }
foreach ($suffix in @('Pull','Sync','Retry','Session')) {
    $task = Get-ScheduledTask -TaskName ('KnowledgeSync-' + $Name + '-' + $suffix) -ErrorAction SilentlyContinue
    if ($task) { $task | Unregister-ScheduledTask -Confirm:$false }
}
Write-Output 'Scheduled tasks removed. Config, logs and the desktop shortcut are preserved.'
