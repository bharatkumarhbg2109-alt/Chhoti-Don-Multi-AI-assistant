param([switch]$Quiet)

$ErrorActionPreference = "Continue"
$ProjectRoot = $PSScriptRoot
$RuntimeDir = Join-Path $ProjectRoot ".runtime"
$report = [System.Collections.Generic.List[string]]::new()

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

foreach ($name in @("frontend", "backend", "ollama")) {
    $pidPath = Join-Path $RuntimeDir "$name.pid"
    if (-not (Test-Path -LiteralPath $pidPath)) { $report.Add("$name`: not launcher-owned"); continue }
    $savedPid = Get-Content -LiteralPath $pidPath -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($savedPid -match '^\d+$') {
        $process = Get-Process -Id ([int]$savedPid) -ErrorAction SilentlyContinue
        if ($process) {
            $children = @(Get-Descendants $process.Id)
            [array]::Reverse($children)
            foreach ($childId in $children) { Stop-Process -Id $childId -Force -ErrorAction SilentlyContinue }
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            $report.Add("$name`: stopped PID $savedPid")
        } else { $report.Add("$name`: removed stale PID file") }
    } else { $report.Add("$name`: removed invalid PID file") }
    Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
}

$message = "CHHOTI DON stop complete.`n" + ($report -join "`n")
Add-Content -LiteralPath (Join-Path $RuntimeDir "launcher.log") -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $($message -replace "`n", '; ')" -Encoding utf8
if (-not $Quiet) { Write-Host $message }
