param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\.."))
)

$extensionsJson = Join-Path $RepoRoot ".vscode\extensions.json"
if (!(Test-Path $extensionsJson)) {
  Write-Host "[ERROR] Not found: $extensionsJson"
  exit 1
}

try {
  $obj = Get-Content $extensionsJson -Raw | ConvertFrom-Json
  $exts = @($obj.recommendations)
} catch {
  Write-Host "[ERROR] Failed to parse .vscode/extensions.json"
  Write-Host $_
  exit 1
}

function Resolve-CodeCmd {
  $code = Get-Command code -ErrorAction SilentlyContinue
  if ($code) { return $code.Path }

  $insiders = Get-Command code-insiders -ErrorAction SilentlyContinue
  if ($insiders) { return $insiders.Path }

  $fallbacks = @(
    "$Env:LocalAppData\Programs\Microsoft VS Code\bin\code.cmd",
    "$Env:LocalAppData\Programs\Microsoft VS Code Insiders\bin\code-insiders.cmd",
    "$Env:ProgramFiles\Microsoft VS Code\bin\code.cmd",
    "$Env:ProgramFiles\Microsoft VS Code Insiders\bin\code-insiders.cmd",
    "$Env:ProgramFiles(x86)\Microsoft VS Code\bin\code.cmd",
    "$Env:ProgramFiles(x86)\Microsoft VS Code Insiders\bin\code-insiders.cmd"
  )

  foreach ($p in $fallbacks) {
    if (Test-Path $p) { return $p }
  }

  return $null
}

$codeCmd = Resolve-CodeCmd
if (!$codeCmd) {
  Write-Host "[WARN] VS Code CLI 'code' not found on PATH."
  Write-Host "       Open VS Code once, then ensure 'code' is available, or restart terminal."
  Write-Host "       Skipping extension installation."
  exit 0
}

Write-Host "Installing VS Code extensions from $extensionsJson"

$localExtensionMap = @{
  "ivyhouse-local.ivyhouse-terminal-injector" = "tools\vscode_terminal_injector"
  "ivyhouse-local.ivyhouse-terminal-monitor" = "tools\vscode_terminal_monitor"
  "ivyhouse-local.ivyhouse-terminal-orchestrator" = "tools\vscode_terminal_orchestrator"
}

function Install-LocalExtension {
  param(
    [string]$ExtId,
    [string]$RelativePath
  )

  $extDir = Join-Path $RepoRoot $RelativePath
  if (!(Test-Path $extDir)) {
    Write-Host "  [WARN] Local extension source not found: $extDir"
    return $false
  }

  $npm = Get-Command npm -ErrorAction SilentlyContinue
  if (!$npm) {
    Write-Host "  [WARN] npm not found; cannot package local extension: $ExtId"
    return $false
  }

  try {
    Push-Location $extDir
    npm -s exec --yes @vscode/vsce package -- --allow-missing-repository --skip-license | Out-Null
  } catch {
    Write-Host "  [WARN] Failed to package local extension: $ExtId"
    Pop-Location
    return $false
  }

  Pop-Location

  $vsix = Get-ChildItem -Path $extDir -Filter "*.vsix" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

  if (!$vsix) {
    Write-Host "  [WARN] VSIX not found after packaging: $ExtId"
    return $false
  }

  & $codeCmd --install-extension $vsix.FullName --force | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "  [WARN] Failed to install local VSIX: $($vsix.FullName)"
    return $false
  }

  return $true
}

$failed = 0
foreach ($ext in $exts) {
  if ([string]::IsNullOrWhiteSpace($ext)) { continue }
  Write-Host "- $ext"

  if ($localExtensionMap.ContainsKey($ext)) {
    $ok = Install-LocalExtension -ExtId $ext -RelativePath $localExtensionMap[$ext]
    if (-not $ok) { $failed++ }
    continue
  }

  & $codeCmd --install-extension $ext | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "  [WARN] Failed: $ext"
    $failed++
  }
}

if ($failed -gt 0) {
  Write-Host "[WARN] Completed with $failed failures. You can re-run this script after VS Code finishes installing/updating."
  exit 0
}

Write-Host "Done."
