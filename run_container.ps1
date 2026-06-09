#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build the Docker image from new.Dockerfile and run the Gyroid Optimizer gRPC server.

.DESCRIPTION
    1. Builds the image tagged 'gyroid-optimizer'.
    2. Removes any existing container with the same name.
    3. Starts the container with port 50051 mapped to the host so that client.py can connect.

.PARAMETER ImageTag
    Docker image tag to build/use. Default: gyroid-optimizer

.PARAMETER ContainerName
    Name for the running container. Default: gyroid-optimizer

.PARAMETER GrpcPort
    Host port to expose the gRPC server on. Default: 50051

.PARAMETER CodeServerPort
    Host port to expose code-server (browser VS Code) on. Default: 8080
    Set to 0 to skip exposing this port.

.PARAMETER NoBuild
    Skip the build step and only (re)start the container from an existing image.

.PARAMETER Detach
    Run the container in the background. Default: $true

.PARAMETER Help
    Print a full explanation of the script and exit.

.EXAMPLE
    .\run_container.ps1
    .\run_container.ps1 -Help
    .\run_container.ps1 -NoBuild
    .\run_container.ps1 -GrpcPort 50052
#>

param(
    [string] $ImageTag       = "gyroid-optimizer",
    [string] $ContainerName  = "gyroid-optimizer",
    [int]    $GrpcPort       = 50051,
    [int]    $CodeServerPort = 8080,
    [switch] $NoBuild,
    [bool]   $Detach         = $true,
    [switch] $Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── help ─────────────────────────────────────────────────────────────────────
if ($Help) {
    Write-Host ""
    Write-Host "GYROID OPTIMIZER - Docker launcher" -ForegroundColor Cyan
    Write-Host "===================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "This script builds the Docker image defined in new.Dockerfile and starts it"
    Write-Host "as a container running the Gyroid Optimizer gRPC server on port 50051,"
    Write-Host "ready to accept connections from client.py."
    Write-Host ""
    Write-Host "WHAT IT DOES (in order)" -ForegroundColor Yellow
    Write-Host "  1. Verifies Docker is installed and its daemon is running."
    Write-Host "  2. Builds the image from new.Dockerfile (skip with -NoBuild)."
    Write-Host "  3. Removes any stale container with the same name so re-runs never fail."
    Write-Host "  4. Starts the container, activates the OFTPMSoptimiser conda environment"
    Write-Host "     inside it, and launches grpc_server/server.py --port 50051 from the"
    Write-Host "     MTO repository that was cloned during the image build."
    Write-Host ""
    Write-Host "USAGE" -ForegroundColor Yellow
    Write-Host "  .\run_container.ps1 [options]"
    Write-Host ""
    Write-Host "OPTIONS" -ForegroundColor Yellow
    Write-Host "  -ImageTag       <string>   Docker image tag to build/use."
    Write-Host "                             Default: gyroid-optimizer"
    Write-Host ""
    Write-Host "  -ContainerName  <string>   Name assigned to the running container."
    Write-Host "                             Default: gyroid-optimizer"
    Write-Host ""
    Write-Host "  -GrpcPort       <int>      Host port forwarded to the gRPC server"
    Write-Host "                             (50051 inside the container)."
    Write-Host "                             Default: 50051"
    Write-Host ""
    Write-Host "  -CodeServerPort <int>      Host port forwarded to browser VS Code"
    Write-Host "                             (code-server, port 8080 inside container)."
    Write-Host "                             Set to 0 to disable. Default: 8080"
    Write-Host ""
    Write-Host "  -NoBuild                   Skip the image build step."
    Write-Host ""
    Write-Host "  -Detach         <bool>     Run in the background (`$true) or foreground"
    Write-Host "                             (`$false). Default: `$true"
    Write-Host ""
    Write-Host "  -Help                      Print this help text and exit."
    Write-Host ""
    Write-Host "EXAMPLES" -ForegroundColor Yellow
    Write-Host "  # First run - build image and start container"
    Write-Host "  .\run_container.ps1"
    Write-Host ""
    Write-Host "  # Restart without rebuilding"
    Write-Host "  .\run_container.ps1 -NoBuild"
    Write-Host ""
    Write-Host "  # Use a different host port for gRPC"
    Write-Host "  .\run_container.ps1 -GrpcPort 50052"
    Write-Host ""
    Write-Host "  # Run in the foreground to watch server logs directly"
    Write-Host "  .\run_container.ps1 -Detach `$false"
    Write-Host ""
    Write-Host "CONNECTING WITH client.py" -ForegroundColor Yellow
    Write-Host "  python client.py --host localhost --port 50051 status"
    Write-Host "  python client.py --host localhost --port 50051 stream"
    Write-Host ""
    Write-Host "USEFUL DOCKER COMMANDS AFTER START" -ForegroundColor Yellow
    Write-Host "  docker logs -f $ContainerName        # tail live server output"
    Write-Host "  docker exec -it $ContainerName bash   # open a shell in the container"
    Write-Host "  docker stop $ContainerName            # stop the container"
    Write-Host ""
    exit 0
}

$ScriptDir  = $PSScriptRoot
$Dockerfile = Join-Path $ScriptDir "new.Dockerfile"

# ── helpers ───────────────────────────────────────────────────────────────────
function Write-Step([string]$msg) { Write-Host "" ; Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-OK  ([string]$msg) { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "    $msg" -ForegroundColor Yellow }

# ── pre-flight ───────────────────────────────────────────────────────────────
Write-Step "Checking prerequisites"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not on PATH. Install Docker Desktop and try again."
}

docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker daemon is not running. Start Docker Desktop and try again."
}
Write-OK "Docker is available."

if (-not (Test-Path $Dockerfile)) {
    throw "Dockerfile not found at: $Dockerfile"
}

# ── build ─────────────────────────────────────────────────────────────────────
if (-not $NoBuild) {
    Write-Step "Building image '$ImageTag' from new.Dockerfile"
    docker build --file "$Dockerfile" --tag "$ImageTag" "$ScriptDir"
    if ($LASTEXITCODE -ne 0) { throw "docker build failed (exit $LASTEXITCODE)." }
    Write-OK "Image built successfully."
} else {
    Write-Warn "-NoBuild specified - skipping image build."
}

# ── remove stale container ────────────────────────────────────────────────────
Write-Step "Removing any existing container named '$ContainerName'"
$existing = docker ps -aq --filter "name=^${ContainerName}$" 2>$null
if ($existing) {
    docker rm -f $ContainerName | Out-Null
    Write-OK "Removed stale container."
} else {
    Write-OK "No existing container to remove."
}

# ── build run arguments ───────────────────────────────────────────────────────
$runArgs = @("run", "--name", $ContainerName, "--restart", "unless-stopped")
$runArgs += @("-p", "${GrpcPort}:50051")
if ($CodeServerPort -gt 0) {
    $runArgs += @("-p", "${CodeServerPort}:8080")
}
if ($Detach) {
    $runArgs += "-d"
}
$runArgs += $ImageTag

# Activate conda env, then start the gRPC server from the cloned MTO repo.
$serverCmd = "source /opt/conda/etc/profile.d/conda.sh && conda activate OFTPMSoptimiser && cd /workspace/MTO && git pull && python 3Dheatsink_gyroid/grpc_server/server.py --port 50051"
$runArgs += @("/bin/bash", "-c", $serverCmd)

# ── run ───────────────────────────────────────────────────────────────────────
Write-Step "Starting container '$ContainerName'"
& docker @runArgs
if ($LASTEXITCODE -ne 0) { throw "docker run failed (exit $LASTEXITCODE)." }

# ── summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Container started." -ForegroundColor Green
Write-Host ""
Write-Host "  gRPC server  : localhost:$GrpcPort"
if ($CodeServerPort -gt 0) {
    Write-Host "  code-server  : http://localhost:$CodeServerPort"
}
Write-Host ""
Write-Host "Connect with client.py:"
Write-Host "  python client.py --host localhost --port $GrpcPort status" -ForegroundColor White
Write-Host ""
Write-Host "Useful commands:"
Write-Host "  docker logs -f $ContainerName        # tail server output"
Write-Host "  docker exec -it $ContainerName bash   # open a shell"
Write-Host "  docker stop $ContainerName            # stop the container"
