param(
    [Parameter(Mandatory)][string]$Config,
    [ValidateSet('inspect','pull','sync','retry','session')][string]$Action
)
$ErrorActionPreference = 'Stop'
$runtime = Split-Path -Parent $Config
try {
    $settings = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json
    $worker = Join-Path $PSScriptRoot 'sync.py'
    $env:PYTHONUTF8 = '1'
    # A hidden PowerShell host supplies valid stdio handles and preserves a
    # diagnostic trail even when Python cannot start in a scheduled session.
    & $settings.python $worker $Action --config $Config > (Join-Path $runtime 'last-run.json') 2> (Join-Path $runtime 'launch-error.log')
    exit $LASTEXITCODE
} catch {
    $_ | Out-String | Set-Content -LiteralPath (Join-Path $runtime 'launch-error.log') -Encoding UTF8
    exit 1
}
