# Task Execution Log

**Index**: Idx-051
**Plan Version**: 2026-03-06-v1
**Task Description**: 方案 A：以 Google 前置身分保護私有 Cloud Run 網站入口

---

## Metadata

- **Start Time**: 2026-03-06 16:22:00 UTC
- **End Time**: 2026-03-07 18:15:45 UTC
- **Engineer**: opencode（依 Plan 工具選擇）
- **QA**: codex-cli（Plan 指定；已完成 formal cross-QA）
- **Duration**: 多輪執行，含 2026-03-07 的 customer-owned OAuth client 修正、Secret Manager 收斂與真人瀏覽器驗收

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

3. customer-owned OAuth client 修復完成
- 在 Google Auth Platform 建立 customer-owned Web OAuth client：`971489052398-untjbrcfdlqc5bg61hbce6aigeia033e.apps.googleusercontent.com`。
- 重新將 IAP backend service 綁定到新的 OAuth client / secret。
- live 入口的 `Location` header 已切換為新的 client id，不再引用舊的 generic client。
- 真人瀏覽器驗收已成功完成：Google 帳戶選擇頁 → OAuth 同意頁 → `首頁 | Ivy House Meta`。

4. 實際建立的 GCP 驗證資源
- Global static IP: `ivyhouse-meta-iap-ip` → `34.95.93.163`
- SSL certificate: `ivyhouse-meta-iap-cert`（self-managed / self-signed）
- Serverless NEG: `ivyhouse-meta-iap-neg`
- Backend service: `ivyhouse-meta-iap-backend`
- URL map: `ivyhouse-meta-iap-map`
- Target HTTPS proxy: `ivyhouse-meta-iap-proxy`
- Forwarding rule: `ivyhouse-meta-iap-fr`

5. 權限與硬化
- 建立 IAP service identity：`service-971489052398@gcp-sa-iap.iam.gserviceaccount.com`
- 授予該 principal `roles/run.invoker`
- 在 IAP backend service 資源層級授予下列 principal `roles/iap.httpsResourceAccessor`
  - `user:foreverwow001@gmail.com`
  - `serviceAccount:971489052398-compute@developer.gserviceaccount.com`
- 將 Cloud Run ingress 更新為 `internal-and-cloud-load-balancing`

6. 驗收結果
- 未登入請求 `https://34.95.93.163/`：HTTP 302 → `accounts.google.com`
- 帶 `aud=<IAP client id>` 且含 `email` claim 的 impersonated service account OIDC token：HTTP 200，成功回傳 Streamlit HTML
- 直接外部請求 `https://ivyhouse-meta-analyzer-dlnp2adjbq-de.a.run.app/`：在 ingress 收斂後回 HTTP 404
- 正式子網域 `https://adanalyzer.shincold.com/`：Google-managed certificate 已啟用，未登入請求回 HTTP 302 → `accounts.google.com`
- 2026-03-07 customer-owned OAuth client 回綁後，入口已改回新的 Google OAuth authorize URL。
- 2026-03-07 真人瀏覽器驗收：成功通過 Google 帳戶選擇頁、OAuth 同意頁，最後載入 `首頁 | Ivy House Meta`。
- 2026-03-07 最小 smoke test：`bash -n scripts/setup_cloud_run_iap_entry.sh` 通過，且以 `IAP_OAUTH_CLIENT_SECRET_NAME=iap-oauth-client-secret` 重跑腳本後，backend service 仍指向 `971489052398-untjbrcfdlqc5bg61hbce6aigeia033e.apps.googleusercontent.com`，`curl -I https://adanalyzer.shincold.com/` 仍回新的 Google OAuth authorize URL。
- 2026-03-07 公開 legal pages 已掛到 `https://adanalyzer.shincold.com/legal/`、`/legal/privacy/`、`/legal/terms/`，且 `curl -I` 驗證為 HTTP 200；同時網站根目錄 `/` 仍維持 IAP 302。
- 2026-03-07 Google Auth Platform Branding draft 已更新並儲存為新的 `/legal/...` 公開網址。
- 2026-03-08 Search Console 檢查：`foreverwow001@gmail.com` 對 `sc-domain:shincold.com` 顯示「你沒有存取這項資源的權限」，因此尚無法以此帳號確認網域驗證狀態。
- 2026-03-08 Verification Center 檢查：畫面顯示「應用程式已設為測試發布狀態，因此不需要驗證」，目前尚不是直接送 brand verification 的狀態。

7. 第 2 步腳本化
- 新增 `scripts/setup_cloud_run_iap_entry.sh`，將 LB + NEG + IAP + ingress 收斂流程做成可重跑腳本。
- 腳本不保存 OAuth client secret，支援執行時環境變數注入，或從 Secret Manager 讀取 `IAP_OAUTH_CLIENT_SECRET_NAME`。
- 腳本已補齊多輪 review 修正：IAP enable idempotency、managed cert/NEG drift、global LB scope、forwarding rule / backend 收斂，以及 IAP allowlist 管理。
- 2026-03-07 已以 `IAP_OAUTH_CLIENT_SECRET_NAME=iap-oauth-client-secret` 成功重跑腳本，驗證 Secret Manager 路徑可用。

---

## Challenges & Solutions

### Challenge: direct IAP on Cloud Run 被 organization 條件阻塞
**Solution**: 改走 `External HTTPS Load Balancer + Serverless NEG + IAP` fallback。

### Challenge: 舊 IAP OAuth brand/client API 在本專案無法使用
**Solution**: 先用 generic OAuth client 驗證 IAP backend 路徑，再改由 Google Auth Platform 建立 customer-owned Web OAuth client 完成真人瀏覽器登入。

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
| OAuth client 建立方式 | Google Auth Platform customer-owned Web client | 可完成真人瀏覽器登入與 OAuth consent screen | generic OAuth client API |

---

## QA Status

- **Status**: ⚠️ PASS WITH RISK
- **QA Date**: 2026-03-07
- **QA Notes**:
  - 已完成 infra 路徑實測：IAP 302、token-auth 200、Cloud Run ingress 收斂後 run.app 不再可作為對外入口。
  - 已以 `codex-cli` 非互動 review 進行 formal cross-QA，並依 findings 補齊腳本的重跑安全性、權限範圍與資源漂移收斂。
  - 2026-03-07 已完成 customer-owned OAuth client 回綁，live 入口 `curl -I` 會吐出新的 Google OAuth authorize URL，且真人瀏覽器驗收已成功回到首頁。
  - `shellcheck` 在此環境不可用，因此 shell 腳本靜態驗證目前以 `bash -n` 與 runtime smoke test 為主。

### ⚠️ Cross-QA Compliance

**Executor**: opencode
**QA Tool**: codex-cli
**QA Compliance**: ⚠️ formal cross-QA 仍以前一輪 `codex-cli` 為準；本輪 customer-owned OAuth client 修復已補做 runtime 驗收，但尚未追加第二輪不同工具的 repo-side review

### Test Results
- [x] 整合測試通過（IAP + LB + Cloud Run 路徑可達）
- [x] 手動命令驗證通過（HTTP 302 / HTTP 200 / run.app 404）
- [x] 文檔已更新（Index + Plan/Log + Deploy/Cloud Integration + Runbook）
- [x] 正式 cross-QA 完成（`codex-cli` 非互動 review，多輪 findings 已修正）
- [x] customer-owned OAuth client 已建立並回綁至 IAP backend
- [x] Secret Manager secret `iap-oauth-client-secret` 已建立並由腳本成功讀取
- [x] 最小 smoke test 已通過（`bash -n` + 腳本重跑 + live 302 + 首頁載入）
- [x] 實際瀏覽器人工驗收已執行，結果為 PASS（帳戶選擇 → OAuth 同意 → 首頁）

---

## Outcome

- `LB + NEG + IAP + custom domain` 的基礎設施路徑已成立，且 customer-owned OAuth client 已成功接手 browser flow。
- 授權使用者現在可透過 Google OAuth 瀏覽器流程登入並進入 `Ivy House Meta` 首頁。

---

## Residual Risks

1. OAuth consent screen 目前仍為 `External / 測試`；若要擴大給更多外部使用者，需再處理正式發布與驗證。
2. `foreverwow001@gmail.com` 目前沒有 `shincold.com` 的 Search Console property 存取權；正式送審前仍需用 owner 帳號確認網域驗證、authorized domains 與 Verification Center 狀態一致。
3. `shellcheck` 不在目前環境內，shell 腳本未做該工具的額外 lint。
4. 若未提供 `IAP_ACCESS_MEMBERS` 完整 allowlist，腳本會採安全的「補齊但不刪除既有 accessor」模式；需要收斂授權名單時應明確提供完整 allowlist。

---

## Next Steps

1. 視需要把 OAuth consent screen 從 `測試中` 推進到正式發布，並完成 Google 驗證流程。
2. 用持有 `shincold.com` Search Console 權限的帳號確認或補做網域驗證，並在切到 production 後重新檢查 Verification Center 是否可直接送 brand verification。
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
