#Requires -Version 5.1
<#
.SYNOPSIS
    Clawforce Installer for Windows (native PowerShell)

.DESCRIPTION
    Installs k3s on Windows via Rancher Desktop or k3d, then deploys
    Clawforce as a Kubernetes workload.

    For WSL2 users, the bash installer is recommended instead:
        wsl curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | wsl bash

.PARAMETER Port
    NodePort to expose (default: 30080)

.PARAMETER Data
    Host data directory (default: %LOCALAPPDATA%\clawforce-data)

.PARAMETER AdminUser
    Admin username (default: admin)

.PARAMETER AdminPass
    Admin password (default: admin)

.PARAMETER Namespace
    Kubernetes namespace (default: clawforce)

.PARAMETER Image
    Container image (default: ghcr.io/saolalab/clawforce:latest)

.PARAMETER ProcessRuntime
    Use process runtime instead of k8s pod isolation

.PARAMETER SkipK3s
    Skip k3s / kubectl installation check

.PARAMETER Uninstall
    Remove Clawforce deployment and optionally data

.EXAMPLE
    # Quick install (run in elevated PowerShell)
    irm https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.ps1 | iex

.EXAMPLE
    # Custom port and password
    & .\scripts\install.ps1 -Port 30090 -AdminPass "s3cr3t"

.NOTES
    Run in an elevated (Administrator) PowerShell for best results.
    k3s on Windows requires one of:
      - Rancher Desktop  https://rancherdesktop.io  (recommended, installs automatically)
      - k3d              https://k3d.io              (requires Docker Desktop)
      - WSL2 + bash installer (the bash script runs natively in WSL2)
#>

[CmdletBinding()]
param(
    [int]    $Port         = $(if ($env:CLAWFORCE_PORT)       { [int]$env:CLAWFORCE_PORT }  else { 30080 }),
    [string] $Data         = $(if ($env:CLAWFORCE_DATA)       { $env:CLAWFORCE_DATA }        else { Join-Path $env:LOCALAPPDATA 'clawforce-data' }),
    [string] $AdminUser    = $(if ($env:CLAWFORCE_ADMIN_USER) { $env:CLAWFORCE_ADMIN_USER }  else { 'admin' }),
    [string] $AdminPass    = $(if ($env:CLAWFORCE_ADMIN_PASS) { $env:CLAWFORCE_ADMIN_PASS }  else { 'admin' }),
    [string] $Namespace    = $(if ($env:CLAWFORCE_NAMESPACE)  { $env:CLAWFORCE_NAMESPACE }   else { 'clawforce' }),
    [string] $Image        = $(if ($env:CLAWFORCE_IMAGE)      { $env:CLAWFORCE_IMAGE }        else { 'ghcr.io/saolalab/clawforce:latest' }),
    [switch] $ProcessRuntime,
    [switch] $SkipK3s,
    [switch] $Uninstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
function Write-Info  { param($Msg) Write-Host "  [>] $Msg" -ForegroundColor Cyan }
function Write-Ok    { param($Msg) Write-Host "  [+] $Msg" -ForegroundColor Green }
function Write-Warn  { param($Msg) Write-Host "  [!] $Msg" -ForegroundColor Yellow }
function Write-Err   { param($Msg) Write-Host "  [x] $Msg" -ForegroundColor Red }
function Fail        { param($Msg) Write-Err $Msg; exit 1 }

function Command-Exists {
    param([string]$Cmd)
    $null -ne (Get-Command $Cmd -ErrorAction SilentlyContinue)
}

function Kubectl {
    param([string[]]$KArgs)
    if (Command-Exists 'kubectl') {
        & kubectl @KArgs
        return $LASTEXITCODE
    }
    Fail "kubectl not found in PATH. Install Rancher Desktop or k3d first."
}

function Get-KubectlOutput {
    param([string[]]$KArgs)
    if (Command-Exists 'kubectl') {
        return (& kubectl @KArgs 2>$null)
    }
    return $null
}

function Test-ClusterReachable {
    if (-not (Command-Exists 'kubectl')) { return $false }
    try {
        $null = & kubectl cluster-info 2>&1
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Invoke-Download {
    param([string]$Url, [string]$Dest)
    Write-Info "Downloading $(Split-Path $Url -Leaf)..."
    $ProgressPreference = 'SilentlyContinue'   # much faster on PS 5.1
    Invoke-WebRequest -Uri $Url -OutFile $Dest -UseBasicParsing
}

function Invoke-Apply {
    param([string]$Yaml)
    $tmp = Join-Path $env:TEMP "clawforce-manifest-$(Get-Random).yaml"
    $Yaml | Set-Content -Path $tmp -Encoding UTF8
    Kubectl @('apply', '-f', $tmp) | Out-Null
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
}

# ─────────────────────────────────────────────────────────────────────────────
# Uninstall
# ─────────────────────────────────────────────────────────────────────────────
if ($Uninstall) {
    Write-Info "Uninstalling Clawforce..."

    if (Test-ClusterReachable) {
        foreach ($res in @("deployment/clawforce","service/clawforce","serviceaccount/clawforce")) {
            Kubectl @('delete', $res, '-n', $Namespace, '--ignore-not-found') | Out-Null
        }
        Kubectl @('delete','pods','-l','app=clawbot-agent',     '-n',$Namespace,'--ignore-not-found','--grace-period=0') | Out-Null
        Kubectl @('delete','pods','-l','app=clawforce-oauth-cb','-n',$Namespace,'--ignore-not-found','--grace-period=0') | Out-Null
        Kubectl @('delete','clusterrolebinding','clawforce-pod-manager','--ignore-not-found') | Out-Null
        Kubectl @('delete','clusterrole',       'clawforce-pod-manager','--ignore-not-found') | Out-Null
        Kubectl @('delete','namespace',$Namespace,'--ignore-not-found') | Out-Null
        Write-Ok "Kubernetes resources removed"
    } else {
        Write-Warn "No cluster reachable — skipping resource deletion."
    }

    if (Test-Path $Data) {
        $answer = Read-Host "Remove data directory '$Data'? [y/N]"
        if ($answer -match '^[Yy]$') {
            Remove-Item -Recurse -Force $Data
            Write-Ok "Data directory removed"
        } else {
            Write-Info "Data directory kept at $Data"
        }
    }

    Write-Ok "Clawforce uninstalled"
    exit 0
}

# ─────────────────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  +------------------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |                                                      |" -ForegroundColor Cyan
Write-Host "  |   - CLAWFORCE -                                      |" -ForegroundColor Cyan
Write-Host "  |   Autonomous AI Team Orchestration Platform          |" -ForegroundColor Cyan
Write-Host "  |   Powered by k3s (Kubernetes)  [Windows installer]  |" -ForegroundColor Cyan
Write-Host "  |                                                      |" -ForegroundColor Cyan
Write-Host "  +------------------------------------------------------+" -ForegroundColor Cyan
Write-Host ""
Write-Info "OS: Windows  Arch: $($env:PROCESSOR_ARCHITECTURE)"

# ─────────────────────────────────────────────────────────────────────────────
# k3s installation helpers
# ─────────────────────────────────────────────────────────────────────────────

function Install-ViaRancherDesktop {
    <#
    .SYNOPSIS
        Downloads and launches the Rancher Desktop installer, then waits for kubectl.
    #>
    Write-Info "Downloading Rancher Desktop..."

    # Resolve latest release from GitHub
    $arch = $env:PROCESSOR_ARCHITECTURE
    $rdArch = if ($arch -eq 'ARM64') { 'aarch64' } else { 'x86_64' }
    $rdTag  = 'latest'
    try {
        $rel  = Invoke-RestMethod -Uri 'https://api.github.com/repos/rancher-sandbox/rancher-desktop/releases/latest' -UseBasicParsing
        $rdTag = $rel.tag_name
    } catch {
        Write-Warn "Could not fetch latest Rancher Desktop tag — trying 'latest' redirect."
    }

    $installerName = "Rancher.Desktop.Setup.$rdTag.$rdArch.exe"
    $installerUrl  = "https://github.com/rancher-sandbox/rancher-desktop/releases/download/$rdTag/$installerName"
    $installerPath = Join-Path $env:TEMP $installerName

    Invoke-Download $installerUrl $installerPath

    Write-Info "Launching Rancher Desktop installer (follow the prompts)..."
    Start-Process -FilePath $installerPath -ArgumentList '/S' -Wait   # /S for silent if supported

    Write-Host ""
    Write-Warn "Rancher Desktop has been installed."
    Write-Warn "Please:"
    Write-Host "  1. Open Rancher Desktop from the Start Menu."
    Write-Host "  2. Wait for the k3s VM to finish starting (status bar turns green)."
    Write-Host "  3. Re-run this installer:"
    Write-Host "       irm https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.ps1 | iex"
    Write-Host ""
    exit 0
}

function Install-ViaK3d {
    <#
    .SYNOPSIS
        Installs k3d (requires Docker Desktop or compatible runtime) and creates a cluster.
    #>
    # Verify Docker is running
    if (-not (Command-Exists 'docker')) {
        Write-Host ""
        Write-Err "Docker not found. k3d requires Docker Desktop (or another compatible runtime)."
        Write-Host ""
        Write-Host "  Install Docker Desktop: https://docs.docker.com/desktop/install/windows-install/"
        Write-Host ""
        Fail "Install Docker Desktop then re-run this script."
    }
    try {
        $null = & docker info 2>&1
        if ($LASTEXITCODE -ne 0) { throw }
    } catch {
        Fail "Docker is installed but not running. Start Docker Desktop and try again."
    }

    # Install k3d
    if (-not (Command-Exists 'k3d')) {
        Write-Info "Installing k3d..."
        if (Command-Exists 'winget') {
            & winget install k3d.k3d --accept-source-agreements --accept-package-agreements
        } elseif (Command-Exists 'choco') {
            & choco install k3d -y
        } else {
            $k3dUrl  = 'https://github.com/k3d-io/k3d/releases/latest/download/k3d-windows-amd64.exe'
            $k3dDest = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\k3d.exe'
            Invoke-Download $k3dUrl $k3dDest
            $env:PATH = "$env:PATH;$(Split-Path $k3dDest)"
        }
        if (-not (Command-Exists 'k3d')) {
            Fail "k3d install failed. Restart your terminal and re-run this script."
        }
        Write-Ok "k3d installed"
    } else {
        Write-Ok "k3d already installed"
    }

    # Create or reuse the cluster
    $clusters = & k3d cluster list 2>$null
    if ($clusters -match 'clawforce') {
        Write-Info "k3d cluster 'clawforce' already exists — reusing it"
        & k3d cluster start clawforce 2>$null
    } else {
        Write-Info "Creating k3d cluster 'clawforce' (port $Port -> 30080)..."
        & k3d cluster create clawforce `
            --port "${Port}:30080@loadbalancer" `
            --agents 1
        Write-Ok "k3d cluster created"
    }

    & k3d kubeconfig merge clawforce --kubeconfig-merge-default --kubeconfig-switch-context 2>$null
    Write-Ok "kubeconfig updated (context: k3d-clawforce)"
    Write-Warn "Access Clawforce at http://localhost:${Port} via k3d load-balancer"
}

function Guide-Wsl2 {
    Write-Host ""
    Write-Info "Run the bash installer inside WSL2:"
    Write-Host ""
    Write-Host "  wsl curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | wsl bash"
    Write-Host ""
    Write-Host "  (If WSL2 is not installed:  winget install Microsoft.WSL)"
    Write-Host ""
    exit 0
}

# ─────────────────────────────────────────────────────────────────────────────
# Main k3s / kubectl check
# ─────────────────────────────────────────────────────────────────────────────
function Check-And-Install-K3s {
    if ($SkipK3s) {
        Write-Info "Skipping k3s check (-SkipK3s)"
        return
    }

    if (Test-ClusterReachable) {
        Write-Ok "k8s cluster is reachable — skipping installation"
        return
    }

    Write-Host ""
    Write-Host "  No accessible k8s cluster found." -ForegroundColor Yellow
    Write-Host "  How would you like to install k3s?" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  [1] Rancher Desktop  (recommended) — GUI app with built-in k3s VM + kubectl"
    Write-Host "  [2] k3d              — k3s inside Docker (requires Docker Desktop)"
    Write-Host "  [3] WSL2             — run bash installer inside Windows Subsystem for Linux"
    Write-Host ""
    $choice = Read-Host "  Your choice [1/2/3] (default: 1)"
    $choice = if ($choice) { $choice.Trim() } else { '1' }

    switch ($choice) {
        '1' { Install-ViaRancherDesktop }
        '2' { Install-ViaK3d }
        '3' { Guide-Wsl2 }
        default { Fail "Invalid choice '$choice'." }
    }

    if (-not (Test-ClusterReachable)) {
        Fail "k8s cluster still not reachable. Check Rancher Desktop or k3d status."
    }
}

Check-And-Install-K3s

# ─────────────────────────────────────────────────────────────────────────────
# Data directory
# ─────────────────────────────────────────────────────────────────────────────
Write-Info "Setting up data directory: $Data"
New-Item -ItemType Directory -Force -Path $Data | Out-Null

# ─────────────────────────────────────────────────────────────────────────────
# Apply Kubernetes manifests
# ─────────────────────────────────────────────────────────────────────────────
$RuntimeBackend = if ($ProcessRuntime) { 'process' } else { 'k8s' }
Write-Info "Runtime backend: $RuntimeBackend"

# Convert Windows backslashes to forward slashes for k8s hostPath
$DataFwd = $Data -replace '\\', '/'

Write-Info "Applying namespace and RBAC..."
Invoke-Apply @"
apiVersion: v1
kind: Namespace
metadata:
  name: $Namespace
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: clawforce
  namespace: $Namespace
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: clawforce-pod-manager
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log", "pods/exec", "namespaces"]
    verbs: ["create", "delete", "get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: clawforce-pod-manager
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: clawforce-pod-manager
subjects:
  - kind: ServiceAccount
    name: clawforce
    namespace: $Namespace
"@
Write-Ok "Namespace and RBAC configured"

Write-Info "Deploying Clawforce..."
Invoke-Apply @"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: clawforce
  namespace: $Namespace
spec:
  replicas: 1
  selector:
    matchLabels:
      app: clawforce
  template:
    metadata:
      labels:
        app: clawforce
    spec:
      serviceAccountName: clawforce
      containers:
        - name: clawforce
          image: $Image
          imagePullPolicy: Always
          ports:
            - containerPort: 8080
          env:
            - name: ADMIN_RUNTIME_BACKEND
              value: "$RuntimeBackend"
            - name: K8S_NAMESPACE
              value: "$Namespace"
            - name: ADMIN_STORAGE_ROOT
              value: "/data"
            - name: ADMIN_PUBLIC_URL
              value: "http://clawforce.$Namespace.svc.cluster.local:8080"
            - name: AGENT_STORAGE_HOST_PATH
              value: "$DataFwd"
            - name: AGENT_IMAGE
              value: "$Image"
            - name: ADMIN_SETUP_USERNAME
              value: "$AdminUser"
            - name: ADMIN_SETUP_PASSWORD
              value: "$AdminPass"
          volumeMounts:
            - name: data
              mountPath: /data
          livenessProbe:
            httpGet:
              path: /api/health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 30
            timeoutSeconds: 5
          readinessProbe:
            httpGet:
              path: /api/health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 3
      volumes:
        - name: data
          hostPath:
            path: "$DataFwd"
            type: DirectoryOrCreate
---
apiVersion: v1
kind: Service
metadata:
  name: clawforce
  namespace: $Namespace
spec:
  selector:
    app: clawforce
  ports:
    - name: http
      port: 8080
      targetPort: 8080
      nodePort: $Port
  type: NodePort
"@
Write-Ok "Deployment and Service applied"

# ─────────────────────────────────────────────────────────────────────────────
# Install PowerShell CLI wrapper
# ─────────────────────────────────────────────────────────────────────────────
function Install-CliWrapper {
    $WrapperDir  = Join-Path $env:LOCALAPPDATA 'Programs\clawforce\bin'
    New-Item -ItemType Directory -Force -Path $WrapperDir | Out-Null

    # .ps1 wrapper
    $Ps1Path = Join-Path $WrapperDir 'clawforce.ps1'
    @'
#Requires -Version 5.1
param([Parameter(Position=0)][string]$Command = '')
$NS = if ($env:CLAWFORCE_NAMESPACE) { $env:CLAWFORCE_NAMESPACE } else { 'clawforce' }
function KCmd { & kubectl @args }
switch ($Command) {
    'start'   { KCmd scale deployment/clawforce --replicas=1 -n $NS }
    'stop'    { KCmd scale deployment/clawforce --replicas=0 -n $NS }
    'restart' { KCmd rollout restart deployment/clawforce -n $NS; KCmd rollout status deployment/clawforce -n $NS --timeout=60s }
    'update'  {
        $img = (KCmd get deployment/clawforce -n $NS -o "jsonpath={.spec.template.spec.containers[0].image}")
        Write-Host "Pulling $img ..."
        KCmd rollout restart deployment/clawforce -n $NS
        KCmd rollout status  deployment/clawforce -n $NS --timeout=120s
        $np = (KCmd get service/clawforce -n $NS -o "jsonpath={.spec.ports[0].nodePort}")
        Write-Host "Updated. Running at http://localhost:$np"
    }
    'logs'    { KCmd logs -f deployment/clawforce -n $NS }
    'status'  {
        Write-Host "`n=== Clawforce pod ===" -ForegroundColor Cyan
        KCmd get pods -n $NS -l app=clawforce
        Write-Host "`n=== Agent pods ===" -ForegroundColor Cyan
        KCmd get pods -n $NS -l app=clawbot-agent 2>$null
    }
    'shell'   {
        $pod = (KCmd get pods -n $NS -l app=clawforce -o "jsonpath={.items[0].metadata.name}")
        if (-not $pod) { Write-Error "No Clawforce pod found"; exit 1 }
        KCmd exec -it $pod -n $NS -- /bin/bash
    }
    default   {
        Write-Host "Usage: clawforce <command>"
        Write-Host "Commands: start | stop | restart | update | logs | status | shell"
    }
}
'@ | Set-Content -Path $Ps1Path -Encoding UTF8

    # .cmd shim so 'clawforce' works from cmd.exe and plain PowerShell without .ps1 extension
    $CmdPath = Join-Path $WrapperDir 'clawforce.cmd'
    @"
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0clawforce.ps1" %*
"@ | Set-Content -Path $CmdPath -Encoding ASCII

    Write-Ok "CLI wrapper installed at $WrapperDir"

    # Add to user PATH
    $UserPath = [System.Environment]::GetEnvironmentVariable('PATH', 'User')
    if ($UserPath -notlike "*$WrapperDir*") {
        [System.Environment]::SetEnvironmentVariable('PATH', "$UserPath;$WrapperDir", 'User')
        $env:PATH = "$env:PATH;$WrapperDir"
        Write-Ok "Added $WrapperDir to user PATH"
        Write-Warn "Restart your terminal for 'clawforce' to be available."
    }
}

Install-CliWrapper

# ─────────────────────────────────────────────────────────────────────────────
# Wait for deployment
# ─────────────────────────────────────────────────────────────────────────────
Write-Info "Waiting for Clawforce to be ready (up to 120s)..."
try {
    Kubectl @('rollout','status','deployment/clawforce','-n',$Namespace,'--timeout=120s') | Out-Null
    Write-Ok "Deployment is ready"
} catch {
    Write-Warn "Rollout not complete — check: kubectl logs deployment/clawforce -n $Namespace"
}

# Health check
$ready = $false
$ProgressPreference = 'SilentlyContinue'
for ($i = 1; $i -le 30; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:${Port}/api/health" `
            -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep 1
}
if (-not $ready) {
    Write-Warn "Server not responding on port $Port after 30s"
    Write-Host "  Check: kubectl logs deployment/clawforce -n $Namespace"
}

# ─────────────────────────────────────────────────────────────────────────────
# Success
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Ok "Clawforce is running!"
Write-Host ""
Write-Host "  +------------------------------------------------------------------+" -ForegroundColor Green
Write-Host "  |                                                                  |" -ForegroundColor Green
Write-Host ("  |   Dashboard:  http://localhost:{0,-5}                            |" -f $Port)           -ForegroundColor Green
Write-Host ("  |   Username:   {0,-50}|" -f $AdminUser)     -ForegroundColor Green
Write-Host ("  |   Password:   {0,-50}|" -f $AdminPass)     -ForegroundColor Green
Write-Host ("  |   Data:       {0,-50}|" -f $Data)          -ForegroundColor Green
Write-Host ("  |   Namespace:  {0,-50}|" -f $Namespace)     -ForegroundColor Green
Write-Host "  |                                                                  |" -ForegroundColor Green
Write-Host "  +------------------------------------------------------------------+" -ForegroundColor Green

if ($AdminPass -eq 'admin') {
    Write-Host ""
    Write-Warn "Default password 'admin' in use — change it after first login."
}
Write-Host ""
Write-Host "  Commands (restart terminal first if 'clawforce' is not found):"
Write-Host "    clawforce logs     -- stream pod logs"
Write-Host "    clawforce stop     -- scale to 0 replicas"
Write-Host "    clawforce start    -- scale to 1 replica"
Write-Host "    clawforce status   -- show pod status"
Write-Host "    clawforce update   -- pull latest image and restart"
Write-Host ""
Write-Host "  Uninstall:"
Write-Host "    irm https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.ps1 | iex"
Write-Host "    # Then add -Uninstall flag in the script (save locally first)"
Write-Host ""
Write-Host "  kubectl shortcuts:"
Write-Host "    kubectl get pods -n $Namespace"
Write-Host "    kubectl logs -f deployment/clawforce -n $Namespace"
Write-Host ""
Write-Host "  Documentation: https://github.com/saolalab/clawforce"
Write-Host ""
