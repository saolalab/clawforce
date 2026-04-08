@echo off
REM Clawforce Installer — Windows Command Prompt launcher
REM
REM This script delegates to install.ps1 (PowerShell 5.1+).
REM Run this file as Administrator for best results.
REM
REM For WSL2 users the bash installer is recommended instead:
REM   wsl curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | wsl bash

echo.
echo  Clawforce Installer (Windows)
echo.

REM Warn if not elevated
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo  WARNING: Not running as Administrator.
    echo           Some operations ^(installing Rancher Desktop, writing to Program Files^)
    echo           may require elevation. Re-run as Administrator if you encounter errors.
    echo.
)

REM Check PowerShell is available
where powershell >nul 2>&1
if %errorLevel% neq 0 (
    echo  ERROR: PowerShell not found. Please install PowerShell 5.1 or later.
    echo         https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-windows
    pause
    exit /b 1
)

REM Delegate to install.ps1 — either run locally (if scripts\ dir present)
REM or download and execute directly from GitHub.
if exist "%~dp0install.ps1" (
    echo  Running local install.ps1 ...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
) else (
    echo  Downloading and running install.ps1 from GitHub ...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "irm https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.ps1 | iex"
)

if %errorLevel% neq 0 (
    echo.
    echo  Installation encountered an error ^(exit code %errorLevel%^).
    echo.
    echo  Troubleshooting:
    echo    1. Run as Administrator
    echo    2. Check: kubectl get pods -n clawforce
    echo    3. Logs:  kubectl logs deployment/clawforce -n clawforce
    echo.
    pause
)
