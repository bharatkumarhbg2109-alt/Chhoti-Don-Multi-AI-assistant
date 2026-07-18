$ErrorActionPreference = "SilentlyContinue"

$Root = $PSScriptRoot
$RuntimeDir = Join-Path $Root ".runtime"

$pidFiles = @(
    (Join-Path $RuntimeDir "frontend.pid"),
    (Join-Path $RuntimeDir "backend.pid")
)

$stopped = @()

foreach ($pidFile in $pidFiles) {
    if (Test-Path $pidFile) {
        $processId = Get-Content $pidFile | Select-Object -First 1
        if ($processId -match '^\d+$') {
            $process = Get-Process -Id ([int]$processId) -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Process -Id $process.Id -Force
                $stopped += $process.Id
            }
        }
        Remove-Item $pidFile -Force
    }
}

Add-Type -AssemblyName PresentationFramework

if ($stopped.Count -gt 0) {
    [System.Windows.MessageBox]::Show(
        "CHHOTI DON has been stopped.",
        "CHHOTI DON",
        "OK",
        "Information"
    ) | Out-Null
}
else {
    [System.Windows.MessageBox]::Show(
        "No launcher-managed CHHOTI DON process was running.",
        "CHHOTI DON",
        "OK",
        "Information"
    ) | Out-Null
}
