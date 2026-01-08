# Terminal Bootstrap Checklist (VS Code / Windows / PowerShell)

## Goal
Keep VS Code terminal consistent per session:
- ExecutionPolicy (Process only)
- UTF-8 output (avoid garbled text)
- Python points to project .venv

## Steps (manual)
1) Open VS Code -> Terminal -> New Terminal (PowerShell)
2) Run:
   - powershell -ExecutionPolicy Bypass -File .\doc\terminal_bootstrap.ps1

## Pass Criteria
- Get-ExecutionPolicy -List shows:
  - Process = Bypass
- python -c "import sys; print(sys.executable)" points to:
  - ...\Ivyhousetw-META\.venv\Scripts\python.exe
- Chinese output is readable (no mojibake)
- python -m pip --version shows pip under .venv

## Notes
- This is session-only; closing terminal resets state.
- No auto-run, no profiles modified, no system-wide changes.
