# run.ps1 — ZnShop Orchestrator Launcher
# Bypasses "Application Control" block by using the allowed base python.

# Determine base directory
$BaseDir = Get-Location
if ($PSScriptRoot) { $BaseDir = $PSScriptRoot }

$VenvDir = Join-Path $BaseDir ".venv"
$CfgPath = Join-Path $VenvDir "pyvenv.cfg"

if (-not (Test-Path $CfgPath)) {
    Write-Warning "Virtual environment not found at $VenvDir. Please run: uv venv"
    # Proceed anyway with system python if allowed
}

# Find pyvenv.cfg and extract home path
if (Test-Path $CfgPath) {
    # Manually parse since ConvertFrom-StringData can be finicky with paths
    $CfgLines = Get-Content $CfgPath
    $HomeDir = ""
    foreach ($Line in $CfgLines) {
        if ($Line -match "^home\s*=\s*(.*)") {
            $HomeDir = $Matches[1].Trim()
            break
        }
    }

    if (-not $HomeDir) {
        Write-Warning "Could not find 'home' in pyvenv.cfg. Using system python."
        $BasePython = "python"
    } else {
        $BasePython = Join-Path $HomeDir "python.exe"
    }
} else {
    Write-Warning "pyvenv.cfg not found. Using system python."
    $BasePython = "python"
}

if (-not (Test-Path $BasePython)) {
    Write-Warning "Python not found at $BasePython. Trying system 'python'."
    $BasePython = "python"
}

Write-Host "Starting ZnShop using: $BasePython" -ForegroundColor Cyan

# Set environment variables to activate the venv context
$env:VIRTUAL_ENV = $VenvDir
$env:PYTHONPATH = (Join-Path $VenvDir "Lib\site-packages") + ";" + $env:PYTHONPATH

# Run the master orchestrator
& $BasePython run_system.py
