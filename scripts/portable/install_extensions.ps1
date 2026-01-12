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

  $fallbacks = @(
    "$Env:LocalAppData\Programs\Microsoft VS Code\bin\code.cmd",
    "$Env:ProgramFiles\Microsoft VS Code\bin\code.cmd",
    "$Env:ProgramFiles(x86)\Microsoft VS Code\bin\code.cmd"
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
$failed = 0
foreach ($ext in $exts) {
  if ([string]::IsNullOrWhiteSpace($ext)) { continue }
  Write-Host "- $ext"
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
