# Plan: Idx-014

**Index**: Idx-014
**Created**: 2026-01-17
**Planner**: Codex CLI (based on repo scan)
**Predecessor**: Idx-013_one_click_restore_hardening.md

---

## 🎯 目標

把「一鍵恢復」從「可用」提升到「可重現且接近一致」，並明確定義哪些部分能做到**幾乎一樣**（Dev Container / workspace），哪些部分**做不到 100% 一樣**（OS 層、VS Code 全域 Profile、Extension 版本）。

---

## 📋 SPEC

### Goal
在台灣的另一台全新電腦上，用 `scripts/portable/` + Dev Containers 開啟後，能以最少人工介入完成：
- 同一份 Dev Container toolchain（Python/Node/uv 等）
- 同一份 workspace 設定（`.vscode/*`）
- 同一份 extensions 清單（devcontainer / .vscode / idx 三方一致）
- 具備可驗證的「恢復完成」檢查點與 troubleshooting

### Non-goals
- ❌ 不做：保證 VS Code **全域** Profile/Keybindings/Snippets 100% 一樣（需 Settings Sync 或手動 profile 管理）
- ❌ 不做：強制鎖定 Marketplace extension 版本（需要 VSIX pinning/鏡像，維護成本高；改用「清單一致 + 可驗證」）
- ❌ 不做：自動搬運任何 secrets（只提供注入規範）

### Acceptance Criteria
1. ✅ Windows portable script 具備「WSL2/Docker/virtualization」前置檢查與清楚指引（必要時提示需 reboot）
2. ✅ Dev Container toolchain 版本「可重現」：至少 pin `python` base image digest（或明確版本策略）+ pin `uv` 版本
3. ✅ `devcontainer-rebuild-test` CI 改成驗證與 Dev Container 實際一致的依賴安裝路徑（優先 `uv.lock`）
4. ✅ 文件中明確標示「一致性等級」：
   - Level A：容器內 toolchain/依賴（目標接近 100%）
   - Level B：workspace 設定與 extensions 清單（目標一致）
   - Level C：VS Code 全域 profile/extension 版本（不保證；提供建議作法）
5. ✅ Dev Container 支援「環境變數注入」最佳實務（例如 `OAI_API_KEY/OAI_BASE_URL/OPENROUTER_API_KEY` 走 `remoteEnv: ${localEnv:...}` 或文件明確指示）

### Edge cases
- Windows 無 App Installer → `winget` 不可用：提供替代方案（手動安裝或 zip fallback）
- Windows Docker Desktop 未啟用 WSL2 backend / virtualization disabled → Dev Container 起不來：需指引與檢查命令
- 新機器未曾啟動 VS Code → `code` CLI 未可用：需提示與 fallback（目前已做，但需對齊文件）
- `uv.lock` 缺失或未更新：需明確阻擋「宣稱一致」並提示如何產生/commit

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- `doc/plans/Idx-013_one_click_restore_hardening.md`
- `doc/ENVIRONMENT_RECOVERY.md`
- `doc/NEW_MACHINE_SETUP.md`
- `.devcontainer/Dockerfile`
- `.devcontainer/devcontainer.json`
- `.vscode/extensions.json`
- `.vscode/settings.json`
- `.idx/dev.nix`
- `scripts/portable/*`
- `.github/workflows/devcontainer-rebuild-test.yml`
- `.github/workflows/check-extensions.yml`

### Assumptions
- ✅ VERIFIED：extensions 三方一致性可由 `scripts/portable/check_extensions_consistency.py` 驗證
- ✅ VERIFIED：Dev Container 依賴安裝目前以 `uv.lock` 優先（`postCreateCommand`）
- ⚠️ RISK: unverified：台灣新電腦的 BIOS virtualization、Windows WSL2、Docker Desktop 安裝/啟動狀態都正常

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `scripts/portable/bootstrap_windows.ps1` - 加 WSL2/Docker/virtualization preflight（不做自動改系統設定，僅檢查+指引）
- `scripts/portable/bootstrap_linux.sh` - Docker 安裝後提示 group/daemon 啟動（更明確）
- `scripts/portable/bootstrap_macos.sh` - Docker Desktop 首次啟動提醒（更明確）
- `doc/ENVIRONMENT_RECOVERY.md` - 明確一致性等級 + Windows 排查（WSL2/Docker）
- `doc/NEW_MACHINE_SETUP.md` - 對齊「容器優先」與 `uv.lock` 規則
- `.devcontainer/Dockerfile` - pin base image digest + pin uv version（提升可重現）
- `.devcontainer/devcontainer.json` - 補齊 `remoteEnv` 注入策略（只引用 `${localEnv:...}`，不寫入 secrets）
- `.github/workflows/devcontainer-rebuild-test.yml` - 改成跑與容器一致的依賴路徑（`uv sync --frozen`）
- （可選）新增 `scripts/portable/verify_restore_state.py` - 只做「檢查」：uv.lock 存在、extensions 一致、devcontainer 主要檔案存在

### Done 定義
1. ✅ Windows 一鍵腳本在缺少 WSL2/Docker prerequisites 時不會 silent fail，會輸出可操作指引
2. ✅ Dev Container 版本策略可驗證（至少 uv 版本固定、base image 可重現）
3. ✅ CI 能驗證 Dev Container build + uv.lock 安裝路徑
4. ✅ 文件清楚寫出「做得到的 90% 一致」與「做不到的 10% 一致」

### Rollback 策略
- **Level**: L2
- **前置條件**: 不破壞既有一鍵腳本；遇到行為變更必須保留舊路徑或提供 fallback
- **回滾動作**: `git restore --worktree --staged -- .`

### Max rounds
- **估計**: 2
- **超過處理**: 第 3 輪只允許修文件與 preflight 訊息，不做容器/CI 大調整

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `scripts/portable/bootstrap_windows.ps1` | 修改 | 增加 WSL2/Docker/virtualization preflight 與指引（必要時提示 reboot） |
| `scripts/portable/bootstrap_linux.sh` | 修改 | Docker optional 安裝後補充 daemon/group 指引與常見錯誤提示 |
| `scripts/portable/bootstrap_macos.sh` | 修改 | Docker Desktop 首次啟動提醒與常見問題提示 |
| `doc/ENVIRONMENT_RECOVERY.md` | 修改 | 加入一致性等級定義 + WSL2/Docker 排查更具體 |
| `doc/NEW_MACHINE_SETUP.md` | 修改 | 明確「容器優先」+ `uv.lock` 必須存在與 commit |
| `.devcontainer/Dockerfile` | 修改 | pin base image digest（或明確版本策略）+ pin uv version |
| `.devcontainer/devcontainer.json` | 修改 | 增加 `remoteEnv`（引用 `${localEnv:...}`）以支援 secrets 注入 |
| `.github/workflows/devcontainer-rebuild-test.yml` | 修改 | 改為驗證 `uv sync --frozen`（與容器實際一致） |
| `scripts/portable/verify_restore_state.py` | 新增（可選） | 一鍵復原前/後的可機械化檢查（不修改系統） |

---

## 📝 邏輯細節

### 1) Windows Preflight（bootstrap_windows.ps1）
- 新增檢查與輸出（只讀/提示，不自動改系統設定）：
  - `wsl.exe --status`（不存在或失敗 → 提示安裝 WSL2 / 啟用 Virtual Machine Platform）
  - virtualization 狀態提示（無法可靠檢測就提示「請確認 BIOS virtualization 已開啟」）
  - Docker Desktop 是否安裝、是否啟動（可用 `docker version` 做提示）
- 若 prerequisites 不滿足：
  - 清楚列出「下一步」與「重新執行腳本」的路徑

### 2) Dev Container 可重現策略
- `.devcontainer/Dockerfile`：
  - base image 建議改為 digest pin（例如 `python:3.11-slim@sha256:...`）或明確寫出「每月更新」策略
  - `uv` 版本固定（例如 `pip install uv==X.Y.Z`）
- `.devcontainer/devcontainer.json`：
  - 增加 `remoteEnv`：
    - `OAI_API_KEY: ${localEnv:OAI_API_KEY}`
    - `OAI_BASE_URL: ${localEnv:OAI_BASE_URL}`
    - `OPENROUTER_API_KEY: ${localEnv:OPENROUTER_API_KEY}`
  - 只引用，不提供預設值（避免誤用）

### 3) CI 與實際容器一致（devcontainer-rebuild-test.yml）
- 現況只測 `pip install -r requirements.txt`，與 `postCreateCommand` 的 `uv sync --frozen` 不一致
- 調整為：
  - build devcontainer image
  - run container 並執行 `uv --version` / `uv sync --frozen`（以 `uv.lock` 為真實一致路徑）
  - 若 `uv.lock` 不存在 → workflow fail（防止「宣稱一致」但實際漂移）

### 4) 文件：一致性等級（ENVIRONMENT_RECOVERY / NEW_MACHINE_SETUP）
- 用「Level A/B/C」描述一致性與限制，避免使用者期待「全域設定 100% 一樣」
- 明確指出 extension 版本不鎖定（Marketplace 最新），但清單一致可保障功能面一致

---

## ⚠️ 注意事項

- **資安**：任何 secrets 只能透過 `${localEnv:...}` / OS env / Secret Manager 注入；repo 內不得出現 token/key（包含 backup 檔）
- **可重現性**：uv/base image pin 會提高一致性，但也會增加「更新成本」；需定義更新節奏
- **相容性**：Windows 使用 Docker Desktop 時，WSL2 是常見必要條件（需文件與 preflight 對齊）

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-01-17 00:00:00
plan_approved: [待用戶確認]
scope_policy: strict
expert_required: false
expert_conclusion: N/A
scope_exceptions: []

# Engineer 執行
executor_tool: [待用戶確認: codex-cli|opencode]
executor_tool_version: [待填寫]
executor_user: [待填寫]
executor_start: [待填寫]
executor_end: [待填寫]
session_id: [待填寫]
last_change_tool: [待填寫]

# QA 執行
qa_tool: [待用戶確認: codex-cli|opencode]
qa_tool_version: [待填寫]
qa_user: [待填寫]
qa_start: [待填寫]
qa_end: [待填寫]
qa_result: [PASS|PASS_WITH_RISK|FAIL]
qa_compliance: [待填寫]

# 收尾
log_file_path: doc/logs/Idx-014_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

