# Idx-049 — 驗證 main push 是否自動觸發 Cloud Build 並部署 Cloud Run

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-03-06 14:05:00+00:00
plan_approved: 2026-03-06T14:05:46Z
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions:
	- 2026-03-06：使用者明確要求擴充 scope，納入 `cloudbuild.yaml` 的最小修正與第二次 main push 驗證

# Engineer 執行
executor_tool: copilot-chat
executor_backend: copilot-chat
monitor_backend: manual_confirmation
executor_tool_version: GPT-5.4
executor_user: vscode
executor_start: 2026-03-06T14:05:46Z
executor_end: 2026-03-06T14:29:51Z
session_id: [terminal session ID if available]
last_change_tool: copilot-chat

# Copilot Chat 小修正政策（僅當 executor_tool=copilot-chat 才允許填；其餘 executor 保持 placeholder）
copilot_chat_small_fix_allowed: true
copilot_chat_small_fix_reason: 單一部署設定檔最小修正 + 直接驗證 Cloud Build / Cloud Run
copilot_chat_max_changed_lines: 40
copilot_chat_allowed_path_globs: ["cloudbuild.yaml", "CHANGELOG.md", "CHECKLIST.md", "README.md", "doc/**", ".agent/**"]

# QA 執行
qa_tool: opencode
qa_tool_version: N/A
qa_user: vscode
qa_start: 2026-03-06T14:07:51Z
qa_end: 2026-03-06T14:29:51Z
qa_result: PASS_WITH_RISK
qa_compliance: ⚠️ 例外：以 GCP CLI 直接驗證 trigger/build/deploy 結果，未經 OpenCode 終端產生獨立審查輸出；技術結果已完成端到端驗證

# 收尾
log_file_path: .agent/logs/Idx-049_log.md
commit_hash: pending
rollback_at: [N/A|YYYY-MM-DD HH:mm:ss]
rollback_reason: [N/A|原因]
rollback_files: [N/A|檔案清單]
<!-- EXECUTION_BLOCK_END -->

---

## 📋 SPEC

### Goal
先以極小 commit 驗證 `main` push 會自動觸發 Cloud Build，再針對第一輪驗證暴露出的單一 `cloudbuild.yaml` 問題做最小修正，並以該修正 commit 再次 push 到 `main`，完成 Cloud Build 與 Cloud Run 自動部署驗證；同時留下可稽核的操作紀錄與回滾方案。

### Non-goals
- ❌ 不修改任何應用程式執行邏輯、依賴版本或非必要設定。
- ❌ 不順手修其他文件、測試或額外部署問題。
- ❌ 不在本任務中調整 trigger、IAM 或 Cloud Run 服務參數；僅修正 `cloudbuild.yaml` 中已驗證的 substitution 展開問題。

### Acceptance Criteria
1. ✅ 第一輪驗證已證明 `git push origin main` 會觸發 Cloud Build trigger。
2. ✅ `cloudbuild.yaml` 的 `AUTH_FLAG` substitution 問題完成最小修正，且 diff 聚焦於單一部署設定檔。
3. ✅ 修正 commit push 到 `main` 後，Cloud Build 產生新的 build 執行紀錄。
4. ✅ 第二輪 build 成功完成，並產生 `ivyhouse-meta-analyzer` 的 Cloud Run service/revision，或明確收斂出新的 deploy 阻塞原因。
5. ✅ 產出可供使用者自行檢視的入口：build log 位置、trigger 位置、Cloud Run revision 位置。

### Edge cases
- `main` 在執行前有新 commit → 先 fast-forward/update 後再做最小修正 commit，避免非快轉 push 失敗。
- 修正後 trigger 有觸發但 build 仍失敗 → 任務仍需完成收斂，記錄新的失敗點與對應 log 位置，不追加第三次 commit。
- build 成功但 deploy 失敗 → 視為 trigger 驗證成功、auto-deploy 未完成，需在 log 明確區分。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- 使用者提供的 trigger 建立輸出：`Created [https://cloudbuild.googleapis.com/v1/projects/ivyhouse-ad-analyzer/locations/asia-east1/triggers/a863974b-ba4a-4a80-aea4-b60517589a4b]`
- repo 既有部署檔：`cloudbuild.yaml`
- repo workflow 規範：`.agent/workflows/AGENT_ENTRY.md`, `.agent/workflows/dev-team.md`, `ivy_house_rules.md`

### Assumptions
- ✅ VERIFIED - 目前 worktree 乾淨，適合做最小 commit 驗證。
- ⚠️ RISK: unverified - Cloud Build trigger 建立成功後，實際 build/deploy 仍可能因執行身分或 Cloud Run 權限而失敗。
- ✅ VERIFIED - 文件變更也會進入 Docker build context，因此足以驗證 trigger 與部署鏈路。
- ✅ VERIFIED - 第一輪失敗由 `cloudbuild.yaml` 中 `${AUTH_FLAG}` 被 Cloud Build 誤當 substitution key 造成。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `.agent/Workflow_Plan_index.md` - 登記 Idx-049
- `.agent/plans/Idx-049_plan.md` - 本計畫文件
- `.agent/logs/Idx-049_log.md` - 執行紀錄與第二輪驗證結果
- `CHANGELOG.md` - 第一輪最小測試 commit 載體（已完成）
- `cloudbuild.yaml` - 第二輪最小修正檔案

### Done 定義
1. ✅ `main` 上存在一個可追溯的最小測試 commit。
2. ✅ 已完成 `cloudbuild.yaml` 最小修正並 push 到 `main`。
3. ✅ 已確認第二輪 build/deploy 的最終結果。
4. ✅ 已回填 Idx-049 log，包含兩次 commit hash、觀察結果、風險與查看入口。

### Rollback 策略
- **Level**: L3
- **前置條件**: 驗證 commit 或修正 commit 已推送到 `main`，且需保留審計紀錄。
- **回滾動作**: 若需撤回測試文件變更或部署修正，使用 `git revert <commit-hash>` 產生反向 commit；不得重寫 `main` 歷史。

### Max rounds
- 2 rounds（第一輪驗證已完成；第二輪為單一修正 + 一次 QA/觀察，若仍失敗則停在分析）

---

## 📁 檔案變更表

| 檔案 | 動作 | 說明 |
|------|------|------|
| `.agent/Workflow_Plan_index.md` | 修改 | 登記 Idx-049 任務 |
| `.agent/plans/Idx-049_plan.md` | 新增 | 本 Plan |
| `.agent/logs/Idx-049_log.md` | 新增 | 執行後記錄 build/deploy 結果 |
| `CHANGELOG.md` | 修改 | 極小、非功能性的測試 commit（建議 1~2 行） |
| `cloudbuild.yaml` | 修改 | 修正 `AUTH_FLAG` 在 Cloud Build 中的 substitution 展開方式 |

---

## 📝 執行步驟（給 Engineer）

### 1) 前置同步
- 切換到 `main`，確認 `origin/main` 為最新。
- 確認 worktree 乾淨且沒有未提交檔案。

### 2) 製作最小測試 commit
- 僅修改 `CHANGELOG.md` 一小段驗證標記，例如加入一行「驗證 Cloud Build trigger on main」。
- commit message 建議：`chore(Idx-049): validate main trigger deployment`

### 3) 修正 `cloudbuild.yaml`
- 僅修正 deploy step 中 `AUTH_FLAG` 的展開方式，避免 Cloud Build 將 shell 變數誤判為 substitution key。
- commit message 建議：`fix(cloudbuild): escape AUTH_FLAG substitution`

### 4) Push 並觀察 trigger
- `git push origin main`
- 觀察 trigger 是否在 Cloud Build 中生成新的 build。

### 5) 收集結果
- 若 build 成功：確認 Cloud Run 服務是否產生新的 revision。
- 若 build 或 deploy 失敗：擷取錯誤摘要與 build ID，停止進一步變更。

---

## 🧪 QA 檢核（給 QA）

- `git show --stat --oneline HEAD`
- 確認第二輪產品變更只包含 `cloudbuild.yaml` 的最小修正。
- 確認 Cloud Build 有對應 build 紀錄。
- 確認 Cloud Run revisions 中有對應新 revision，或明確記錄 deploy 失敗原因。

---

## ✅ 用戶確認（Gate）

- [ ] Spec 已確認，可進入執行
- [ ] 已選 Engineer Tool（建議：`opencode`）
- [ ] 已選 QA Tool（建議：`codex-cli`）
- [ ] 已確認最小 commit 只允許動 `CHANGELOG.md`
