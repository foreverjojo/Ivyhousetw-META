# 環境復原指南（Environment Recovery Guide）

此指南適用於全新電腦，幫助你快速恢復目前的開發環境，包括安裝必要工具、配置專案依賴，並確保操作介面與目前一致。

---

## 0. 一鍵復原（建議）

本 repo 內建「portable 一鍵復原」腳本：
- 位置：`scripts/portable/`
- 內容：安裝 VS Code / Docker / Git / Python（視作業系統與可用套件管理工具而定）+ 下載本 repo + 安裝本 repo 建議的 VS Code extensions

### 0.1 Windows（PowerShell / 需系統管理員）

建議先打開以下網址確認腳本內容，再執行：
- https://raw.githubusercontent.com/foreverjojo/Ivyhousetw-META/main/scripts/portable/bootstrap_windows.ps1

一行指令（PowerShell 以系統管理員身分開啟後執行）：
```powershell
iwr -useb https://raw.githubusercontent.com/foreverjojo/Ivyhousetw-META/main/scripts/portable/bootstrap_windows.ps1 | iex
```

### 0.2 macOS（Terminal）

一行指令：
```bash
curl -fsSL https://raw.githubusercontent.com/foreverjojo/Ivyhousetw-META/main/scripts/portable/bootstrap.sh | bash
```

### 0.3 Linux（Debian/Ubuntu，Terminal）

一行指令（預設只裝 git/python 等基礎工具；Docker / VS Code 可選）：
```bash
curl -fsSL https://raw.githubusercontent.com/foreverjojo/Ivyhousetw-META/main/scripts/portable/bootstrap.sh | bash
```

若你希望 Linux 也自動安裝 Docker / VS Code：
```bash
WITH_DOCKER=1 WITH_VSCODE=1 curl -fsSL https://raw.githubusercontent.com/foreverjojo/Ivyhousetw-META/main/scripts/portable/bootstrap.sh | bash
```

---

## 1. 安裝必要工具

### 1.1 安裝 VS Code
1. 前往 [VS Code 官方網站](https://code.visualstudio.com/) 下載並安裝。
2. 安裝完成後，建議同步你的 VS Code 設定（若有使用 GitHub 登入，可自動同步）。

### 1.2 安裝 Docker
1. 前往 [Docker 官方網站](https://www.docker.com/products/docker-desktop/) 下載並安裝 Docker Desktop。
2. 啟動 Docker Desktop，並確保 Docker Daemon 正常運行。

### 1.3 安裝 Git
1. 前往 [Git 官方網站](https://git-scm.com/) 下載並安裝。
2. 安裝完成後，執行以下指令確認版本：
   ```bash
   git --version
   ```

### 1.4 安裝 Python
1. 前往 [Python 官方網站](https://www.python.org/downloads/) 下載並安裝 Python 3.11+。
2. 確保勾選「Add Python to PATH」。
3. 安裝完成後，執行以下指令確認版本：
   ```bash
   python --version
   pip --version
   ```

---

## 2. 配置專案環境

### 2.1 克隆專案
1. 打開終端機，執行以下指令克隆專案：
   ```bash
   git clone https://github.com/foreverjojo/Ivyhousetw-META.git
   cd Ivyhousetw-META
   ```

### 2.2 啟動 Dev Container
1. 在 VS Code 中打開專案資料夾。
2. 按下 `F1`，搜尋並選擇 **Dev Containers: Reopen in Container**。
3. 等待容器啟動並自動安裝依賴。

### 2.3 本機執行（可選）
若不使用 Dev Container，可手動配置本機環境：
1. 建立虛擬環境：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. 安裝依賴：
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. 啟動應用程式：
   ```bash
   streamlit run app.py
   ```

---

## 3. 安裝 VS Code Extensions

### 3.1 安裝建議的 Extensions
1. 在 VS Code 中，打開 Extensions 視窗（快捷鍵：`Ctrl+Shift+X`）。
2. 搜尋並安裝以下 Extensions：
   - `ms-python.python`
   - `ms-python.vscode-pylance`
   - `github.copilot`
   - `eamodio.gitlens`
   - `esbenp.prettier-vscode`
   - （完整清單見 `.vscode/extensions.json`）

---

## 4. 驗證環境
1. 確保 Docker 容器能正常啟動，並執行以下指令檢查：
   ```bash
   docker ps
   ```
2. 確保 Python 依賴已正確安裝：
   ```bash
   pip list
   ```
3. 啟動應用程式，並確認無錯誤：
   ```bash
   streamlit run app.py
   ```

---

完成以上步驟後，你的開發環境應該已完全恢復！
