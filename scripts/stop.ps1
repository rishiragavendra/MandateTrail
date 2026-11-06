$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$file = Join-Path $root 'logs\processes.json'
if (Test-Path -LiteralPath $file) {
    $entries = Get-Content -LiteralPath $file -Raw | ConvertFrom-Json
    function StopOwnedTree([int]$ownedId) {
        $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ownedId" -ErrorAction SilentlyContinue
        foreach ($child in $children) { StopOwnedTree $child.ProcessId }
        Stop-Process -Id $ownedId -ErrorAction SilentlyContinue
    }
    foreach ($entry in $entries) {
        $process = Get-Process -Id $entry.pid -ErrorAction SilentlyContinue
        if ($process -and $process.StartTime.ToUniversalTime().ToString('o') -eq $entry.started) {
            StopOwnedTree $entry.pid
            Write-Host ("Stopped " + $entry.service)
        }
    }
    Remove-Item -LiteralPath $file
}
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Push-Location -LiteralPath $root
    try { docker compose -p mandatetrail stop 2>$null } catch {} finally { Pop-Location }
}
Write-Host 'MandateTrail services stopped. Persistent data retained.'
