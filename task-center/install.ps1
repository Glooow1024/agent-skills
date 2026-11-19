param(
    [string]$Python,
    [switch]$NoLaunch,
    [switch]$WithBridge,
    [switch]$WithKnowledgeSync
)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$repoRoot = Split-Path $taskRoot -Parent
$orbitRoot = Join-Path $env:USERPROFILE '.orbit'

function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed (exit $LASTEXITCODE). Installation not completed." }
}
function Install-Package([string]$Id, [switch]$UserScope) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (!$winget) { throw "Install $Id manually (winget/App Installer unavailable), then rerun this installer." }
    $options = @('install', '--id', $Id, '--exact', '--source', 'winget', '--silent', '--accept-package-agreements', '--accept-source-agreements')
    if ($UserScope) { $options += @('--scope', 'user') }
    Invoke-Checked $winget.Source $options
}
function Find-Python {
    $candidates = @()
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        # An installed launcher can have no Python registered. Keep searching.
        try {
            $launched = & $launcher.Source -3 -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0) { $candidates += $launched }
        } catch { }
    }
    $candidates += @(Get-ChildItem -Path "$env:LOCALAPPDATA/Programs/Python/Python*/python.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -ExpandProperty FullName)
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if ($candidate -like '*\WindowsApps\*') { continue }
        try {
            & $candidate -c 'import sys, tkinter, venv; assert sys.version_info >= (3,11)' 2>$null
            if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath (Join-Path (Split-Path $candidate) 'pythonw.exe'))) { return $candidate }
        } catch { }
    }
}
function Find-Program([string]$Name, [string[]]$Candidates) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    foreach ($candidate in $Candidates) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
}

if ($env:OS -ne 'Windows_NT') { throw 'Orbit desktop installer requires Windows.' }
if ($Python) {
    $Python = (Get-Command $Python -ErrorAction Stop).Source
    Invoke-Checked $Python @('-c', 'import sys, tkinter, venv; assert sys.version_info >= (3,11)')
} else {
    $Python = Find-Python
    if (!$Python) {
        Write-Host 'Installing Python 3.13 with Tk and venv...'
        Install-Package 'Python.Python.3.13' -UserScope
        $Python = Find-Python
        if (!$Python) { throw 'Python installation could not be verified. Rerun with -Python <python.exe>.' }
    }
}
$venv = Join-Path $orbitRoot 'venv'
$venvPython = Join-Path $venv 'Scripts/python.exe'
if (!(Test-Path -LiteralPath $venv)) {
    Write-Host 'Creating isolated Orbit Python environment...'
    Invoke-Checked $Python @('-m', 'venv', $venv)
}
if (!(Test-Path -LiteralPath $venvPython)) { throw "Incomplete environment at $venv. Repair it before retrying; existing files were preserved." }
Invoke-Checked $venvPython @('-c', 'import sys, tkinter; assert sys.version_info >= (3,11)')
& $venvPython -c 'import importlib.util, sys; from importlib.metadata import version; sys.exit(0 if importlib.util.find_spec(''psutil'') and 6 <= int(version(''psutil'').split(''.'')[0]) < 8 else 1)' 2>$null
if ($LASTEXITCODE -ne 0) {
    Invoke-Checked $venvPython @('-m', 'ensurepip')
    Invoke-Checked $venvPython @('-m', 'pip', 'install', '--disable-pip-version-check', '--only-binary=:all:', '-r', (Join-Path $taskRoot 'requirements.txt'))
}
Invoke-Checked $venvPython @('-c', 'import tkinter, psutil; root=tkinter.Tk(); root.withdraw(); root.update(); root.destroy()')
$pythonWindow = Join-Path $venv 'Scripts/pythonw.exe'
if (!(Test-Path -LiteralPath $pythonWindow)) { throw 'pythonw.exe is missing from the Orbit environment.' }

if ($WithKnowledgeSync) {
    $gitCandidates = @("$env:ProgramFiles/Git/cmd/git.exe", "$env:LOCALAPPDATA/Programs/Git/cmd/git.exe")
    $git = Find-Program 'git.exe' $gitCandidates
    if (!$git) { Install-Package 'Git.Git'; $git = Find-Program 'git.exe' $gitCandidates }
    if (!$git) { throw 'Git not found after installation. Reopen the terminal and retry.' }
    Invoke-Checked $git @('--version')
    Write-Host 'Git ready. Configure the knowledge repository separately; no sync schedule was changed.'
}
if ($WithBridge) {
    $nodeCandidates = @("$env:ProgramFiles/nodejs/node.exe", "$env:LOCALAPPDATA/Programs/nodejs/node.exe")
    $node = Find-Program 'node.exe' $nodeCandidates
    $nodeReady = $false
    if ($node) { & $node -e 'process.exit(Number(process.versions.node.split(''.'')[0]) >= 22 ? 0 : 1)'; $nodeReady = ($LASTEXITCODE -eq 0) }
    if (!$nodeReady) { Install-Package 'OpenJS.NodeJS.LTS'; $node = Find-Program 'node.exe' $nodeCandidates }
    if (!$node) { throw 'Node.js not found. Reopen the terminal and retry.' }
    Invoke-Checked $node @('-e', 'process.exit(Number(process.versions.node.split(''.'')[0]) >= 22 ? 0 : 1)')
    $env:PATH = (Split-Path $node) + ';' + $env:PATH
    $npm = Find-Program 'npm.cmd' @((Join-Path (Split-Path $node) 'npm.cmd'))
    if (!$npm) { throw 'npm.cmd is required. Repair the Node.js installation.' }
    $npmRoot = Join-Path $env:USERPROFILE 'AppData/Roaming/npm'
    $cli = Join-Path $npmRoot 'node_modules/@larksuite/cli/scripts/run.js'
    if (!(Test-Path -LiteralPath $cli)) { Invoke-Checked $npm @('install', '--global', '--prefix', $npmRoot, '@larksuite/cli') }
    if (!(Test-Path -LiteralPath $cli)) { throw 'The installed Lark CLI has an unsupported layout; configure the bridge cli command explicitly.' }
    Invoke-Checked $node @($cli, '--version')
    Write-Host 'Bridge tools ready. Configure the Lark profile and Codex connection separately; no accounts were changed.'
}

Invoke-Checked $venvPython @((Join-Path $taskRoot 'core/setup_state.py'), '--repository', $repoRoot, '--python', $venvPython)
$wsh = New-Object -ComObject WScript.Shell
# Code points keep shortcut names portable to Windows PowerShell 5.1 without a UTF-8 BOM.
$desktopName = -join ([char[]]@(0x672c,0x5730,0x4efb,0x52a1,0x4e2d,0x5fc3))
$startupName = 'Orbit ' + (-join ([char[]]@(0x672c,0x5730,0x670d,0x52a1)))
foreach ($item in @(
    @{Folder='Desktop'; Name=$desktopName; Args='gui'},
    @{Folder='Startup'; Name=$startupName; Args='supervise --boot'}
)) {
    $shortcut = $wsh.CreateShortcut((Join-Path ([Environment]::GetFolderPath($item.Folder)) ($item.Name + '.lnk')))
    $shortcut.TargetPath = $pythonWindow
    $shortcut.Arguments = '"' + (Join-Path $taskRoot 'orbit.py') + '" ' + $item.Args
    $shortcut.WorkingDirectory = $taskRoot
    $shortcut.Description = 'Orbit local task center'
    $shortcut.IconLocation = Join-Path $taskRoot 'assets/orbit.ico'
    if ($item.Folder -eq 'Startup') { $shortcut.WindowStyle = 7 }
    $shortcut.Save()
}
if (!$NoLaunch) {
    foreach ($mode in @('supervise', 'gui')) {
        $running = & $venvPython (Join-Path $taskRoot 'core/setup_state.py') --running $mode --repository $repoRoot
        if ($LASTEXITCODE -ne 0) { throw 'Could not inspect running Orbit processes.' }
        if ($running -eq 'yes') { Write-Host "Orbit $mode is already running; left unchanged."; continue }
        $window = if ($mode -eq 'gui') { 'Normal' } else { 'Hidden' }
        Start-Process -FilePath $pythonWindow -ArgumentList ('"' + (Join-Path $taskRoot 'orbit.py') + '" ' + $mode) -WorkingDirectory $taskRoot -WindowStyle $window
    }
}
Write-Host "Installed Orbit. Local configuration: $orbitRoot"
Write-Host 'Desktop and login startup shortcuts are ready. No example service was registered.'
