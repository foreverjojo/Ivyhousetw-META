# Task Execution Log

**Index**: Idx-052
**Plan Version**: 2026-03-08-v1
**Task Description**: Testing 小範圍使用：主管帳號開通與 access runbook 收斂

---

## Metadata

- **Start Time**: 2026-03-08 05:00:09 UTC
- **End Time**: 2026-03-08 05:10:00 UTC
- **Engineer**: opencode（Plan 指定；已完成 preflight 與 workflow 注入）
- **QA**: codex-cli（Plan 指定；已完成 cross-QA）
- **Duration**: 約 10 分鐘

---

## 🔧 Execution Information

**Execution Tool**: opencode
**Execution Start**: 2026-03-08 05:05 UTC
**Execution End**: 2026-03-08 05:10 UTC
**Exit Code**: 0

---

## Objective

- 在不推進 production 的前提下，將本次確認的 3 位主管帳號完整納入 Testing 小範圍使用名單。
- 補齊 Google Auth Platform `test users` 與 IAP allowlist。
- 產出一份短 runbook，讓後續新增主管時可依相同步驟維護。

---

## Key Changes

### Files Created
- `doc/plans/Idx-052_plan.md` - 本任務正式計畫
- `doc/testing_small_scope_runbook.md` - Testing 小範圍使用短 runbook
- `doc/logs/Idx-052_log.md` - 本次執行紀錄

### Files Modified
- `doc/Implementation_Plan_index.md` - 登記 Idx-052 任務

### Live Config Updated
- Google Auth Platform `目標對象 > 測試使用者`
- IAP backend service `ivyhouse-meta-iap-backend` IAM policy

---

## Implementation Details

### 1. Workflow Gate 與 preflight
- 完成 `/dev` 必要的 `READ_BACK_REPORT`。
- 建立 `Idx-052` 計畫並經使用者明確 `approved`。
- 使用者選定：Engineer = `opencode`、QA = `codex-cli`、Monitor = `proposed-primary-with-extension-fallback`。
- 因使用者明確同意 HTTP SendText Bridge，本輪執行：

```bash
python scripts/vscode/workflow_preflight_check.py --require-bridge --json
```

- 結果：`status = pass`

### 2. Google Auth Platform 測試使用者補齊
- 進入 `Google Auth Platform > 目標對象`。
- 原始狀態：僅有 `foreverwow001@gmail.com` 1 位測試使用者。
- 新增以下 3 位主管帳號：
  - `ivyhousetw@gmail.com`
  - `foreverjojo@gmail.com`
  - `maomaohappymeow@gmail.com`
- 儲存後頁面顯示：`4 位使用者 (4 位測試使用者，0 位其他使用者)`。

### 3. IAP allowlist 補齊
- 初始查詢顯示 IAP allowlist 含：
  - `user:foreverwow001@gmail.com`
  - `user:ivyhousetw@gmail.com`
  - `user:foreverjojo@gmail.com`
  - `serviceAccount:971489052398-compute@developer.gserviceaccount.com`
- 補上最後缺口：

```bash
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=ivyhouse-meta-iap-backend \
  --member='user:maomaohappymeow@gmail.com' \
  --role='roles/iap.httpsResourceAccessor' \
  --project=ivyhouse-ad-analyzer
```

- 最終查詢結果包含：
  - `user:foreverwow001@gmail.com`
  - `user:ivyhousetw@gmail.com`
  - `user:foreverjojo@gmail.com`
  - `user:maomaohappymeow@gmail.com`
  - `serviceAccount:971489052398-compute@developer.gserviceaccount.com`

### 4. Access inventory 結論
- 使用者已明確確認本次 3 個 email 即為全部主管帳號。
- 完成雙層名單補齊後，本次範圍的 access gap = 0。

### 5. 文件化
- 新增 `doc/testing_small_scope_runbook.md`，整理：
  - `External / 測試` 模式下的維護原則
  - 新增主管必補的兩個地方
  - 驗證與移除步驟
  - 目前正式維護名單

---

## Decisions Made

| 決策點 | 選擇方案 | 理由 | 替代方案 |
|--------|---------|------|---------|
| 小範圍維運文件位置 | 新增獨立短 runbook | 讓日常維護清單與大型總 runbook 分離，較容易查找 | 直接擴寫 `doc/RUNBOOK.md` |
| Testing 名單維護模型 | `test users` + IAP allowlist 雙層同步 | 符合目前 `External / 測試` 的實際限制 | 只維護 IAP allowlist（不足） |

---

## Challenges & Solutions

### Challenge 1: Google Auth Platform `test users` 缺少 CLI 管理路徑
**Solution**: 直接透過 Console `目標對象` 頁面完成新增與驗證。

### Challenge 2: IAP allowlist 一度只補到 2 位主管帳號
**Solution**: 直接以 `gcloud iap web add-iam-policy-binding` 補齊 `user:maomaohappymeow@gmail.com`，再重新查詢 IAM policy 驗證。

---

## 🔄 Rollback Records

| Level | Timestamp | Reason | Action | Result |
|-------|-----------|--------|--------|--------|
| - | - | - | - | - |

**Rollback Summary**: 無

---

## 🛠️ SKILLS_EXECUTION_REPORT

| Skill | Target | Status | Summary | Timestamp |
|-------|--------|--------|---------|-----------|
| `workflow_preflight_check.py` | `Idx-052 bridge path` | `pass` | Proposed API 與 SendText Bridge 健康檢查通過 | 2026-03-08 05:04:38 UTC |

---

## QA Status

- **Status**: ⚠️ PASS WITH RISK
- **QA Date**: 2026-03-08
- **QA Notes**:
  - 已以 `codex-cli` focused review 檢查 `doc/Implementation_Plan_index.md`、`doc/plans/Idx-052_plan.md`、`doc/logs/Idx-052_log.md`、`doc/testing_small_scope_runbook.md`。
  - QA 曾指出 Index / Log / Runbook 狀態未完全對齊；本輪已完成回填修正。
  - 修正後再以 `codex-cli` 做第二輪極短復核，結論為 `no findings`。
  - 修正後，live 狀態與文件基線一致：`test users` = 4 位、IAP allowlist = 4 個 user principals + 1 個 compute service account。
  - 保留風險僅為 `External / 測試` 模式本身的限制，以及各主管帳號實際 Google 登入可用性需在首次登入時各自驗證。
  - 2026-03-08 後續嘗試補做 3 位主管首次真人登入 smoke check 時，確認目前瀏覽器 profile 僅有 `foreverwow001@gmail.com` 已登入，另外 3 位帳號需由帳號持有人自行完成 Google 登入與可能的 OTP；使用者已接受先以「設定層驗證完成、真人首次登入待補驗」結案並進行 commit / push。

### ✅ Cross-QA Compliance

**Executor**: opencode
**QA Tool**: codex-cli *(必須與 last_change_tool 不同)*
**QA Compliance**: ✅ PASS

### Test Results
- [x] 手動設定驗證通過（Google Auth Platform `test users` = 4）
- [x] CLI 驗證通過（IAP allowlist = 4 個 user principals + 1 個 service account）
- [x] 文檔已更新
- [x] Cross-QA 規則已完成

---

## Outcome

- 3 位主管帳號已全部補入 `test users` 與 IAP allowlist。
- 目前 Testing 小範圍使用的正式主管名單已完整，缺口為 0。
- repo 內已補上一份可直接操作的短 runbook。

---

## Residual Risks

1. 目前仍是 `External / 測試`，若未來要開放更多外部帳號，仍需進入正式發布與驗證流程。
2. 帳號列入雙層名單不代表該 email 一定可完成 Google 登入；若帳號本身不可用，仍需個別排查。

---

## Next Steps

1. 由 3 位主管帳號持有人各自完成首次真人登入驗證。
2. 若後續新增或移除主管，依 `doc/testing_small_scope_runbook.md` 的雙層名單步驟操作。
3. 本輪文件變更可直接 commit / push；若後續真人登入驗證失敗，再另開新任務追蹤。

---

## References

- `doc/plans/Idx-052_plan.md`
- `doc/Implementation_Plan_index.md`
- `doc/logs/Idx-051_log.md`

---

**Log Created**: 2026-03-08
**Last Updated**: 2026-03-08
