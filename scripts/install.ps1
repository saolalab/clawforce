#Requires -Version 5.1
<#
.SYNOPSIS
    Clawforce Installer for Windows

.DESCRIPTION
    Installs Docker Desktop (if needed) and runs Clawforce in a container.

.PARAMETER Port
    Port to expose (default: 8080)

.PARAMETER DataDir
    Data directory path (default: $env:USERPROFILE\.clawforce\data)

.PARAMETER AdminUser
    Admin username (default: admin)

.PARAMETER AdminPass
    Admin password (default: admin)

.PARAMETER ProcessPool
    Use process pool instead of Docker isolation

.PARAMETER SkipDockerInstall
    Skip Docker installation check

.PARAMETER Uninstall
    Remove Clawforce container and optionally data

.EXAMPLE
    # Quick install (PowerShell)
    irm https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.ps1 | iex

    # Or download and run with parameters
    .\install.ps1 -Port 9000 -AdminPass "mypassword"

.LINK
    https://github.com/saolalab/clawforce
#>

[CmdletBinding()]
param(
    [int]$Port = 8080,
    [string]$DataDir = "$env:USERPROFILE\.clawforce\data",
    [string]$AdminUser = "admin",
    [string]$AdminPass = "admin",
    [string]$Image = "ghcr.io/saolalab/clawforce:latest",
    [string]$Container = "clawforce",
    [switch]$ProcessPool,
    [switch]$SkipDockerInstall,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
function Write-Info { param($msg) Write-Host "▸ " -ForegroundColor Blue -NoNewline; Write-Host $msg }
function Write-Success { param($msg) Write-Host "✓ " -ForegroundColor Green -NoNewline; Write-Host $msg }
function Write-Warn { param($msg) Write-Host "⚠ " -ForegroundColor Yellow -NoNewline; Write-Host $msg }
function Write-Err { param($msg) Write-Host "✗ " -ForegroundColor Red -NoNewline; Write-Host $msg }

function Test-Command { param($cmd) return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function Test-DockerRunning {
    try {
        $null = docker info 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Get-DockerDesktopPath {
    $paths = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )
    foreach ($path in $paths) {
        if (Test-Path $path) { return $path }
    }
    return $null
}

# ─────────────────────────────────────────────────────────────────────────────
# Uninstall
# ─────────────────────────────────────────────────────────────────────────────
if ($Uninstall) {
    Write-Info "Uninstalling Clawforce..."
    
    # Stop and remove container
    try {
        $containerExists = docker inspect $Container 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Stopping container..."
            docker stop $Container 2>&1 | Out-Null
            docker rm $Container 2>&1 | Out-Null
            Write-Success "Container removed"
        } else {
            Write-Info "Container not found"
        }
    } catch {
        Write-Info "Container not found"
    }
    
    # Stop agent workers
    try {
        $agentContainers = docker ps -aq --filter "name=clawbot-agent-" 2>&1
        if ($agentContainers) {
            Write-Info "Stopping agent workers..."
            $agentContainers | ForEach-Object { docker rm -f $_ 2>&1 | Out-Null }
            Write-Success "Agent workers removed"
        }
    } catch {}
    
    # Ask about data
    if (Test-Path $DataDir) {
        Write-Host ""
        $response = Read-Host "Remove data directory $DataDir? [y/N]"
        if ($response -match "^[Yy]$") {
            Remove-Item -Recurse -Force $DataDir
            Write-Success "Data directory removed"
        } else {
            Write-Info "Data directory kept at $DataDir"
        }
    }
    
    Write-Success "Clawforce uninstalled"
    exit 0
}

# ─────────────────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ┌─────────────────────────────────────────────────────────────────┐" -ForegroundColor Cyan
Write-Host "  │                                                                 │" -ForegroundColor Cyan
Write-Host "  │            C L A W F O R C E   I N S T A L L E R                │" -ForegroundColor Cyan
Write-Host "  │                                                                 │" -ForegroundColor Cyan
Write-Host "  │           Autonomous AI Team Orchestration Platform             │" -ForegroundColor Cyan
Write-Host "  │                                                                 │" -ForegroundColor Cyan
Write-Host "  └─────────────────────────────────────────────────────────────────┘" -ForegroundColor Cyan
Write-Host ""

# ─────────────────────────────────────────────────────────────────────────────
# Check Windows version
# ─────────────────────────────────────────────────────────────────────────────
$osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
$winVersion = [System.Environment]::OSVersion.Version
Write-Info "Detected: Windows $($osInfo.Caption) ($($winVersion.Major).$($winVersion.Minor))"

if ($winVersion.Major -lt 10) {
    Write-Err "Windows 10 or later is required for Docker Desktop"
    exit 1
}

# ─────────────────────────────────────────────────────────────────────────────
# Check/Install Docker
# ─────────────────────────────────────────────────────────────────────────────
if (-not $SkipDockerInstall) {
    if (Test-Command "docker") {
        if (Test-DockerRunning) {
            Write-Success "Docker is installed and running"
        } else {
            Write-Warn "Docker is installed but not running"
            
            $dockerPath = Get-DockerDesktopPath
            if ($dockerPath) {
                Write-Info "Starting Docker Desktop..."
                Start-Process $dockerPath
                Write-Host ""
                Write-Warn "Please wait for Docker Desktop to start (look for the whale icon in the system tray)"
                Write-Host ""
                
                # Wait for Docker to be ready
                $maxWait = 120
                $waited = 0
                while (-not (Test-DockerRunning) -and $waited -lt $maxWait) {
                    Write-Host "." -NoNewline
                    Start-Sleep -Seconds 2
                    $waited += 2
                }
                Write-Host ""
                
                if (Test-DockerRunning) {
                    Write-Success "Docker is now running"
                } else {
                    Write-Err "Docker failed to start within $maxWait seconds"
                    Write-Host ""
                    Write-Host "  Please start Docker Desktop manually and run this script again."
                    exit 1
                }
            } else {
                Write-Err "Cannot find Docker Desktop executable"
                Write-Host ""
                Write-Host "  Please start Docker Desktop manually and run this script again."
                exit 1
            }
        }
    } else {
        Write-Warn "Docker is not installed"
        Write-Host ""
        
        # Check for winget
        if (Test-Command "winget") {
            $response = Read-Host "Install Docker Desktop via winget? [Y/n]"
            if ($response -notmatch "^[Nn]$") {
                Write-Info "Installing Docker Desktop..."
                winget install -e --id Docker.DockerDesktop --accept-source-agreements --accept-package-agreements
                
                Write-Host ""
                Write-Success "Docker Desktop installed"
                Write-Warn "Please restart your computer, then run this script again."
                Write-Host ""
                Write-Host "  After restart:"
                Write-Host "  1. Open Docker Desktop from Start Menu"
                Write-Host "  2. Complete the setup wizard"
                Write-Host "  3. Run this installer again"
                Write-Host ""
                exit 0
            }
        }
        
        # Manual installation instructions
        Write-Host ""
        Write-Err "Docker Desktop is required."
        Write-Host ""
        Write-Host "  Please install Docker Desktop from:"
        Write-Host "  https://docs.docker.com/desktop/install/windows-install/"
        Write-Host ""
        Write-Host "  After installation:"
        Write-Host "  1. Restart your computer"
        Write-Host "  2. Open Docker Desktop"
        Write-Host "  3. Run this installer again"
        Write-Host ""
        exit 1
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# Check WSL2 for Docker socket mounting
# ─────────────────────────────────────────────────────────────────────────────
if (-not $ProcessPool) {
    # Check if Docker is using WSL2 backend
    $dockerInfo = docker info --format '{{.OSType}}' 2>&1
    if ($dockerInfo -eq "linux") {
        Write-Info "Docker is using Linux containers (WSL2)"
    } else {
        Write-Warn "Docker may be using Windows containers. Linux containers are recommended."
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# Stop existing containers
# ─────────────────────────────────────────────────────────────────────────────
try {
    $containerExists = docker inspect $Container 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Info "Stopping existing Clawforce container..."
        docker stop $Container 2>&1 | Out-Null
        docker rm $Container 2>&1 | Out-Null
    }
} catch {}

# Stop orphaned agent workers
try {
    $agentContainers = docker ps -aq --filter "name=clawbot-agent-" 2>&1
    if ($agentContainers -and $LASTEXITCODE -eq 0) {
        Write-Info "Cleaning up agent workers..."
        $agentContainers | ForEach-Object { docker rm -f $_ 2>&1 | Out-Null }
    }
} catch {}

# ─────────────────────────────────────────────────────────────────────────────
# Create data directory
# ─────────────────────────────────────────────────────────────────────────────
Write-Info "Setting up data directory: $DataDir"
if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
}
$DataDir = (Resolve-Path $DataDir).Path

# Convert Windows path to Docker-compatible path
# Docker Desktop on Windows can use Windows paths directly
$DockerDataPath = $DataDir

# ─────────────────────────────────────────────────────────────────────────────
# Registry login check
# ─────────────────────────────────────────────────────────────────────────────
function Test-RegistryLogin {
    param([string]$Registry)
    $configPath = if ($env:DOCKER_CONFIG) { "$env:DOCKER_CONFIG\config.json" } else { "$env:USERPROFILE\.docker\config.json" }
    if (Test-Path $configPath) {
        $configContent = Get-Content $configPath -Raw -ErrorAction SilentlyContinue
        if ($configContent -and $configContent.Contains("`"$Registry`"")) {
            return $true
        }
    }
    return $false
}

$imageRegistry = ($Image -split '/')[0]
# Only check login for registries that contain a dot (not Docker Hub)
if ($imageRegistry -match '\.') {
    Write-Info "Checking registry authentication for $imageRegistry..."
    if (Test-RegistryLogin -Registry $imageRegistry) {
        Write-Success "Already authenticated with $imageRegistry"
    } else {
        Write-Warn "Not logged in to $imageRegistry"
        Write-Host ""
        $loginResponse = Read-Host "Log in to $imageRegistry now? [Y/n]"
        if ($loginResponse -notmatch "^[Nn]$") {
            docker login $imageRegistry
            if ($LASTEXITCODE -ne 0) {
                Write-Err "Login to $imageRegistry failed. Re-run after authenticating with: docker login $imageRegistry"
                exit 1
            }
            Write-Success "Logged in to $imageRegistry"
        } else {
            Write-Warn "Skipping login — pull may fail if the image is private."
        }
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# Pull image
# ─────────────────────────────────────────────────────────────────────────────
Write-Info "Pulling Clawforce image: $Image"
docker pull $Image
if ($LASTEXITCODE -ne 0) {
    Write-Err "Failed to pull image"
    exit 1
}
Write-Success "Image pulled"

# ─────────────────────────────────────────────────────────────────────────────
# Run container
# ─────────────────────────────────────────────────────────────────────────────
Write-Info "Starting Clawforce on port $Port..."

$runArgs = @(
    "run", "-d",
    "-p", "${Port}:8080",
    "-e", "ADMIN_SETUP_USERNAME=$AdminUser",
    "-e", "ADMIN_SETUP_PASSWORD=$AdminPass",
    "-e", "AGENT_IMAGE=$Image",
    "-v", "${DockerDataPath}:/data",
    "--name", $Container,
    "--restart", "unless-stopped"
)

if ($ProcessPool) {
    Write-Info "Using process pool (no Docker isolation for agents)"
    $runArgs += @("-e", "ADMIN_RUNTIME_BACKEND=process")
} else {
    Write-Info "Using Docker isolation for agents"
    # On Windows with Docker Desktop, use named pipe for Docker socket
    $runArgs += @("-v", "//var/run/docker.sock:/var/run/docker.sock")
    $runArgs += @("-e", "AGENT_STORAGE_HOST_PATH=$DockerDataPath")
}

$runArgs += $Image

& docker @runArgs
if ($LASTEXITCODE -ne 0) {
    Write-Err "Failed to start container"
    exit 1
}

# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────
Write-Info "Waiting for server to be ready..."
$maxAttempts = 30
for ($i = 1; $i -le $maxAttempts; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            break
        }
    } catch {}
    
    if ($i -eq $maxAttempts) {
        Write-Warn "Server not responding after 30s"
        Write-Host ""
        Write-Host "  Check logs with: docker logs $Container"
        exit 1
    }
    Start-Sleep -Seconds 1
}

# ─────────────────────────────────────────────────────────────────────────────
# Success
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Success "Clawforce is running!"
Write-Host ""
Write-Host "  ┌─────────────────────────────────────────────────────────────────┐" -ForegroundColor Green
Write-Host "  │                                                                 │" -ForegroundColor Green
Write-Host "  │   Dashboard:    http://localhost:$Port                          │" -ForegroundColor Green
Write-Host "  │   Username:     $AdminUser                                       │" -ForegroundColor Green
Write-Host "  │   Password:     $AdminPass                                       │" -ForegroundColor Green
Write-Host "  │   Data:         $DataDir                                         │" -ForegroundColor Green
Write-Host "  │                                                                 │" -ForegroundColor Green
Write-Host "  └─────────────────────────────────────────────────────────────────┘" -ForegroundColor Green
Write-Host ""
Write-Host "  Commands:"
Write-Host "    View logs:      docker logs -f $Container"
Write-Host "    Stop:           docker stop $Container"
Write-Host "    Start:          docker start $Container"
Write-Host "    Uninstall:      .\install.ps1 -Uninstall"
Write-Host ""
Write-Host "  Documentation:    https://github.com/saolalab/clawforce"
Write-Host ""

# Open browser
$openBrowser = Read-Host "Open dashboard in browser? [Y/n]"
if ($openBrowser -notmatch "^[Nn]$") {
    Start-Process "http://localhost:$Port"
}
