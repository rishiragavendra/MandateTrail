param([switch]$Docker,[switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
if (!(Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
Get-Content -LiteralPath '.env' | ForEach-Object {
    if ($_ -match '^([A-Z_][A-Z0-9_]*)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim().Trim('"'), 'Process')
    }
}
New-Item -ItemType Directory -Force -Path 'logs' | Out-Null
function Native($exe, $arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $exe $arguments" }
}
function FileHash($path) {
    $stream = [System.IO.File]::OpenRead((Resolve-Path -LiteralPath $path).Path)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-','') } finally { $stream.Dispose(); $sha.Dispose() }
}
function Ready($url, $seconds=120) {
    $deadline = (Get-Date).AddSeconds($seconds)
    do {
        try { $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -eq 200) { return } } catch {}
        Start-Sleep -Milliseconds 800
    } while ((Get-Date) -lt $deadline)
    throw "Service did not become ready: $url. Inspect logs in $root\logs"
}
if ($Docker) {
    if (!(Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Install Docker Desktop and enable Linux containers.' }
    Native 'docker' @('info','--format','{{.ServerVersion}}')
    if (!(Test-Path -LiteralPath 'data')) { New-Item -ItemType Directory 'data' | Out-Null }
    if (!$env:POSTGRES_PASSWORD) {
        $bytes = New-Object byte[] 24
        [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
        $env:POSTGRES_PASSWORD = [BitConverter]::ToString($bytes).Replace('-','').ToLowerInvariant()
        Add-Content -LiteralPath '.env' -Value ("`nPOSTGRES_PASSWORD=" + $env:POSTGRES_PASSWORD)
    }
    Native 'docker' @('compose','-p','mandatetrail','up','-d','--build','--wait')
    Ready 'http://127.0.0.1:8000/api/v1/health'
    Ready 'http://localhost:3000'
    Write-Host 'Docker credentials are in data\DEMO_CREDENTIALS.txt'
} else {
    if (!(Get-Command python -ErrorAction SilentlyContinue)) { throw 'Install Python 3.11 or newer from python.org and enable Add Python to PATH.' }
    $pythonVersion = & python --version 2>&1
    if ($LASTEXITCODE -ne 0 -or $pythonVersion -notmatch 'Python (\d+)\.(\d+)' -or [int]$matches[1] -lt 3 -or ([int]$matches[1] -eq 3 -and [int]$matches[2] -lt 11)) { throw 'Install Python 3.11 or newer.' }
    if (!(Get-Command node -ErrorAction SilentlyContinue) -or !(Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw 'Install Node.js 22 LTS (includes npm) from nodejs.org.' }
    $nodeVersion = & node --version
    if ($nodeVersion -notmatch '^v(\d+)' -or [int]$matches[1] -lt 20) { throw 'Install Node.js 20 or newer (22 LTS recommended).' }
    if (Test-Path -LiteralPath 'logs\processes.json') {
        $existing = Get-Content -LiteralPath 'logs\processes.json' -Raw | ConvertFrom-Json
        if (@($existing | Where-Object { Get-Process -Id $_.pid -ErrorAction SilentlyContinue }).Count) { throw 'MandateTrail is already running. Open http://localhost:3000 or run stop.bat first.' }
    }
    foreach ($port in @(3000,8000)) {
        if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Port $port is in use. Stop the conflicting service or change the documented configuration." }
    }
    if (!(Test-Path -LiteralPath '.venv\Scripts\python.exe')) { Native 'python' @('-m','venv','.venv') }
    $python = Join-Path $root '.venv\Scripts\python.exe'
    $reqHash = FileHash 'backend\requirements.txt'
    $stamp = 'logs\requirements.sha256'
    if (!(Test-Path $stamp) -or (Get-Content $stamp -Raw).Trim() -ne $reqHash) {
        Native $python @('-m','pip','install','-r','backend\requirements.txt')
        Set-Content -LiteralPath $stamp -Value $reqHash
    }
    Push-Location -LiteralPath 'backend'
    try { Native $python @('-m','alembic','upgrade','head'); Native $python @('-c','from app.main import seed; seed()') } finally { Pop-Location }
    Push-Location -LiteralPath 'frontend'
    try {
        $lockHash = FileHash 'package-lock.json'
        if (!(Test-Path -LiteralPath 'node_modules') -or !(Test-Path -LiteralPath '..\logs\npm.sha256') -or (Get-Content -LiteralPath '..\logs\npm.sha256' -Raw).Trim() -ne $lockHash) {
            Native 'npm.cmd' @('ci','--no-fund'); Set-Content -LiteralPath '..\logs\npm.sha256' -Value $lockHash
        }
        $sourceHash = (Get-ChildItem -LiteralPath 'app','components','lib' -File -Recurse | Sort-Object FullName | ForEach-Object { FileHash $_.FullName }) -join ''
        $buildStamp = '..\logs\frontend.sha256'
        if (!(Test-Path -LiteralPath '.next\BUILD_ID') -or !(Test-Path -LiteralPath $buildStamp) -or (Get-Content -LiteralPath $buildStamp -Raw).Trim() -ne $sourceHash) {
            Native 'npm.cmd' @('run','build'); Set-Content -LiteralPath $buildStamp -Value $sourceHash
        }
    } finally { Pop-Location }
    $started = @()
    try {
        $backend = Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory (Join-Path $root 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root 'logs\backend.log') -RedirectStandardError (Join-Path $root 'logs\backend.error.log') -PassThru
        $started += @{pid=$backend.Id;started=$backend.StartTime.ToUniversalTime().ToString('o');service='backend'}
        $started | ConvertTo-Json | Set-Content -LiteralPath 'logs\processes.json'
        Ready 'http://127.0.0.1:8000/api/v1/health'
        $next = Join-Path $root 'frontend\node_modules\next\dist\bin\next'
        $frontend = Start-Process -FilePath (Get-Command node).Source -ArgumentList @(('"'+$next+'"'),'start','--hostname','127.0.0.1','--port','3000') -WorkingDirectory (Join-Path $root 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root 'logs\frontend.log') -RedirectStandardError (Join-Path $root 'logs\frontend.error.log') -PassThru
        $started += @{pid=$frontend.Id;started=$frontend.StartTime.ToUniversalTime().ToString('o');service='frontend'}
        $started | ConvertTo-Json | Set-Content -LiteralPath 'logs\processes.json'
        Ready 'http://localhost:3000'
    } catch { & (Join-Path $PSScriptRoot 'stop.ps1'); throw }
    Write-Host "Your generated login password: $root\backend\data\DEMO_CREDENTIALS.txt"
}
Write-Host "`nMandateTrail ready`nFrontend: http://localhost:3000`nBackend / API docs: http://127.0.0.1:8000/docs`nEmail: admin@mandatetrail.local`nSynthetic payments only. Use stop.bat to stop project services.`n"
if (!$NoBrowser) { Start-Process 'http://localhost:3000' }
