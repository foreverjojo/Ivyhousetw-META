# 環境復原指南（Environment Recovery Guide）

此指南適用於全新電腦，幫助你快速恢復目前的開發環境，包括安裝必要工具、配置專案依賴，並確保操作介面與目前一致。

---

## 0. 一鍵復原（建議）

本 repo 內建「portable 一鍵復原」腳本：
- 位置：`scripts/portable/`
- 內容：安裝 VS Code / Docker / Git / Python（視作業系統與可用套件管理工具而定）+ 下載本 repo + 安裝本 repo 建議的 VS Code extensions

### 0.z 一鍵自檢入口指令（建議）

完成 restore / Reopen in Container 後，建議先跑一次自檢（不修改系統）：

```bash
python scripts/portable/self_check.py --strict
```

若提示缺少 `ruff/pytest`（dev dependencies 未安裝），可用以下方式（擇一）：

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

或（若你使用 uv/uv.lock 工作流）：

```bash
uv sync --extra dev
```

### 0.x 一致性等級（你能期待「一模一樣」到什麼程度）

- **Level A（幾乎 100%）**：Dev Container 內 toolchain + Python 依賴（以 `uv.lock` + `uv sync --frozen` 為準）
- **Level B（目標一致）**：workspace 設定（`.vscode/*`）+ extensions 清單一致（devcontainer / .vscode / idx 三方同步）
- **Level C（不保證）**：VS Code 全域 Profile / Keybindings / Snippets / Marketplace extension 版本差異
   - 這部分建議用 **VS Code Settings Sync** 自行處理

> 結論：若你使用 Dev Container + Settings Sync，你會得到「實務上非常接近一模一樣」的環境。

### 0.y Full-fidelity（容器層更接近完全一致：GHCR pinned image）

若你希望「容器內環境」也能達到接近完全一致，建議使用 GHCR 預建的 Dev Container image（由 CI 發佈）。

- CI 會產出 tag：`ghcr.io/foreverjojo/ivyhousetw-meta-devcontainer:devcontainer-<git_sha>`
- portable 腳本在你啟用 `WITH_GHCR_PINNED=1` 時，會在 clone 後執行：
   - `python scripts/portable/pin_devcontainer_image.py`
   - 使 `.devcontainer/devcontainer.json` 切換為 image 模式，並盡量 pin 到 digest（@sha256）

若你已完成 clone，但尚未啟用 full-fidelity，也可以手動執行：
```bash
python scripts/portable/pin_devcontainer_image.py
```

若你在新機器 pull image 時遇到權限問題：
```bash
docker login ghcr.io
```

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
   ```
2. 安裝依賴：
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
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
   - `esbenp.prettier-vscode`
   - （完整清單見 `.vscode/extensions.json`）

本 repo 另含 3 個 local terminal extensions（由 portable 安裝腳本 best-effort 打包安裝）：
- `ivyhouse-local.ivyhouse-terminal-injector`
- `ivyhouse-local.ivyhouse-terminal-monitor`
- `ivyhouse-local.ivyhouse-terminal-orchestrator`（legacy）

如果要手動補裝（容器內）：
```bash
bash scripts/vscode/install_terminal_orchestrator.sh
```

### 3.2 Proposed API runtime arguments（重要）

若要讓 Monitor 主路徑生效，請設定 runtime `argv.json`：

```json
{
   "enable-proposed-api": [
      "ivyhouse-local.ivyhouse-terminal-monitor",
      "ivyhouse-local.ivyhouse-terminal-orchestrator"
   ]
}
```

常見路徑：
- Windows Insiders：`%APPDATA%\\Code - Insiders\\User\\argv.json`
- Windows Stable：`%APPDATA%\\Code\\User\\argv.json`
- macOS Insiders：`~/Library/Application Support/Code - Insiders/User/argv.json`
- Linux Insiders：`~/.config/Code - Insiders/User/argv.json`

儲存後請完整關閉並重啟 VS Code，再檢查 `.service/terminal_capture/monitor_debug.jsonl` 是否出現 `proposed_api: true`。

本 repo 提供自動化工具確保三處 extensions 清單（devcontainer / .vscode / idx）保持同步：

```bash
# 檢查一致性
python scripts/portable/check_extensions_consistency.py --verbose

# 若有不一致，自動修復
python scripts/portable/check_extensions_consistency.py --fix
```

---

## 4. 設定 API 金鑰 & 環境變數

### 4.1 VS Code OAI Copilot 配置
若要啟用 VS Code 中 OAI Compatible Provider 的 Copilot 功能，需設定環境變數：

**方式 1：Windows 系統環境變數（推薦）**
```powershell
setx OAI_API_KEY "sk-your-api-key-here"
setx OAI_BASE_URL "http://host.docker.internal:8045/v1"
```
重啟 VS Code 後即可生效。

**方式 2：本機開發用 .env 檔（不進版控）**
```bash
# 複製範本
cp ifp.env.example ifp.env

# 編輯 ifp.env，填入金鑰
OAI_API_KEY=sk-your-api-key-here
OAI_BASE_URL=http://host.docker.internal:8045/v1
```

**方式 3：Dev Container 啟動時注入（推薦用於容器）**
在 `.devcontainer/devcontainer.json` 的 `remoteEnv` 加入：
```json
"remoteEnv": {
  "OAI_API_KEY": "${localEnv:OAI_API_KEY}",
  "OAI_BASE_URL": "${localEnv:OAI_BASE_URL}"
}
```

### 4.2 其他敏感資訊
- 不要將 API key / token 放入 repo（`.gitignore` 會阻擋 `.env` 與 `secrets/` 目錄）
- 敏感資訊優先使用：系統環境變數 → `.env`（本機） → GCP Secret Manager（雲端）

---

## 5. 驗證環境
1. 確保 Docker 容器能正常啟動，並執行以下指令檢查：
   ```bash
   docker ps
   ```
2. 確保 Python 依賴已正確安裝：
   ```bash
   pip list
   ```
3. 驗證 extensions 清單一致：
   ```bash
   python scripts/portable/check_extensions_consistency.py
   ```
4. 啟動應用程式，並確認無錯誤：
   ```bash
   streamlit run app.py
   ```

---

## 常見問題排查

### Q: Dev Container 啟動失敗（Docker/WSL 相關）
**A:**
- Windows：確認 Docker Desktop 已啟用 WSL2 backend
- macOS：確認 Docker Desktop 正常運行
- Linux：確認 Docker daemon 已啟動（`sudo systemctl start docker`）

### Q: `code` CLI 無法找到（Windows）
**A:** 在 VS Code 安裝完畢後：
1. 重啟 PowerShell / Terminal
2. 執行 `code --version` 確認 CLI 可用
3. 若仍失敗，重新執行 `bootstrap_windows.ps1`

### Q: 環境變數設定後 Copilot 仍無反應
**A:**
1. 確認 `OAI_API_KEY` 已設定：`echo $env:OAI_API_KEY`（Windows）或 `echo $OAI_API_KEY`（macOS/Linux）
2. 重啟 VS Code
3. 若使用 Dev Container，重建容器（`Dev Containers: Rebuild Container`）

---

完成以上步驟後，你的開發環境應該已完全恢復，且能在另一台電腦上一鍵重現！
