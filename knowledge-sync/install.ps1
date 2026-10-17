param(
    [Parameter(Mandatory)][string]$Repository,
    [ValidateSet('primary', 'secondary')][string]$Profile = 'primary',
    [string]$Name = 'knowledge-base',
    [string]$Python = 'python.exe',
    [string]$RuntimeRoot = (Join-Path $env:USERPROFILE '.knowledge-sync')
)
$ErrorActionPreference = 'Stop'
if ($Name -notmatch '^[a-zA-Z0-9-]+$') { throw 'Name must contain only letters, digits and hyphens.' }
$repoPath = (Resolve-Path -LiteralPath $Repository).Path
$pythonPath = (Get-Command $Python -ErrorAction Stop).Source
$pythonwPath = Join-Path (Split-Path $pythonPath) 'pythonw.exe'
if (!(Test-Path -LiteralPath $pythonwPath)) { throw 'A real Python installation with pythonw.exe is required.' }
& $pythonPath -c 'import sys, tkinter; assert sys.version_info >= (3, 11)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ and Tkinter are required.' }
$gitPath = (Get-Command git.exe -ErrorAction Stop).Source
$remoteUrl = (& $gitPath -C $repoPath remote get-url origin).Trim()
$branch = (& $gitPath -C $repoPath branch --show-current).Trim()
if (!$remoteUrl -or !$branch -or $LASTEXITCODE -ne 0) { throw 'Repository needs origin and a checked-out branch.' }
# AppData can be virtualized when installed from a packaged desktop host.
# A regular user-profile directory is also visible to Task Scheduler.
$runtime = Join-Path $RuntimeRoot $Name
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$configPath = Join-Path $runtime 'config.json'
$prefix = 'KnowledgeSync-' + $Name
$config = @{
    repository=$repoPath; runtime=$runtime; remote='origin'; branch=$branch; remote_url=$remoteUrl;
    git=$gitPath; python=$pythonPath; pythonw=$pythonwPath; profile=$Profile;
    quiet_minutes=15; max_changed_files=40; max_file_mb=25;
    scheduler_enabled=$true; notifications=$true; task_prefix=$prefix;
    installed_at=[DateTimeOffset]::Now.ToString('o')
}
if (Test-Path -LiteralPath $configPath) {
    $oldConfig = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    if ($oldConfig.repository -ne $repoPath) { throw 'This task name already belongs to a different repository.' }
    foreach ($key in @('quiet_minutes', 'max_changed_files', 'max_file_mb', 'notifications')) {
        if ($null -ne $oldConfig.$key) { $config[$key] = $oldConfig.$key }
    }
}
$config | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
$userSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
function Esc([string]$Value) { [System.Security.SecurityElement]::Escape($Value) }
$launcherPath = Join-Path $PSScriptRoot 'run.ps1'
$powershellPath = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
function Register-Worker([string]$Suffix, [string]$Action, [string]$Triggers) {
    $arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -File "' + $launcherPath + '" -Action ' + $Action + ' -Config "' + $configPath + '"'
    $xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
 <RegistrationInfo><Description>Knowledge Sync: $Action ($Profile). Local Git worker, no AI service.</Description></RegistrationInfo>
 <Triggers>$Triggers</Triggers>
 <Principals><Principal id="User"><UserId>$userSid</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
 <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><StartWhenAvailable>true</StartWhenAvailable><RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable><AllowStartOnDemand>true</AllowStartOnDemand><Enabled>true</Enabled><WakeToRun>false</WakeToRun><ExecutionTimeLimit>PT10M</ExecutionTimeLimit></Settings>
 <Actions Context="User"><Exec><Command>$(Esc $powershellPath)</Command><Arguments>$(Esc $arguments)</Arguments><WorkingDirectory>$(Esc $PSScriptRoot)</WorkingDirectory></Exec></Actions>
</Task>
"@
    Register-ScheduledTask -TaskName ($prefix + '-' + $Suffix) -Xml $xml -Force | Out-Null
}
function Daily([string]$Clock) {
    '<CalendarTrigger><StartBoundary>2026-01-01T' + $Clock + ':00+08:00</StartBoundary><Enabled>true</Enabled><ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger>'
}
if ($Profile -eq 'primary') {
    Register-Worker 'Sync' 'sync' ((Daily '09:00') + (Daily '12:30') + (Daily '18:30'))
} else {
    # Login/unlock handles pulls; checking local changes every 30 minutes works
    # at arbitrary evening/weekend hours. Tasks run only while this user is logged on.
    Register-Worker 'Sync' 'sync' '<CalendarTrigger><Repetition><Interval>PT30M</Interval><Duration>P1D</Duration><StopAtDurationEnd>false</StopAtDurationEnd></Repetition><StartBoundary>2026-01-01T00:00:00+08:00</StartBoundary><Enabled>true</Enabled><ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger>'
}
Unregister-ScheduledTask -TaskName ($prefix + '-Pull') -Confirm:$false -ErrorAction SilentlyContinue
Register-Worker 'Retry' 'retry' ''
$session = '<LogonTrigger><Enabled>true</Enabled><UserId>' + $userSid + '</UserId><Delay>PT30S</Delay></LogonTrigger><SessionStateChangeTrigger><Enabled>true</Enabled><StateChange>SessionUnlock</StateChange><UserId>' + $userSid + '</UserId><Delay>PT10S</Delay></SessionStateChangeTrigger>'
Register-Worker 'Session' 'session' $session
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Knowledge Sync.lnk'))
$shortcut.TargetPath = $pythonwPath
$shortcut.Arguments = '"' + (Join-Path $PSScriptRoot 'status.py') + '" --config "' + $configPath + '"'
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = 'Knowledge Sync status, retry and pause'
$shortcut.Save()
Write-Output "Installed profile: $Profile"
Write-Output "Config: $configPath"
Get-ScheduledTask -TaskName ($prefix + '-*') | Select-Object TaskName,State
