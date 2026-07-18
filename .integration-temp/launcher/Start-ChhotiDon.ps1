$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$RuntimeDir = Join-Path $Root ".runtime"
$LogDir = Join-Path $Root "logs"

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# ---------------- USER CONFIGURATION ----------------
$BackendHost = "127.0.0.1"
$BackendPort = 8000
$FrontendHost = "127.0.0.1"
$FrontendPort = 5173

# Leave blank for auto-detection. Examples: "app:app" or "main:app"
$PreferredBackendModule = ""
# ----------------------------------------------------

function Test-TcpPort {
    param(
        [string]$HostName,
        [int]$Port
    )

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync($HostName, $Port)
        if (-not $task.Wait(500)) {
            return $false
        }
        return $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Wait-ForPort {
    param(
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-TcpPort -HostName $HostName -Port $Port) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Resolve-Python {
    $candidates = @(
        (Join-Path $Root ".venv\Scripts\python.exe"),
        (Join-Path $Root "venv\Scripts\python.exe"),
        (Join-Path $Root "env\Scripts\python.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }

    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyCommand) {
        return $pyCommand.Source
    }

    throw "Python was not found. Install Python or create a .venv/venv inside the project root."
}

function Resolve-FrontendDirectory {
    $nested = Join-Path $Root "chhoti-don-react"
    if (Test-Path (Join-Path $nested "package.json")) {
        return $nested
    }

    if (Test-Path (Join-Path $Root "package.json")) {
        return $Root
    }

    throw "Frontend package.json was not found in '$Root\chhoti-don-react' or the project root."
}

function Resolve-BackendModule {
    if ($PreferredBackendModule.Trim()) {
        return $PreferredBackendModule.Trim()
    }

    $candidates = @(
        @{ Path = (Join-Path $Root "app.py"); Module = "app:app" },
        @{ Path = (Join-Path $Root "main.py"); Module = "main:app" }
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate.Path) {
            $content = Get-Content -Raw -Path $candidate.Path -ErrorAction SilentlyContinue
            if ($content -match '(?m)^\s*app\s*=\s*FastAPI\s*\(') {
                return $candidate.Module
            }
        }
    }

    # Fallback: prefer app.py, then main.py.
    if (Test-Path (Join-Path $Root "app.py")) {
        return "app:app"
    }
    if (Test-Path (Join-Path $Root "main.py")) {
        return "main:app"
    }

    throw "Could not find app.py or main.py for the FastAPI backend."
}

function Save-Pid {
    param(
        [string]$Name,
        [int]$ProcessId
    )
    Set-Content -Path (Join-Path $RuntimeDir "$Name.pid") -Value $ProcessId -Encoding ascii
}

try {
    $Python = Resolve-Python
    $FrontendDir = Resolve-FrontendDirectory
    $BackendModule = Resolve-BackendModule
    $Npm = (Get-Command npm.cmd -ErrorAction Stop).Source

    # Install frontend dependencies only when missing.
    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        $installOut = Join-Path $LogDir "npm-install.out.log"
        $installErr = Join-Path $LogDir "npm-install.err.log"

        $install = Start-Process `
            -FilePath $Npm `
            -ArgumentList @("install") `
            -WorkingDirectory $FrontendDir `
            -PassThru `
            -Wait `
            -WindowStyle Hidden `
            -RedirectStandardOutput $installOut `
            -RedirectStandardError $installErr

        if ($install.ExitCode -ne 0) {
            throw "npm install failed. Check '$installErr'."
        }
    }

    if (-not (Test-TcpPort -HostName $BackendHost -Port $BackendPort)) {
        $backendOut = Join-Path $LogDir "backend.out.log"
        $backendErr = Join-Path $LogDir "backend.err.log"

        $backendProcess = Start-Process `
            -FilePath $Python `
            -ArgumentList @(
                "-m", "uvicorn", $BackendModule,
                "--host", $BackendHost,
                "--port", "$BackendPort"
            ) `
            -WorkingDirectory $Root `
            -PassThru `
            -WindowStyle Hidden `
            -RedirectStandardOutput $backendOut `
            -RedirectStandardError $backendErr

        Save-Pid -Name "backend" -ProcessId $backendProcess.Id
    }

    if (-not (Test-TcpPort -HostName $FrontendHost -Port $FrontendPort)) {
        $frontendOut = Join-Path $LogDir "frontend.out.log"
        $frontendErr = Join-Path $LogDir "frontend.err.log"

        $frontendProcess = Start-Process `
            -FilePath $Npm `
            -ArgumentList @(
                "run", "dev", "--",
                "--host", $FrontendHost,
                "--port", "$FrontendPort"
            ) `
            -WorkingDirectory $FrontendDir `
            -PassThru `
            -WindowStyle Hidden `
            -RedirectStandardOutput $frontendOut `
            -RedirectStandardError $frontendErr

        Save-Pid -Name "frontend" -ProcessId $frontendProcess.Id
    }

    $frontendReady = Wait-ForPort -HostName $FrontendHost -Port $FrontendPort -TimeoutSeconds 45
    if (-not $frontendReady) {
        throw "Frontend did not start within 45 seconds. Check '$LogDir\frontend.err.log'."
    }

    $frontendUrl = "http://${FrontendHost}:${FrontendPort}"
    Start-Process $frontendUrl
}
catch {
    $message = @"
CHHOTI DON could not start.

$($_.Exception.Message)

Logs folder:
$LogDir
"@
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        $message,
        "CHHOTI DON Launcher",
        "OK",
        "Error"
    ) | Out-Null
    exit 1
}
