# Task Execution Log

**Index**: Idx-051
**Plan Version**: 2026-03-06-v1
**Task Description**: 方案 A：以 Google 前置身分保護私有 Cloud Run 網站入口

---

## Metadata

- **Start Time**: 2026-03-06 16:22:00 UTC
- **End Time**: 2026-03-07 17:16:24 UTC
- **Engineer**: opencode（依 Plan 工具選擇）
- **QA**: codex-cli（Plan 指定；已完成 formal cross-QA）
- **Duration**: 多輪執行，含 2026-03-07 的修正與 cross-QA 收尾

---

## 🔧 Execution Information

**Execution Tool**: opencode
**Execution Start**: 2026-03-06 16:22 UTC
**Execution End**: 2026-03-06 16:53 UTC
**Exit Code**: 0

---

## Objective

- 讓 `ivyhouse-meta-analyzer` 維持 private Cloud Run，但可由瀏覽器先經 Google 身分驗證後再進入首頁。
- 不改做公開 Cloud Run，也不在 Streamlit app 內自建 login 頁或 user database。

---

## Key Changes

### Files Created
- doc/logs/Idx-051_log.md - 本任務 Log
- doc/plans/Idx-051_plan.md - 正式計畫文件
- scripts/setup_cloud_run_iap_entry.sh - 可重跑入口建置腳本

### Files Modified
- doc/Implementation_Plan_index.md - 更新 Idx-051 狀態與 log 路徑
- doc/plans/Idx-051_plan.md - 補 direct IAP blocker、腳本治理與 QA 狀態
- DEPLOY.md - 補私有入口的實際部署方式與驗收指令
- doc/CLOUD_INTEGRATION.md - 補 Cloud Run 網站入口架構、IAP 權限與 OAuth client 注意事項
- doc/RUNBOOK.md - 補 IAP / Load Balancer 排查與重建步驟

---

## Implementation Details

1. direct IAP on Cloud Run 正式排除
- 官方文件要求 project 必須屬於 organization。
- 本專案 `ivyhouse-ad-analyzer` 無 organization parent。
- `gcloud iap oauth-brands create` 實測回 `Project must belong to an organization`。

2. fallback 路線驗證成功
- 建立 `Global External HTTPS Load Balancer + Serverless NEG + IAP`。
- 建立 generic OAuth client 與 credential，IAP backend service 成功接受該 client id / secret。
- 從 IAP 302 實測反推出正確 redirect URI：
  - `https://iap.googleapis.com/v1/oauth/clientIds/a5889775f-e34f-481b-b30f-9ab52de675bc:handleRedirect`
- 更新 OAuth client redirect URI 後，未登入請求會正確 302 到 Google OAuth。

3. 實際建立的 GCP 驗證資源
- Global static IP: `ivyhouse-meta-iap-ip` → `34.95.93.163`
- SSL certificate: `ivyhouse-meta-iap-cert`（self-managed / self-signed）
- Serverless NEG: `ivyhouse-meta-iap-neg`
- Backend service: `ivyhouse-meta-iap-backend`
- URL map: `ivyhouse-meta-iap-map`
- Target HTTPS proxy: `ivyhouse-meta-iap-proxy`
- Forwarding rule: `ivyhouse-meta-iap-fr`

4. 權限與硬化
- 建立 IAP service identity：`service-971489052398@gcp-sa-iap.iam.gserviceaccount.com`
- 授予該 principal `roles/run.invoker`
- 在 IAP backend service 資源層級授予下列 principal `roles/iap.httpsResourceAccessor`
  - `user:foreverwow001@gmail.com`
  - `serviceAccount:971489052398-compute@developer.gserviceaccount.com`
- 將 Cloud Run ingress 更新為 `internal-and-cloud-load-balancing`

5. 驗收結果
- 未登入請求 `https://34.95.93.163/`：HTTP 302 → `accounts.google.com`
- 帶 `aud=<IAP client id>` 且含 `email` claim 的 impersonated service account OIDC token：HTTP 200，成功回傳 Streamlit HTML
- 直接外部請求 `https://ivyhouse-meta-analyzer-dlnp2adjbq-de.a.run.app/`：在 ingress 收斂後回 HTTP 404
- 正式子網域 `https://adanalyzer.shincold.com/`：Google-managed certificate 已啟用，未登入請求回 HTTP 302 → `accounts.google.com`
- 2026-03-07 真人瀏覽器驗收：Google 直接回 `Access blocked: Authorization Error` / `The OAuth client was not found` / `Error 401: invalid_client`

6. 第 2 步腳本化
- 新增 `scripts/setup_cloud_run_iap_entry.sh`，將 LB + NEG + IAP + ingress 收斂流程做成可重跑腳本。
- 腳本不保存 OAuth client secret，改由執行時環境變數注入。
- 腳本已補齊多輪 review 修正：IAP enable idempotency、managed cert/NEG drift、global LB scope、forwarding rule / backend 收斂，以及 IAP allowlist 管理。

---

## Challenges & Solutions

### Challenge: direct IAP on Cloud Run 被 organization 條件阻塞
**Solution**: 改走 `External HTTPS Load Balancer + Serverless NEG + IAP` fallback。

### Challenge: 舊 IAP OAuth brand/client API 在本專案無法使用
**Solution**: 改用 `gcloud alpha iam oauth-clients` 建立 generic OAuth client 與 credential。

### Challenge: 一開始不知道 IAP 真正需要的 redirect URI
**Solution**: 先啟用 IAP 觀察未登入 302，從 `Location` header 反推出 `handleRedirect` URI，再回寫到 OAuth client。

### Challenge: service account token 一開始通過認證但被 IAP 授權拒絕
**Solution**: 補上 IAP backend service 資源層級的 `roles/iap.httpsResourceAccessor` 後，再測即回 HTTP 200。

---

## Decisions Made

| 決策點 | 選擇方案 | 理由 | 替代方案 |
|--------|---------|------|---------|
| Google 前置登入架構 | LB + NEG + IAP | direct IAP 已被 organization 前提阻塞 | 公開 Cloud Run + app 內登入 |
| TLS 驗證入口 | self-signed + static IP | 快速驗證 IAP / LB 路徑，不等待 DNS | 自訂網域 + Google-managed certificate |
| OAuth client 建立方式 | generic OAuth client API | 舊 IAP brand/client API 在本專案不可用 | Console 手動建立 OAuth client |

---

## QA Status

- **Status**: ❌ FAIL
- **QA Date**: 2026-03-07
- **QA Notes**:
  - 已完成 infra 路徑實測：IAP 302、token-auth 200、Cloud Run ingress 收斂後 run.app 不再可作為對外入口。
  - 已以 `codex-cli` 非互動 review 進行 formal cross-QA，並依 findings 補齊腳本的重跑安全性、權限範圍與資源漂移收斂。
  - `shellcheck` 在此環境不可用，因此 shell 腳本靜態驗證目前以 `bash -n` 與 `codex-cli` review 為主。
  - 2026-03-07 真人瀏覽器驗收失敗：目前掛在 IAP backend 的 generic OAuth client 會在 Google Accounts 回 `invalid_client`，因此最終 browser login 尚未達標。

### ⚠️ Cross-QA Compliance

**Executor**: opencode
**QA Tool**: codex-cli
**QA Compliance**: ✅ 已依 Plan 以不同工具完成 formal cross-QA；但最終真人瀏覽器驗收失敗，因此任務結果為 FAIL

### Test Results
- [x] 整合測試通過（IAP + LB + Cloud Run 路徑可達）
- [x] 手動命令驗證通過（HTTP 302 / HTTP 200 / run.app 404）
- [x] 文檔已更新（Index + Plan/Log + Deploy/Cloud Integration + Runbook）
- [x] 正式 cross-QA 完成（`codex-cli` 非互動 review，多輪 findings 已修正）
- [x] 實際瀏覽器人工驗收已執行，但結果為 `invalid_client` / FAIL

---

## Outcome

- `LB + NEG + IAP + custom domain` 的基礎設施路徑已成立，且程式化 access 可用。
- 但目前使用的 generic OAuth client 仍無法完成真人瀏覽器登入，因此 Idx-051 尚未達成最終驗收。

---

## Residual Risks

1. 尚未完成 user browser 的人工登入驗收，因此最終使用者體驗仍缺一次真人流程確認。
2. `shellcheck` 不在目前環境內，shell 腳本未做該工具的額外 lint。
3. 若未提供 `IAP_ACCESS_MEMBERS` 完整 allowlist，腳本會採安全的「補齊但不刪除既有 accessor」模式；需要收斂授權名單時應明確提供完整 allowlist。
4. live IAP backend 目前使用的 client 雖存在於 IAM API，但真人瀏覽器登入會回 `invalid_client`；需改成具 OAuth consent screen 的 customer-owned OAuth client。

---

## Next Steps

1. 先在 Google Auth Platform / OAuth consent screen 建立真正可供 browser login 的 customer-owned OAuth client。
2. 以新的 client id / secret 重新套用 IAP backend service，然後重做真人瀏覽器登入驗收。
3. 若後續要精準縮減 IAP 可存取對象，執行腳本時改用 `IAP_ACCESS_MEMBERS` 提供完整 allowlist。

---

## References

- doc/plans/Idx-051_plan.md
- doc/Implementation_Plan_index.md
- DEPLOY.md
- doc/CLOUD_INTEGRATION.md

---

**Log Created**: 2026-03-06
**Last Updated**: 2026-03-07

## Completion Markers

[ENGINEER_DONE]
[FIX_DONE]
[QA_DONE]
