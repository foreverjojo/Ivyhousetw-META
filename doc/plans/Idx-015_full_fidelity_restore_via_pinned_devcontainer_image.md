# Plan: Idx-015

**Index**: Idx-015
**Created**: 2026-01-17
**Planner**: Codex CLI (restore gap analysis)
**Predecessor**: Idx-014_one_click_restore_reproducibility_hardening.md

---

## 🎯 目標

把「一鍵恢復」從「幾乎一樣」提升到「容器內環境可達到近乎 bit-identical」的等級（仍排除 VS Code Settings Sync 的全域層），避免因上游 image / apt / 下載腳本變動導致新機器與舊機器產生差異。

---

## 📋 SPEC

### Goal
讓新電腦的 Dev Container 使用「已建置並固定 digest」的容器映像，達成：
- OS layer（容器 base image）固定
- 系統套件層固定（在 build 時鎖定）
- Python/Node tooling 固定
- `uv.lock` 依賴固定（`uv sync --frozen`）

### Non-goals
- ❌ 不做：VS Code 全域 profile / keybindings / snippets（由 Settings Sync 處理）
- ❌ 不做：自動搬運 secrets（仍採 `${localEnv:...}` 注入）

### Acceptance Criteria
1. ✅ Dev Container 改為使用 `ghcr.io/<owner>/<repo>-devcontainer@sha256:<digest>`（或同等固定 digest 的 image）
2. ✅ CI 產出並發佈該 image（每次 `.devcontainer/**` 或 toolchain 變動時）
3. ✅ 新機器只需 clone repo + Reopen in Container，就能使用相同 digest image（容器層一致）
4. ✅ `scripts/portable/verify_restore_state.py` 額外檢查「devcontainer image digest」是否為預期值（或至少顯示目前值供人工核對）

### Edge cases
- 未登入 GitHub Container Registry / rate limit：需文件提供登入方式（`docker login ghcr.io`）
- 私有 repo：需處理 token 權限（read:packages）

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: true

### Sources
- GitHub Container Registry (GHCR) 官方文件（需在執行前補上 URL）
- VS Code Dev Containers：使用 `image` vs `build` 的官方文件（需在執行前補上 URL）
- Repo 現況：`.devcontainer/*`, `.github/workflows/devcontainer-rebuild-test.yml`

### Assumptions
- ⚠️ RISK: unverified - Repo 具備發佈 GHCR image 的權限（public 或已配置 packages 權限）
- ⚠️ RISK: unverified - 新電腦可正常 pull 影像（網路/公司防火牆/憑證）

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `.devcontainer/devcontainer.json` - 改用 `image`（固定 digest）或加入 build args 以可重現方式產生 digest
- `.github/workflows/*` - 新增/更新 workflow：build + push ghcr + 產出 digest
- `doc/ENVIRONMENT_RECOVERY.md` - 補上 ghcr 登入與 pull 的說明
- `scripts/portable/verify_restore_state.py` - 增加 digest 檢查或提示

### Done 定義
1. ✅ CI 可產出 devcontainer image 並固定 digest
2. ✅ devcontainer.json 能消費固定 digest image
3. ✅ 文件能引導新機器完成 ghcr 登入並成功 pull

### Rollback 策略
- **Level**: L2
- **回滾動作**: 將 devcontainer.json 改回 `build` 模式；保留 workflow 但停止觸發

### Max rounds
- **估計**: 2
- **超過處理**: 第 3 輪只補文件與 debug，不改 CI 流程

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `.devcontainer/devcontainer.json` | 修改 | 改用固定 digest 的 image（或導入可重現 build args） |
| `.github/workflows/build-devcontainer-image.yml` | 新增 | build + push GHCR + 寫出 digest artifact |
| `doc/ENVIRONMENT_RECOVERY.md` | 修改 | 加入 GHCR login / 常見問題 |
| `scripts/portable/verify_restore_state.py` | 修改 | 顯示/檢查預期 digest |

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
log_file_path: doc/logs/Idx-015_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

