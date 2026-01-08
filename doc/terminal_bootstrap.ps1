# doc/terminal_bootstrap.ps1
# Purpose: Safe, manual, session-only bootstrap for VS Code PowerShell terminal
# - ExecutionPolicy (Process only)
# - UTF-8 output encoding
# - Quick checks for python/pip pointing to project venv
# IMPORTANT: This script does NOT modify user profile or system settings.

Write-Host "=== [1/3] ExecutionPolicy (Process) ==="
try {
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
  $pol = Get-ExecutionPolicy -List
  $processPolicy = ($pol | Where-Object { $_.Scope -eq "Process" }).ExecutionPolicy
  Write-Host "Process ExecutionPolicy = $processPolicy"
} catch {
  Write-Host "[WARN] Failed to set ExecutionPolicy for Process scope."
  Write-Host $_
}

Write-Host "`n=== [2/3] UTF-8 Encoding ==="
try {
  chcp 65001 | Out-Null
  $OutputEncoding = [System.Text.UTF8Encoding]::new()
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
  Write-Host "Encoding set to UTF-8 (65001) for this session."
  Write-Host "中文測試：艾薇手工坊 / 毛毛好日"
} catch {
  Write-Host "[WARN] Failed to set UTF-8 encoding."
  Write-Host $_
}

Write-Host "`n=== [3/3] Python/Venv Quick Check ==="
try {
  Write-Host "where.exe python:"
  where.exe python
} catch {
  Write-Host "[WARN] where.exe python failed."
}

try {
  Write-Host "`npython sys.executable:"
  python -c "import sys; print(sys.executable)"
} catch {
  Write-Host "[WARN] python not runnable in this terminal."
  Write-Host "Expected: python points to .venv\Scripts\python.exe"
}

try {
  Write-Host "`npython -m pip --version:"
  python -m pip --version
} catch {
  Write-Host "[WARN] pip check failed."
}
