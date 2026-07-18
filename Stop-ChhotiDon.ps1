param([switch]$Quiet)

# Stops ONLY the processes owned by CHHOTI DON:
#   1. The native desktop app process ("CHHOTI DON.exe") and its process tree
#      (which includes the backend it started).
#   2. Any PID-file-tracked services (backend / frontend / ollama) recorded by
#      the dev launcher or the desktop process manager, in either the project
#      .runtime folder or the packaged per-user runtime folder.
#
# It NEVER kills every python.exe / node.exe / ollama.exe. An externally started
# Ollama (no ollama.pid owned by us) is always preserved.

$ErrorActionPreference = "Continue"
$ProjectRoot = $PSScriptRoot
$report = [System.Collections.Generic.List[string]]::new()

$runtimeDirs = @(
    (Join-Path $ProjectRoot ".runtime"),
    (Join-Path $env:APPDATA "CHHOTI DON\runtime")
)

function Get-Descendants([int]$ParentId) {
    $result = [System.Collections.Generic.List[int]]::new()
    $queue = [System.Collections.Generic.Queue[int]]::new()
    $queue.Enqueue($ParentId)
    while ($queue.Count -gt 0) {
        $current = $queue.Dequeue()
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$current" -ErrorAction SilentlyContinue | ForEach-Object {
            $result.Add([int]$_.ProcessId)
            $queue.Enqueue([int]$_.ProcessId)
        }
    }
    return $result
}

function Stop-Tree([int]$RootPid, [string]$Label) {
    $children = @(Get-Descendants $RootPid)
    [array]::Reverse($children)
    foreach ($childId in $children) { Stop-Process -Id $childId -Force -ErrorAction SilentlyContinue }
    Stop-Process -Id $RootPid -Force -ErrorAction SilentlyContinue
    $report.Add("$Label`: stopped PID $RootPid (+ $($children.Count) child processes)")
}

# 1. The desktop app itself (by executable name — unique to this app).
$app = Get-Process "CHHOTI DON" -ErrorAction SilentlyContinue
if ($app) {
    foreach ($p in $app) { Stop-Tree $p.Id "desktop-app" }
} else {
    $report.Add("desktop-app: not running")
}

# 2. PID-file-tracked services in every known runtime dir.
foreach ($RuntimeDir in $runtimeDirs) {
    if (-not (Test-Path $RuntimeDir)) { continue }
    foreach ($name in @("frontend", "backend", "ollama")) {
        $pidPath = Join-Path $RuntimeDir "$name.pid"
        if (-not (Test-Path -LiteralPath $pidPath)) { continue }
        $savedPid = Get-Content -LiteralPath $pidPath -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($savedPid -match '^\d+$') {
            $process = Get-Process -Id ([int]$savedPid) -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Tree ([int]$savedPid) $name
            } else {
                $report.Add("$name`: removed stale PID file")
            }
        } else {
            $report.Add("$name`: removed invalid PID file")
        }
        Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
    }
}

$message = "CHHOTI DON stop complete.`n" + ($report -join "`n")
foreach ($RuntimeDir in $runtimeDirs) {
    if (Test-Path $RuntimeDir) {
        Add-Content -LiteralPath (Join-Path $RuntimeDir "launcher.log") -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $($message -replace "`n", '; ')" -Encoding utf8 -ErrorAction SilentlyContinue
    }
}
if (-not $Quiet) { Write-Host $message }
