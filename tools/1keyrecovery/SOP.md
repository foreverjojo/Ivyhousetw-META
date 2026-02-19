本檔案用途：回台灣新電腦（Windows 11）從零恢復 Ivyhousetw-META 開發環境的 SOP（含 Full‑fidelity / GHCR digest pinned）。

# 回台灣 Windows 11 一鍵恢復 SOP（Full‑fidelity）

## 重要前提（請先看）

- 此 repo 與對應的 GHCR devcontainer image 為 **private**；你需要具備存取權限。
- 目標是用 **VS Code Dev Containers** 進入容器內工作，避免依賴本機 Python/.venv。
- **不要**把任何 token / API key 寫進 repo；一律使用 **Windows 環境變數** 或私密檔案（不進版控）。

## 0) 你出發前（在舊電腦上）

- 確認所有要帶走的改動都已 `commit` + `push` 到 `main`。
- 確認 `uv.lock` 已在 repo 內（用於 `uv sync --frozen` 的可重現依賴）。

## 1) 新電腦一次性準備（Windows 11）

1. 安裝 VS Code（建議也登入 GitHub 以啟用 Settings Sync）。
2. 安裝 Git。
3. 安裝 Docker Desktop。
   - 建議啟用 WSL2 backend（Docker Desktop 安裝流程會引導）。
   - 安裝後先啟動 Docker Desktop 一次，確保 Engine 正常。
4. VS Code 安裝 Microsoft 的 Dev Containers extension。

## 2) 取得存取權（repo + GHCR）

### 2.1 Clone repo（建議用 SSH 或 HTTPS）

- 用 Git clone 到你習慣的位置（例如 `C:\work\Ivyhousetw-META`）。

### 2.2 GHCR 登入（pull private image 必要）

- 你需要一個 **Classic PAT**（建議），至少包含：
  - `read:packages`
  - 若遇到 pull private package 仍 403/401，再補上 `repo`

在 PowerShell（建議不要把 token 寫進指令歷史；可先放環境變數）：

```powershell
# 方式 A：環境變數（本機）
setx GHCR_TOKEN "<your_pat_here>"
setx GHCR_USERNAME "<your_github_username>"

# 重新開一個 PowerShell 視窗後：
docker login ghcr.io -u $env:GHCR_USERNAME -p $env:GHCR_TOKEN
```

> 註：本 repo 的 `pin_devcontainer_image.py` 會讀 `GHCR_TOKEN`（必要時也讀 `GHCR_USERNAME`）協助解析 digest。

## 3) Full‑fidelity（容器層完全一致）主要流程

> 這是你指定的「Full‑fidelity」做法：使用 GHCR 預建 image，並盡量 pin 到 `@sha256:<digest>` 避免 tag 漂移。

1. 用 VS Code 打開專案資料夾。
2. （建議先做一次靜態檢查）在 VS Code Terminal 執行：

```powershell
python scripts/portable/verify_restore_state.py --json
```

3. 執行 digest pin（會嘗試把 devcontainer 切到 image 模式並 pin digest）：

```powershell
python scripts/portable/pin_devcontainer_image.py
```

4. 重新開容器：
   - `Ctrl+Shift+P` → `Dev Containers: Reopen in Container`
5. 容器第一次建立完成後，跑兩個驗證：

```powershell
python scripts/portable/check_extensions_consistency.py --verbose
python scripts/portable/verify_restore_state.py --strict
```

6. 在容器內啟動（依你的工作流程選一個）：

```powershell
streamlit run app.py
```

## 4) 最省事版本（但一致性略低）

如果你不在意「容器 image digest 完全一致」，只想快速開工：

1. VS Code 打開 repo
2. `Dev Containers: Reopen in Container`
3. 需要時再跑：

```powershell
python scripts/portable/verify_restore_state.py
```

## 5) 常見問題排查（Windows 11）

### 5.1 Dev Container 起不來 / Docker 連不上

- 確認 Docker Desktop 已啟動。
- 確認 WSL2 正常（Docker Desktop 設定頁通常可檢查）。

### 5.2 Pull GHCR image 401/403

- 確認你 `docker login ghcr.io` 成功。
- PAT scopes 至少有 `read:packages`；若仍不行再加 `repo`。
- 確認你帳號對該 package 有讀取權（repo private 時很常是權限問題）。

### 5.3 Extensions 安裝結果跟現在不一致

- 先跑：

```powershell
python scripts/portable/check_extensions_consistency.py --verbose
```

- 若要自動修正清單同步（會覆寫 devcontainer/idx 來源）：

```powershell
python scripts/portable/check_extensions_consistency.py --fix
```

## 6) 參考文件（更完整）

- 環境復原指南：`doc/ENVIRONMENT_RECOVERY.md`
- 新電腦一鍵開工：`doc/NEW_MACHINE_SETUP.md`
- portable 腳本總覽：`scripts/portable/README.md`
