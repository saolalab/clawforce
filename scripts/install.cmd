@echo off
REM Clawforce Installer - Windows Command Prompt wrapper
REM This script launches the PowerShell installer

echo.
echo Clawforce Installer
echo.
echo Launching PowerShell installer...
echo.

REM Check if running as admin (recommended for Docker)
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo WARNING: Not running as Administrator. Docker operations may require admin rights.
    echo.
)

REM Launch PowerShell with execution policy bypass for this script
powershell -ExecutionPolicy Bypass -Command "& { irm https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.ps1 | iex }"

if %errorLevel% neq 0 (
    echo.
    echo If PowerShell download failed, you can run manually:
    echo   1. Open PowerShell as Administrator
    echo   2. Run: irm https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.ps1 ^| iex
    echo.
    pause
)
