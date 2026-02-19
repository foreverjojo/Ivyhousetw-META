# 新電腦一鍵開工（Ivyhousetw-META）

目標：回台灣換電腦後，直接用 Dev Container 開專案即可開始工作，不再依賴本機 Python/.venv/.python311。

## 0) 先確認 Git 狀態

1. 先把目前這台電腦的變更 commit + push（至少要包含 `.devcontainer/` 與文件更新）。
2. 確認 `uv.lock` 有被 commit（用來鎖住依賴版本，確保新電腦環境一致）。

## 1) 新電腦準備（一次性）

1. 安裝 VS Code
2. 安裝 Docker Desktop（Windows）
3. VS Code 安裝 Dev Containers extension（Microsoft）
4. Clone 專案到本機資料夾

## 2) 用 Dev Container 開專案（主要流程）

1. VS Code 打開專案資料夾
2. `Ctrl+Shift+P` → `Dev Containers: Reopen in Container`
3. 第一次建立容器會花一點時間
4. 容器建立完後會自動執行依賴安裝（`.devcontainer/devcontainer.json` 的 `postCreateCommand`）

> 如果你看到依賴安裝失敗，請先確認 `uv.lock` 是否存在且已進版控；否則會走 `requirements.txt` 路徑。
>
> ✅ 建議在新電腦先跑一次可機械化檢查（不修改系統）：
> - `python scripts/portable/verify_restore_state.py`

> 若你要追求容器層「完全一致」：portable 腳本會自動執行 `pin_devcontainer_image.py`，或你也可手動執行：
> - `python scripts/portable/pin_devcontainer_image.py`

## 3) 啟動本機開發（容器內）

### 3.0 Terminal extensions 初始化（建議先做）

在容器內執行：

```bash
bash scripts/vscode/install_terminal_orchestrator.sh
```

完成後在 VS Code 執行 `Developer: Reload Window`。

若要啟用 Monitor 的 Proposed API 主路徑，請在 Windows 端 runtime `argv.json`（例如 `%APPDATA%\\Code - Insiders\\User\\argv.json`）加入：

```json
{
  "enable-proposed-api": [
    "ivyhouse-local.ivyhouse-terminal-monitor",
    "ivyhouse-local.ivyhouse-terminal-orchestrator"
  ]
}
```

儲存後完整關閉 VS Code 再重啟。

- Streamlit：
  - `streamlit run app.py`

> `main.py` 是 Cloud Run 用的 Flask wrapper；本機開發通常直接跑 `app.py` 即可。

## 4) Secrets / 憑證（不要進版控）

本專案用到的敏感資訊不要 commit：

- `ifp.env`：本機/容器開發用環境變數（請用 `ifp.env.example` 生成）
- `secrets/*.json`：GCP Service Account key（如果需要）

建議做法：

1. 在新電腦複製 `ifp.env.example` → `ifp.env`，填入非敏感的設定（API Key 請走 Secret Manager 或 OS 環境變數）。
2. `GOOGLE_APPLICATION_CREDENTIALS` 指向 `secrets/your-service-account-key.json`（檔案用安全方式移轉，不要丟到 Git）。

> 容器內環境變數注入：本 repo 已在 `.devcontainer/devcontainer.json` 設定 `remoteEnv`（從本機 `localEnv` 注入）。

## 5) 建議：避免把本機環境資料夾當成「可重現」

以下資料夾不應作為「可移植環境」來源（換電腦會失效/不一致）：

- `.venv/`
- `.python311/`
- `.pytest_cache/`
- `logs/`（runtime）
- `history/`（除非你希望連歷史產物也一併帶走）
