param(
  [string]$Owner = "foreverjojo",
  [string]$Repo = "Ivyhousetw-META",
  [string]$Branch = "main",
  [string]$DestRoot = "$HOME\src",
  [switch]$SkipDocker
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-Admin {
  $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
  $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if (-not $isAdmin) {
    Write-Host "[ERROR] Please run PowerShell as Administrator."
    Write-Host "        (Right click PowerShell -> Run as administrator)"
    exit 1
  }
}

function Assert-Winget {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] winget not found. Please install 'App Installer' from Microsoft Store, then re-run."
    exit 1
  }
}

function Ensure-Folder([string]$path) {
  if (!(Test-Path $path)) { New-Item -ItemType Directory -Path $path | Out-Null }
}

function Get-RepoPath {
  Ensure-Folder $DestRoot
  return (Join-Path $DestRoot $Repo)
}

function Download-RepoZip([string]$targetPath) {
  $zipUrl = "https://github.com/$Owner/$Repo/archive/refs/heads/$Branch.zip"
  $zipFile = Join-Path $env:TEMP "$Repo-$Branch.zip"

  Write-Host "Downloading repo zip: $zipUrl"
  Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile

  if (Test-Path $targetPath) {
    Write-Host "Removing existing folder: $targetPath"
    Remove-Item -Recurse -Force $targetPath
  }

  Expand-Archive -Path $zipFile -DestinationPath $DestRoot -Force

  $expanded = Join-Path $DestRoot "$Repo-$Branch"
  if (!(Test-Path $expanded)) {
    throw "Expected extracted folder not found: $expanded"
  }

  Rename-Item -Path $expanded -NewName $Repo
  Remove-Item $zipFile -Force
}

function Ensure-Repo([string]$repoPath) {
  if (Get-Command git -ErrorAction SilentlyContinue) {
    if (Test-Path (Join-Path $repoPath ".git")) {
      Write-Host "Updating repo: $repoPath"
      pushd $repoPath
      git fetch --all
      git checkout $Branch
      git pull --ff-only
      popd
    } else {
      Write-Host "Cloning repo into: $repoPath"
      git clone "https://github.com/$Owner/$Repo.git" $repoPath
    }
    return
  }

  Write-Host "Git not found yet; using zip download."
  Download-RepoZip $repoPath
}

function Winget-Install([string]$id, [string]$name) {
  Write-Host "Installing: $name ($id)"
  winget install --id $id -e --accept-source-agreements --accept-package-agreements
}

Assert-Admin
Assert-Winget

Winget-Install -id "Microsoft.VisualStudioCode" -name "VS Code"
Winget-Install -id "Git.Git" -name "Git"
Winget-Install -id "Python.Python.3.11" -name "Python 3.11"

if (-not $SkipDocker) {
  Winget-Install -id "Docker.DockerDesktop" -name "Docker Desktop"
}

$repoPath = Get-RepoPath
Ensure-Repo $repoPath

$extInstaller = Join-Path $repoPath "scripts\portable\install_extensions.ps1"
if (Test-Path $extInstaller) {
  Write-Host "Installing VS Code extensions..."
  powershell -ExecutionPolicy Bypass -File $extInstaller -RepoRoot $repoPath
}

Write-Host "Done. Next steps:"
Write-Host "- Open the repo in VS Code: code $repoPath"
Write-Host "- Then: Dev Containers: Reopen in Container"
Write-Host "If 'code' is not recognized, restart your terminal and open VS Code once."
