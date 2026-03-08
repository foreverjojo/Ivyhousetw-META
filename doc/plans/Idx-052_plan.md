# Idx-052 — Testing 小範圍使用：主管帳號開通與 access runbook 收斂

**Index**: Idx-052
**Created**: 2026-03-08
**Planner**: GitHub Copilot

---

## 🎯 目標

在維持 Google Auth Platform `External / 測試` 與既有 IAP 架構不變的前提下，將本次確認的 3 位主管帳號完整加入可用名單，並整理一份可重複操作的短 runbook，讓後續小範圍使用能以固定流程維護。

---

## 📋 SPEC

### Goal
完成以下三件事：
1. 將 `ivyhousetw@gmail.com`、`foreverjojo@gmail.com`、`maomaohappymeow@gmail.com` 加入 Google Auth Platform `test users`
2. 將相同 3 個 email 加入 IAP backend (`ivyhouse-meta-iap-backend`) 的 `roles/iap.httpsResourceAccessor` allowlist
3. 在 repo 中新增或更新一份短 runbook，記錄「Testing 小範圍使用」的實務操作清單與目前 access inventory

### Non-goals
- ❌ 不將 OAuth consent screen 從 `Testing` 推進到 `Production`
- ❌ 不處理 Search Console ownership 或 brand verification
- ❌ 不更換 OAuth client、不改動 Cloud Run / Load Balancer / NEG / URL map 架構
- ❌ 不擴大開放名單到本次 3 位主管帳號以外的使用者
- ❌ 不修改應用程式業務邏輯或 UI

### Acceptance Criteria
1. ✅ Google Auth Platform `目標對象` 頁面中的 `測試使用者` 至少包含以下 4 人：
   - `foreverwow001@gmail.com`
   - `ivyhousetw@gmail.com`
   - `foreverjojo@gmail.com`
   - `maomaohappymeow@gmail.com`
2. ✅ `gcloud iap web get-iam-policy` 查詢結果中的 `roles/iap.httpsResourceAccessor` 至少包含以下 principals：
   - `user:foreverwow001@gmail.com`
   - `user:ivyhousetw@gmail.com`
   - `user:foreverjojo@gmail.com`
   - `user:maomaohappymeow@gmail.com`
   - 既有 compute service account
3. ✅ runbook 明確說明：
   - 維持 `External / 測試` 時，新增主管必須同步補的兩個地方
   - 最小驗證步驟
   - 目前已配置名單與本次範圍內無剩餘缺口
4. ✅ 完成後有一份對應的 log 記錄實際操作、驗證結果與殘餘風險

### Edge cases
- 某個 email 已存在於 `test users` 或 IAP allowlist → 視為冪等成功，不做重複新增。
- Google Auth Platform Console 無法直接修改或權限異常 → 停止新增操作，回報實際卡點與可行替代路徑。
- IAP allowlist 更新成功，但 `test users` 漏補 → 該帳號仍不應視為可用，任務不得結案。
- runbook 整理完成，但 live 名單未更新 → 視為文件完成、功能未完成，不可判定 PASS。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- repo 文件：`DEPLOY.md`
- repo 文件：`doc/RUNBOOK.md`
- repo 文件：`doc/OAUTH_CONSENT_PUBLICATION.md`
- repo 文件：`doc/logs/Idx-051_log.md`
- 2026-03-08 live 盤點：Google Auth Platform `目標對象` 頁面顯示目前僅有 1 位測試使用者 `foreverwow001@gmail.com`
- 2026-03-08 live 盤點：`gcloud iap web get-iam-policy --resource-type=backend-services --service=ivyhouse-meta-iap-backend --project=ivyhouse-ad-analyzer --format='json'`

### Assumptions
- ✅ VERIFIED - 本任務的「全部需要開放的主管帳號」就是以下 3 個 email：`ivyhousetw@gmail.com`、`foreverjojo@gmail.com`、`maomaohappymeow@gmail.com`
- ✅ VERIFIED - 目前 Google Auth Platform `test users` 只有 `foreverwow001@gmail.com`
- ✅ VERIFIED - 目前 IAP allowlist 只有 `user:foreverwow001@gmail.com` 與 `serviceAccount:971489052398-compute@developer.gserviceaccount.com`
- ✅ VERIFIED - 此任務不涉及 Meta 指標計算或 Meta API，無需 Meta Expert 專業審核
- ⚠️ RISK: unverified - 3 位主管帳號新增後，是否每一位都已具備可用的 Google 帳戶登入狀態，需在實際登入時各自驗證

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `doc/Implementation_Plan_index.md` - 登記 Idx-052 任務
- `doc/plans/Idx-052_plan.md` - 本計畫文件
- `doc/logs/Idx-052_log.md` - 執行與驗收紀錄
- `doc/RUNBOOK.md` - 若採既有 runbook 擴充，回填 Testing 小範圍使用操作清單
- `doc/OAUTH_CONSENT_PUBLICATION.md` - 若需要補充 test users / 小範圍使用操作注意事項
- `doc/testing_small_scope_runbook.md` - 若決定拆成獨立短 runbook

### Live config scope
- Google Auth Platform `目標對象 > 測試使用者`
- IAP backend service IAM policy：`ivyhouse-meta-iap-backend`

### Done 定義
1. ✅ 3 個主管 email 已同時存在於 `test users` 與 IAP allowlist
2. ✅ 名單已以頁面或 CLI 查詢重新驗證
3. ✅ 短 runbook 已落到 repo，內容足夠讓後續新增主管時可依樣操作
4. ✅ 已建立對應 log，清楚記錄本次新增名單與剩餘風險

### Rollback 策略
- **Level**: L3
- **前置條件**: 必須保留目前 `foreverwow001@gmail.com` 與 compute service account 的既有可用設定
- **回滾動作**:
  - 若新增 email 後造成誤授權或配置錯誤，從 Google Auth Platform `test users` 與 IAP IAM policy 移除新增的 user principals
  - repo 文件若需回滾，使用 `git revert <commit>`，不重寫歷史

### Max rounds
- **估計**: 3 rounds（名單新增 → 驗證 → 文件與 log 回填）
- **超過處理**: 若第 3 輪後仍有任一 email 無法完成雙層名單配置，停止擴大變更並回報具體卡點

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `doc/Implementation_Plan_index.md` | 修改 | 登記 Idx-052 任務 |
| `doc/plans/Idx-052_plan.md` | 新增 | 本計畫文件 |
| `doc/logs/Idx-052_log.md` | 新增 | 記錄實際新增名單、驗證與風險 |
| `doc/RUNBOOK.md` | 修改（候選） | 補「Testing 小範圍使用」操作清單 |
| `doc/OAUTH_CONSENT_PUBLICATION.md` | 修改（候選） | 視需要補充小範圍使用維運注意事項 |
| `doc/testing_small_scope_runbook.md` | 新增（候選） | 若選擇拆成獨立短 runbook |

---

## 📝 邏輯細節

### 1. 名單新增
- 先在 Google Auth Platform `目標對象` 頁面新增 3 個主管 email 到 `測試使用者`。
- 再將相同 3 個 email 以 `user:<email>` principal 形式加入 `ivyhouse-meta-iap-backend` 的 `roles/iap.httpsResourceAccessor` binding。
- 更新時必須保留既有 `user:foreverwow001@gmail.com` 與 compute service account，不可誤覆蓋掉原 binding。

### 2. 驗證方式
- 以 Google Auth Platform `目標對象` 頁面確認 `測試使用者` 清單。
- 以 `gcloud iap web get-iam-policy` 查詢 IAP backend IAM policy，確認新增 principals 已存在。
- 如時間允許，可再以最小 smoke check 驗證 root URL 仍會 302 至 Google OAuth，且未破壞既有 IAP 流程。

### 3. runbook 整理
- 若內容短且與既有 IAP 操作相鄰，優先補在 `doc/RUNBOOK.md`。
- 若內容較偏日常營運清單，則建立獨立短文件並在 `doc/RUNBOOK.md` 或 `doc/OAUTH_CONSENT_PUBLICATION.md` 連回。
- runbook 內容至少應涵蓋：
  - 什麼情況下只補 IAP allowlist 不夠，還必須補 `test users`
  - 新增一位主管的最小步驟
  - 如何查目前名單
  - 目前正式維護名單

### 4. 缺口盤點
- 因使用者已明確確認本次 3 個 email 就是「全部需要開放的主管帳號」，盤點邏輯以這 3 人為完整基準。
- 完成新增後，若雙層名單均已包含這 3 人，則本次範圍內缺口應為 0。

---

## ⚠️ 注意事項

- **風險提示**：Google Auth Platform `Testing` 模式下，未列入 `test users` 的帳號即使在 IAP allowlist 內，仍可能無法完成登入流程。
- **風險提示**：IAP IAM policy 若用覆寫式更新且未保留既有 principals，可能導致原本可登入的人員失去存取權。
- **資安考量**：只新增本次明確核准的 3 個主管 email，不擴大到其他未知帳號。
- **相依性**：本任務依賴目前 Google Cloud Console 與 gcloud 權限足以修改 Auth Platform audience 與 IAP IAM policy。

---

## 🔗 相關資源

- `doc/plans/Idx-051_plan.md`
- `doc/logs/Idx-051_log.md`
- `DEPLOY.md`
- `doc/RUNBOOK.md`
- `doc/OAUTH_CONSENT_PUBLICATION.md`

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-03-08 05:00:09 UTC
plan_approved: 2026-03-08 05:00:09 UTC
scope_policy: strict
expert_required: false
expert_conclusion: 此任務不涉及數據分析，跳過專家審核
execution_backend_policy: extension-sendtext-required
scope_exceptions: ["使用者已明確同意本輪採 HTTP SendText Bridge 將指令送至既有 OpenCode / Codex 終端"]

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: proposed_api_monitor
executor_tool_version: N/A
executor_user: foreverwow001@gmail.com
executor_start: 2026-03-08 05:05:43 UTC
executor_end: 2026-03-08 05:10:00 UTC
session_id: wf_20260308050542_551f5c
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: OpenAI Codex v0.111.0
qa_user: foreverwow001@gmail.com
qa_start: 2026-03-08 05:12:00 UTC
qa_end: 2026-03-08 05:15:00 UTC
qa_result: PASS_WITH_RISK
qa_compliance: ✅ 符合

# 收尾
log_file_path: [doc/logs/Idx-052_log.md]
commit_hash: [pending|hash]
rollback_at: [N/A|YYYY-MM-DD HH:mm:ss]
rollback_reason: [N/A|原因]
rollback_files: [N/A|檔案清單]
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 用戶確認

> 🛑 **必要停頓點**：Planner 產出 Spec 後，必須等待用戶確認才能進入 Step 2。

- [x] Spec 已確認，可進入 Step 2（Meta Expert 已判定可略過）
- [x] Engineer Tool 已選擇：`opencode`
- [x] QA Tool 已選擇：`codex-cli`（必須 ≠ last_change_tool）
- [x] Execution Backend Policy 已確認：`extension-sendtext-required`（本輪另有使用者明確同意 HTTP SendText Bridge）
- [x] Monitor Backend Policy 已確認：`proposed-primary-with-extension-fallback`
- [x] Terminal 管理策略已確認
