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

function Print-Preflight {
  Write-Host "=== Preflight Checks (Windows) ==="
  Write-Host "- Docker Desktop requires virtualization + WSL2 backend (recommended)."
  Write-Host "- Dev Containers requires VS Code + Dev Containers extension + Docker running."
  Write-Host ""

  try {
    $sys = systeminfo 2>$null
    if ($sys) {
      $virt = $sys | Select-String -Pattern "Virtualization Enabled In Firmware" -SimpleMatch
      if ($virt) { Write-Host $virt.Line }
      $hv = $sys | Select-String -Pattern "Hyper-V Requirements" -SimpleMatch
      if ($hv) { Write-Host $hv.Line }
    }
  } catch { }

  if (Get-Command wsl -ErrorAction SilentlyContinue) {
    try {
      Write-Host "`nWSL status:"
      wsl --status
    } catch {
      Write-Host "[WARN] wsl exists but 'wsl --status' failed. You may need to enable WSL2 features and reboot."
    }
  } else {
    Write-Host "`n[WARN] WSL not found. Recommended: run 'wsl --install' then reboot."
  }
  Write-Host ""
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
Print-Preflight

Winget-Install -id "Microsoft.VisualStudioCode" -name "VS Code"
Winget-Install -id "Git.Git" -name "Git"
Winget-Install -id "Python.Python.3.11" -name "Python 3.11"

if (-not $SkipDocker) {
  Winget-Install -id "Docker.DockerDesktop" -name "Docker Desktop"
}

$repoPath = Get-RepoPath
Ensure-Repo $repoPath

$pinScript = Join-Path $repoPath "scripts\portable\pin_devcontainer_image.py"
if (($env:WITH_GHCR_PINNED -eq "1") -and (Test-Path $pinScript)) {
  try {
    Write-Host "Pinning Dev Container image (GHCR; best-effort digest)..."
    python $pinScript
  } catch {
    Write-Host "[WARN] Failed to pin devcontainer image. You can run later:"
    Write-Host "       python scripts\\portable\\pin_devcontainer_image.py"
  }
} elseif (Test-Path $pinScript) {
  Write-Host "[INFO] GHCR pinned devcontainer is opt-in. To enable for this run:"
  Write-Host "       setx WITH_GHCR_PINNED 1"
  Write-Host "       (restart PowerShell) then re-run bootstrap_windows.ps1"
}

$extInstaller = Join-Path $repoPath "scripts\portable\install_extensions.ps1"
if (Test-Path $extInstaller) {
  Write-Host "Installing VS Code extensions..."
  powershell -ExecutionPolicy Bypass -File $extInstaller -RepoRoot $repoPath
}

if (-not $SkipDocker) {
  if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "`nDocker check:"
    try { docker version | Out-Null } catch { Write-Host "[WARN] 'docker version' failed. Please open Docker Desktop and wait until it's running." }
  } else {
    Write-Host "`n[WARN] Docker CLI not found yet. Please open Docker Desktop once and wait for initialization."
  }
}

Write-Host "Done. Next steps:"
Write-Host "- Open the repo in VS Code: code $repoPath"
Write-Host "- Then: Dev Containers: Reopen in Container"
Write-Host "If 'code' is not recognized, restart your terminal and open VS Code once."
Write-Host ""
Write-Host "Recommended verification:"
Write-Host "- python scripts\\portable\\check_extensions_consistency.py --verbose"
Write-Host "- (inside container) uv sync --frozen"
