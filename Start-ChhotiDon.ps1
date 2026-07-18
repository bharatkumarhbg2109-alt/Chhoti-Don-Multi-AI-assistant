param(
    [switch]$NoBrowser,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$RuntimeDir = Join-Path $ProjectRoot ".runtime"
$FrontendDir = Join-Path $ProjectRoot "chhoti-don-react"
$BackendUrl = "http://127.0.0.1:8000/api/health"
$FrontendUrl = "http://127.0.0.1:5173"
$OllamaUrl = "http://127.0.0.1:11434/api/tags"
$RequiredModel = if ($env:CHHOTI_DON_OLLAMA_MODEL) { $env:CHHOTI_DON_OLLAMA_MODEL } else { "mistral:latest" }

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
$LauncherLog = Join-Path $RuntimeDir "launcher.log"

function Write-LauncherLog([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -LiteralPath $LauncherLog -Value $line -Encoding utf8
    if (-not $Quiet) { Write-Host $line }
}

function Test-Url([string]$Url, [int]$TimeoutSeconds = 3) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSeconds
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 400
    } catch { return $false }
}

function Wait-Url([string]$Url, [int]$TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Url $Url) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Get-OwnedProcess([string]$Name) {
    $pidPath = Join-Path $RuntimeDir "$Name.pid"
    if (-not (Test-Path -LiteralPath $pidPath)) { return $null }
    $savedPid = (Get-Content -LiteralPath $pidPath -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($savedPid -notmatch '^\d+$') {
        Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
        return $null
    }
    $process = Get-Process -Id ([int]$savedPid) -ErrorAction SilentlyContinue
    if (-not $process) { Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue }
    return $process
}

function Save-OwnedPid([string]$Name, [int]$ProcessId) {
    Set-Content -LiteralPath (Join-Path $RuntimeDir "$Name.pid") -Value $ProcessId -Encoding ascii
}

function Resolve-Python {
    foreach ($candidate in @(".venv\Scripts\python.exe", "venv\Scripts\python.exe", "env\Scripts\python.exe")) {
        $full = Join-Path $ProjectRoot $candidate
        if (Test-Path -LiteralPath $full) { return $full }
    }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) { return $python.Source }
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) { return $py.Source }
    throw "Python was not found. Install Python or add a virtual environment to the project."
}

function Start-LoggedProcess([string]$FilePath, [string[]]$Arguments, [string]$WorkingDirectory, [string]$LogName) {
    $stdout = Join-Path $RuntimeDir "$LogName.log"
    $stderr = Join-Path $RuntimeDir "$LogName.error.log"
    return Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
}

try {
    Write-LauncherLog "Starting CHHOTI DON from $ProjectRoot"

    # Ollama is optional at runtime, but always attempted before the backend.
    if (-not (Test-Url $OllamaUrl)) {
        $ollamaCommand = Get-Command ollama.exe -ErrorAction SilentlyContinue
        if ($ollamaCommand) {
            if (-not (Get-OwnedProcess "ollama")) {
                Write-LauncherLog "Ollama is offline; starting ollama serve."
                $ollamaProcess = Start-LoggedProcess $ollamaCommand.Source @("serve") $ProjectRoot "ollama"
                Save-OwnedPid "ollama" $ollamaProcess.Id
            }
            if (-not (Wait-Url $OllamaUrl 20)) {
                Write-LauncherLog "Ollama did not become ready. Backend will remain available in simulated mode."
            }
        } else {
            Write-LauncherLog "Ollama is not installed. Backend will remain available in simulated mode."
        }
    } else {
        Write-LauncherLog "Using an existing Ollama server (not launcher-owned)."
    }

    if (Test-Url $OllamaUrl) {
        $tags = Invoke-RestMethod -Uri $OllamaUrl -TimeoutSec 5
        $available = @($tags.models | ForEach-Object { $_.name })
        $requiredBase = ($RequiredModel -split ':')[0]
        $modelFound = @($available | Where-Object { $_ -eq $RequiredModel -or ($_ -split ':')[0] -eq $requiredBase }).Count -gt 0
        if ($modelFound) {
            Write-LauncherLog "Configured Ollama model is installed: $RequiredModel"
        } else {
            Write-LauncherLog "Configured model is missing. Install it explicitly with: ollama pull $RequiredModel"
        }
    }

    $python = Resolve-Python
    if (-not (Test-Url $BackendUrl)) {
        if (Get-OwnedProcess "backend") { throw "The tracked backend process is running but its health endpoint is unavailable." }
        $backend = Start-LoggedProcess $python @("app.py") $ProjectRoot "backend"
        Save-OwnedPid "backend" $backend.Id
        Write-LauncherLog "Started backend (PID $($backend.Id))."
    } else { Write-LauncherLog "Using an existing healthy backend (not launcher-owned)." }
    if (-not (Wait-Url $BackendUrl 60)) { throw "Backend health check failed. See .runtime\backend.error.log." }

    if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "package.json"))) { throw "React frontend package.json was not found." }
    $npm = (Get-Command npm.cmd -ErrorAction Stop).Source
    if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules"))) {
        Write-LauncherLog "Installing missing frontend dependencies."
        $install = Start-Process -FilePath $npm -ArgumentList @("install") -WorkingDirectory $FrontendDir -Wait -PassThru -WindowStyle Hidden
        if ($install.ExitCode -ne 0) { throw "npm install failed with exit code $($install.ExitCode)." }
    }
    if (-not (Test-Url $FrontendUrl)) {
        if (Get-OwnedProcess "frontend") { throw "The tracked frontend process is running but its URL is unavailable." }
        $frontend = Start-LoggedProcess $npm @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173") $FrontendDir "frontend"
        Save-OwnedPid "frontend" $frontend.Id
        Write-LauncherLog "Started frontend (PID $($frontend.Id))."
    } else { Write-LauncherLog "Using an existing frontend (not launcher-owned)." }
    if (-not (Wait-Url $FrontendUrl 60)) { throw "Frontend readiness check failed. See .runtime\frontend.error.log." }

    Write-LauncherLog "All services are ready."
    if (-not $NoBrowser) { Start-Process $FrontendUrl }
    exit 0
} catch {
    Write-LauncherLog "STARTUP FAILED: $($_.Exception.Message)"
    if (-not $Quiet) { Write-Error "CHHOTI DON could not start. $($_.Exception.Message) Logs: $RuntimeDir" }
    exit 1
}
