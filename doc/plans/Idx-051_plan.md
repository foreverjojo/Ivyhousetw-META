# Idx-051 — 方案 A：以 Google 前置身分保護私有 Cloud Run 網站入口

**Index**: Idx-051
**Created**: 2026-03-06
**Planner**: GitHub Copilot

---

## 🎯 目標

將目前「私有 Cloud Run 只能靠 local token / impersonation 測試」的存取模式，改為「使用者以瀏覽器開啟網址後，先經 Google 身分驗證，再進入私有服務」，而不在應用程式內自建 login 頁、帳密系統或 user database。

---

## 📋 SPEC

### Goal
建立一個以 Google 前置身分保護為核心的最小可行架構，讓 `ivyhouse-meta-analyzer` 維持私有 Cloud Run，但能以瀏覽器登入方式供授權使用者存取，不再依賴本地 CLI token 流程。

本計畫的官方 research 結論：
- **原第一優先（理論上最簡）**：直接在 Cloud Run 上啟用 IAP（官方文件標示為 Preview）。
- **實際執行結果**：此專案不屬於任何 organization，已被 direct IAP 官方前提阻塞，因此本任務已正式切換到 `External HTTPS Load Balancer + Serverless NEG + IAP`。
- **已驗證 MVP 路線**：`Global External HTTPS Load Balancer + Serverless NEG + IAP` 可在本專案落地，並已成功回傳 IAP 302 與帶 token 的 HTTP 200；但 2026-03-07 真人瀏覽器驗收顯示目前使用的 generic OAuth client 仍不足以完成最終 browser login。

### Non-goals
- ❌ 不改為方案 B（不把 Cloud Run 改成公開入口 + app 內登入）。
- ❌ 不在 Streamlit app 內建立自有 login 頁、session auth、密碼管理或 user database。
- ❌ 不在本任務中擴充多角色 RBAC、註冊/邀請流程或完整會員系統。
- ❌ 不在本任務中重構應用核心頁面流程、資料模型或顧問邏輯。

### Acceptance Criteria
1. ✅ `ivyhouse-meta-analyzer` 仍維持私有 Cloud Run，不開放匿名呼叫。
2. ✅ 授權使用者可透過瀏覽器路徑登入 Google 身分後，直接進入應用首頁，不需手動產生 token 或在 local 代理。
3. ✅ 未授權使用者無法進入應用；存取控制由 Google 前置身分層處理，而非 app 內頁面 gate。
4. ✅ repo 內新增或更新部署/操作文件，明確說明 GCP 架構、設定步驟、最小 IAM、驗收方式與 rollback。
5. ✅ 驗收時可明確區分三種結果：未登入、已登入但未授權、已授權可進入應用。

### Edge cases
- Cloud Run 仍為私有，但前置保護層配置不完整 → 會導致登入後仍 403/502；需先以架構驗證清單逐層排除。
- 使用者帳號不在 allowlist / Google 群組內 → 應停在 Google 前置授權層，不應落到 app 內再顯示自製拒絕頁。
- 自訂網域或負載平衡器未完成 TLS / DNS → 驗收時可先接受 Google 提供的 LB 網址，但不可回退到公開 Cloud Run。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: true

### Sources
- repo 既有部署文件：`DEPLOY.md`
- repo 雲端整合文件：`doc/CLOUD_INTEGRATION.md`
- 目前部署設定：`cloudbuild.yaml`
- 已驗證現況：`ivyhouse-meta-analyzer` 已成功部署至私有 Cloud Run，匿名/未帶正確 token 請求會回 401。
- Google 官方文件：`https://docs.cloud.google.com/iap/docs/enabling-cloud-run`
- Google 官方文件：`https://docs.cloud.google.com/load-balancing/docs/negs/serverless-neg-concepts`
- Google 官方文件：`https://docs.cloud.google.com/run/docs/securing/ingress`

### Assumptions
- ✅ VERIFIED - 目前服務已在 Cloud Run 正常啟動，問題是「瀏覽器可用的授權入口」而非應用本身無法啟動。
- ✅ VERIFIED - `cloudbuild.yaml` 目前預設 `_ALLOW_UNAUTH=false`，符合「維持私有 Cloud Run」的方向。
- ✅ VERIFIED - 官方文件目前**推薦**直接在 Cloud Run 上啟用 IAP；但 direct IAP on Cloud Run 要求 project 必須屬於 organization，本專案不符合此前提。
- ✅ VERIFIED - 若走 Load Balancer 路線，Cloud Run 應使用 `Internal and Cloud Load Balancing` ingress，並可考慮停用預設 `run.app` URL，避免繞過前置保護層。
- ✅ VERIFIED - 若走 IAP behind LB 路線，必須授予 `service-[PROJECT_NUMBER]@gcp-sa-iap.iam.gserviceaccount.com` 對後端 Cloud Run 的 `Cloud Run Invoker`。
- ✅ VERIFIED - IAP 與 Cloud CDN 不相容，且啟用 IAP 會增加延遲。
- ✅ VERIFIED - `gcloud iap oauth-brands create` 在本專案會回 `Project must belong to an organization`，再次證實舊 IAP brand/client API 路線不可行。
- ✅ VERIFIED - `gcloud alpha iam oauth-clients` 可在本專案建立 generic OAuth client 與 credential，IAP backend service 也接受該 client id/secret。
- ✅ VERIFIED - 以 `https://iap.googleapis.com/v1/oauth/clientIds/<CLIENT_ID>:handleRedirect` 作為 redirect URI 後，IAP 入口會對未登入請求回 302 至 Google OAuth，且對帶正確 OIDC token 的請求回 200。
- ⚠️ RISK: verified - 2026-03-07 真人瀏覽器驗收顯示目前 generic OAuth client 在 Google Accounts 回 `invalid_client`；最終 browser login 仍需 customer-owned OAuth consent screen client。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `doc/Implementation_Plan_index.md` - 登記 Idx-051 任務
- `doc/plans/Idx-051_plan.md` - 本計畫文件
- `doc/logs/Idx-051_log.md` - 完成後新增執行與驗收紀錄
- `DEPLOY.md` - 補方案 A 的部署/驗收步驟
- `doc/CLOUD_INTEGRATION.md` - 補前置身分保護架構與安全邊界
- `doc/RUNBOOK.md` - 補登入/授權失敗的排查與操作指引（若執行時確認需要）

### Done 定義
1. ✅ 已選定並記錄方案 A 的最小可行 GCP 架構，不混入方案 B，且明確區分 direct IAP 與 LB+NEG+IAP 的採用條件。
2. ✅ 已完成文件化的部署步驟、IAM/授權設計、驗收方式與 rollback。
3. ✅ 實作完成後，授權使用者可在瀏覽器中登入並進入私有應用，不需 local token。

### Rollback 策略
- **Level**: L3
- **前置條件**: 所有 infra 變更都必須可審計，且 Cloud Run 服務本身仍維持 private。
- **回滾動作**:
  - 停用/移除前置保護層（如 IAP / Load Balancer backend 綁定），恢復到目前「僅可由 CLI token 測試」的私有 Cloud Run 狀態。
  - repo 內文件若已更新，使用 `git revert <commit>` 回滾，不重寫歷史。

### Max rounds
- **估計**: 3 rounds（架構確認 → GCP 設定與文件落地 → 驗收與修正）
- **超過處理**: 若第三輪仍未完成瀏覽器登入流，停止新增變更，回報卡點並要求補官方文件或縮小實作範圍。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `doc/Implementation_Plan_index.md` | 修改 | 登記 Idx-051 任務 |
| `doc/plans/Idx-051_plan.md` | 新增 | 方案 A 正式計畫 |
| `doc/logs/Idx-051_log.md` | 新增 | 執行完成後記錄架構、驗收與風險 |
| `DEPLOY.md` | 修改 | 補私有 Cloud Run + Google 前置身分保護部署步驟 |
| `doc/CLOUD_INTEGRATION.md` | 修改 | 補安全入口架構與邊界說明 |
| `doc/RUNBOOK.md` | 修改（條件式） | 補授權失敗、401/403、IAP/LB 排查手冊 |
| `scripts/setup_cloud_run_iap_entry.sh` | 新增 | 可重跑的 LB + IAP 建置腳本，避免後續手動重建 |

---

## 📝 邏輯細節

### 1. 架構決策
- 維持 Cloud Run private，不允許匿名存取。
- 將「誰可進入應用」的責任交給 Google 前置身分保護層，而不是交給 Streamlit app 自己處理。
- app 保持無自建 login 頁，避免把安全邊界下沉到應用層。
- direct IAP on Cloud Run 已於實作前被正式排除，原因是此 project 無 organization parent，不符合官方 direct IAP 前提。
- 本任務已採用 **External HTTPS Load Balancer + Serverless NEG + IAP** 作為實際落地方案。

### 2. 最小可行路線
- 以 Google 前置登入層作為單一入口。
- **已執行路線**：建立 `Global External HTTPS Load Balancer`，後端以 `serverless NEG` 指向 `ivyhouse-meta-analyzer`，並在 backend service 啟用 IAP。
- OAuth client 不再使用舊 IAP brand/client API，而是使用 generic OAuth client API 建立 custom client，再把 redirect URI 更新為 IAP 實際使用的 `handleRedirect`。
- 以 allowlist 的 Google 帳號或 Google 群組作為第一版授權模型，不導入 user database。
- Cloud Run 已收斂為 `internal-and-cloud-load-balancing` ingress，避免從 `run.app` 直接繞過前置入口。

### 3. 文件與操作面
- 在 `DEPLOY.md` 補充：
  - 需要啟用/配置的 GCP 元件
  - direct IAP 與 LB+NEG+IAP 的決策準則
  - 最小 IAM / principal 綁定
  - 驗收步驟（未登入 / 未授權 / 已授權）
- 在 `doc/CLOUD_INTEGRATION.md` 補充：
  - 為何方案 A 比方案 B 更符合本專案的安全目標
  - 為何不需要 app 內 login 頁與 user database
  - 若採 LB 路線，Cloud Run ingress 與預設 URL 應如何限制以避免繞過 IAP

### 4. 驗收策略
- Case 1: 未登入使用者 → 先被導向 Google 登入或停在前置保護頁。
- Case 2: 已登入但未授權 → 由 Google 前置授權層拒絕。
- Case 3: 已登入且授權 → 成功進入 `ivyhouse-meta-analyzer` Streamlit 首頁。

### 5. 本輪實測結果
- 未帶憑證請求 `https://34.95.93.163/`：HTTP 302，並導向 `accounts.google.com`，其中 `redirect_uri` 已確認為 `https://iap.googleapis.com/v1/oauth/clientIds/a5889775f-e34f-481b-b30f-9ab52de675bc:handleRedirect`。
- 帶 `aud=a5889775f-e34f-481b-b30f-9ab52de675bc` 且含 `email` claim 的 impersonated service account OIDC token 請求 `https://34.95.93.163/`：HTTP 200，成功回傳 Streamlit HTML。
- 直接外部請求既有 `run.app` URL：在 ingress 收斂後回 HTTP 404，不再能作為對外入口繞過 LB。

---

## ⚠️ 注意事項

- **風險提示**：方案 A 的安全性較高，但部署複雜度高於方案 B；若缺少官方對照文件，容易在 GCP 設定細節上卡住。
- **風險提示**：direct IAP 雖是官方推薦的簡化路徑，但目前為 Preview；若你不接受 Preview 進正式入口，應直接採 LB+NEG+IAP。
- **決策記錄**：使用者已接受 direct IAP 的 Preview 狀態，作為本任務第一執行路徑。
- **資安考量**：不得為了簡化流程而把 Cloud Run 改成公開，或把登入責任下放到 app 層假登入頁。
- **相依性**：此任務高度依賴 GCP 身分保護產品能力與 IAM 設定，不只是 repo 內程式碼改動。

---

## 🔗 相關資源

- `DEPLOY.md`
- `doc/CLOUD_INTEGRATION.md`
- `cloudbuild.yaml`

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-03-06 16:22:00+00:00
plan_approved: 2026-03-06T16:21:55Z
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: manual_confirmation
executor_tool_version: N/A
executor_user: vscode
executor_start: 2026-03-06T16:22:00Z
executor_end: 2026-03-06T16:53:51Z
session_id: [terminal session ID if available]
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: N/A
qa_user: vscode
qa_start: 2026-03-07T16:24:00Z
qa_end: 2026-03-07T17:16:24Z
qa_result: FAIL
qa_compliance: ✅ 已以 codex-cli 完成 formal cross-QA；但 2026-03-07 真人瀏覽器驗收發現 live browser login 仍被 `invalid_client` 阻塞

# 收尾
log_file_path: doc/logs/Idx-051_log.md
commit_hash: [pending|hash]
rollback_at: [N/A|YYYY-MM-DD HH:mm:ss]
rollback_reason: [N/A|原因]
rollback_files: [N/A|檔案清單]
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 用戶確認

> 🛑 **必要停頓點**：Planner 產出 Spec 後，必須等待用戶確認才能進入 Step 2。

- [ ] Spec 已確認，可進入 Step 2（若需要再補官方文件 research）
- [x] Engineer Tool 已選擇：`opencode`
- [x] QA Tool 已選擇：`codex-cli`（必須 ≠ last_change_tool）
- [x] Execution Backend Policy 已確認：`extension-sendtext-required`
- [x] Monitor Backend Policy 已確認：`manual_confirmation`
- [x] 已確認本任務不改做方案 B 或 app 內 login/user database
