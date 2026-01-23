# Plan: Idx-032

**Index**: Idx-032
**Created**: 2026-01-23
**Planner**: GitHub Copilot

---

## 🎯 目標

針對「回台灣後一鍵恢復到現在一模一樣狀態」做一次治理收斂：

1) 跑一次 Ruff / Pytest 做整體健康檢查，並修到可以通過。
2) 盤點「目前已安裝 extensions」並確保 repo 內所有 extensions list（devcontainer / .vscode / idx）一致；本機 local extension（terminal orchestrator）則用可重現的安裝流程覆蓋。
3) 檢查一鍵恢復（portable scripts + verify_restore_state）與現在環境的差異，若有差異則更新 restore 內容（例如 dev deps / local extension 安裝、script 權限）。

---

## 📋 SPEC

### Goal
讓新機器/回台灣後能透過 repo 內機制（Dev Container / portable scripts）恢復到目前相同的開發體驗與工具鏈。

### Non-goals
- ❌ 不做 secret scan 強化（gitleaks/detect-secrets）
- ❌ 不改動專案商業邏輯/產出內容

### Acceptance Criteria
1. ✅ `python -m ruff check ...` 與 `python -m ruff format --check ...` 皆通過。
2. ✅ `pytest tests/` 全綠（允許既有 golden files 的 skip）。
3. ✅ `python scripts/portable/check_extensions_consistency.py` 通過。
4. ✅ `python scripts/portable/verify_restore_state.py` 通過。
5. ✅ Dev Container `postCreateCommand` 會安裝 dev 依賴（pytest/ruff 等）並自動安裝 local terminal orchestrator extension。
6. ✅ `scripts/portable/*.sh` 與 `scripts/vscode/install_terminal_orchestrator.sh` 具備可執行權限（避免新機器直接執行失敗）。

### Edge cases
- VS Code Marketplace 不支援安裝 repo 內 local extension → 以 `scripts/vscode/install_terminal_orchestrator.sh`（symlink 到 .vscode-server/extensions）處理。
- `uv.lock` 存在但未安裝 dev extra → Dev Container 需改用 `uv sync --frozen --extra dev`。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- `scripts/portable/verify_restore_state.py`
- `.devcontainer/devcontainer.json`
- `.devcontainer/devcontainer.ghcr.json`
- `.vscode/extensions.json`
- `.idx/dev.nix`

### Assumptions
- ✅ VERIFIED：目前已安裝 extensions 與 repo 內三方清單一致（marketplace extensions），但另有 local extension `ivyhouse-local.ivyhouse-terminal-orchestrator`。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `.agent/plans/Idx-032_plan.md` - 新增
- `.agent/logs/Idx-032_log.md` - 新增
- `.agent/Workflow_Plan_index.md` - 修改（登記 Idx-032）

- `tests/test_service_manager.py` - Ruff format / 測試對齊
- `tests/test_validate_state_gate.py` - Ruff import/format 修正
- `scripts/service_manager.sh` - 修正可執行權限與 PTY fallback 行為

- `.devcontainer/devcontainer.json` - 修改（dev deps + local extension install）
- `.devcontainer/devcontainer.ghcr.json` - 修改（dev deps + local extension install）
- `.idx/dev.nix` - 修改（安裝 dev deps）

- `scripts/portable/verify_restore_state.py` - 修改（補齊 restore 差異檢查）
- `scripts/portable/README.md` - 修改（補充 local extension/restore 說明）

- `scripts/portable/bootstrap.sh` - chmod +x
- `scripts/portable/bootstrap_linux.sh` - chmod +x
- `scripts/portable/bootstrap_macos.sh` - chmod +x
- `scripts/portable/install_extensions.sh` - chmod +x
- `scripts/vscode/install_terminal_orchestrator.sh` - chmod +x

### Done 定義
1. ✅ Ruff / Pytest / restore verifiers 結果在 Idx-032 log 可稽核。
2. ✅ 變更已 commit 並 push 至 `origin/feature/idx-024-clear-on-pass`。

### Rollback 策略
- **Level**: L2
- **回滾動作**:
  - `git restore --worktree --staged -- .`
  - 針對新增檔：`git clean -fd -- .agent/plans/Idx-032_plan.md .agent/logs/Idx-032_log.md`

### Max rounds
- **估計**: 1
- **超過處理**: 若 restore/check 需新增更多檔案到白名單，先停下來請你確認擴 scope。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| .devcontainer/devcontainer.json | 修改 | uv sync 安裝 dev extra + 自動安裝 local extension |
| .devcontainer/devcontainer.ghcr.json | 修改 | 同上（GHCR template） |
| .idx/dev.nix | 修改 | onCreate 安裝 requirements-dev |
| scripts/service_manager.sh | 修改 | 支援 --pty + 自動 fallback；並修正可執行權限 |
| scripts/portable/verify_restore_state.py | 修改 | 加強 restore 差異檢查（dev deps/local extension/腳本權限） |
| scripts/portable/README.md | 修改 | 更新一鍵恢復說明 |
| scripts/portable/*.sh | 修改 | chmod +x |
| scripts/vscode/install_terminal_orchestrator.sh | 修改 | chmod +x |
| tests/*.py | 修改 | Ruff format / import block 修正 |

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-01-23T06:37:39+00:00
plan_approved: 2026-01-23T06:37:39+00:00
scope_policy: strict
expert_required: false
expert_conclusion: N/A
scope_exceptions: ["本次為 /dev 治理收斂（健康檢查 + restore 同步），允許直接在此環境修測試/腳本/Dev Container 設定以達到可重現狀態"]

# Engineer 執行
executor_tool: manual
executor_tool_version: N/A
executor_user: GitHub Copilot (VS Code)
executor_start: 2026-01-23T06:37:39+00:00
executor_end: [TBD]
session_id: N/A
last_change_tool: manual

# QA 執行
qa_tool: manual
qa_tool_version: N/A
qa_user: GitHub Copilot (VS Code)
qa_start: [TBD]
qa_end: [TBD]
qa_result: [TBD]
qa_compliance: ⚠️ 例外：本次為 repo 內建驗證（ruff/pytest/restore scripts）自動化驗證為主，未切換 codex/opencode

# 收尾
log_file_path: .agent/logs/Idx-032_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 用戶確認

- [x] 以 `/dev` 啟動並要求執行 Ruff/Pytest + extensions/restore 同步
