param([switch]$NoLaunch)
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$pythonWindow=Join-Path (Split-Path (Get-Command python.exe).Source) 'pythonw.exe'
$orbitRoot=Join-Path $env:USERPROFILE '.orbit'
New-Item -ItemType Directory -Path $orbitRoot -Force | Out-Null
@{root=(Split-Path $taskRoot -Parent)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $orbitRoot 'installation.json') -Encoding UTF8
$registryPath=Join-Path $orbitRoot 'services.json'
if (!(Test-Path -LiteralPath $registryPath)) { '[]' | Set-Content -LiteralPath $registryPath -Encoding UTF8 }
$wsh=New-Object -ComObject WScript.Shell
$desktopLink=$wsh.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) '本地任务中心.lnk'))
$desktopLink.TargetPath=$pythonWindow
$desktopLink.Arguments='"'+(Join-Path $taskRoot 'orbit.py')+'" gui'
$desktopLink.WorkingDirectory=$taskRoot
$desktopLink.Description='Orbit · 跨项目本地任务中心'
$desktopLink.IconLocation=(Join-Path $taskRoot 'assets/orbit.ico')
$desktopLink.Save()
$startupLink=$wsh.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Startup')) 'Orbit 本地服务.lnk'))
$startupLink.TargetPath=$pythonWindow
$startupLink.Arguments='"'+(Join-Path $taskRoot 'orbit.py')+'" supervise --boot'
$startupLink.WorkingDirectory=$taskRoot
$startupLink.WindowStyle=7
$startupLink.Description='登录后启动消息桥接；不启动训练监测或远端训练'
$startupLink.Save()
if (!$NoLaunch) {
    Start-Process -FilePath $pythonWindow -ArgumentList ('"'+(Join-Path $taskRoot 'orbit.py')+'" supervise') -WorkingDirectory $taskRoot -WindowStyle Hidden
    Start-Process -FilePath $pythonWindow -ArgumentList ('"'+(Join-Path $taskRoot 'orbit.py')+'" gui') -WorkingDirectory $taskRoot -WindowStyle Normal
}
