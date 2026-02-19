# 自動安裝 Python 3.11 並啟動專案的腳本 (修正版)
# 目的：解決本地只有 Python 3.14 不支援 crewai 的問題
# 修正：直接使用 embed python 安裝套件，不使用 venv (因為 embed 版不支援 venv)

$ErrorActionPreference = "Stop"
$ProjectRoot = Get-Location

# 1. 檢查並下載 Python 3.11
$PythonDir = Join-Path $ProjectRoot ".python311"
$PythonZip = Join-Path $ProjectRoot "python-3.11.9-embed-amd64.zip"
$PythonUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"

if (-not (Test-Path $PythonDir)) {
    Write-Host "正在下載 Python 3.11 (因為 crewai 不支援 Python 3.14)..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $PythonUrl -OutFile $PythonZip

    Write-Host "正在解壓縮 Python 3.11..." -ForegroundColor Cyan
    Expand-Archive -Path $PythonZip -DestinationPath $PythonDir
    Remove-Item $PythonZip

    # 修正 embed 版的 pip 路徑問題 (開啟 import site)
    $PthFile = Get-ChildItem -Path $PythonDir -Filter "*._pth" | Select-Object -First 1
    $Content = Get-Content $PthFile.FullName
    # 取消註解 import site
    $Content = $Content -replace "#import site", "import site"
    Set-Content -Path $PthFile.FullName -Value $Content

    # 下載 get-pip.py
    Write-Host "正在安裝 pip..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile (Join-Path $PythonDir "get-pip.py")
    & (Join-Path $PythonDir "python.exe") (Join-Path $PythonDir "get-pip.py") --no-warn-script-location
}

$PythonExe = Join-Path $PythonDir "python.exe"

# 2. 安裝依賴 (直接裝在 embed python 裡)
Write-Host "正在安裝依賴 (這可能需要幾分鐘)..." -ForegroundColor Cyan
& $PythonExe -m pip install -r requirements.txt --no-warn-script-location

# 3. 啟動 Streamlit
Write-Host "正在啟動 Streamlit..." -ForegroundColor Green
& $PythonExe -m streamlit run app.py
