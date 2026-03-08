# Testing 小範圍使用 Runbook

版本：2026-03-08
目的：在 Google Auth Platform 維持 `External / 測試` 的前提下，穩定維護少量主管帳號的存取權。

## 適用範圍
- 目前只開放固定少數主管使用，不推 production / brand verification。
- 網站入口仍為 IAP 保護的 `https://adanalyzer.shincold.com/`。
- 公開 legal 頁維持：
  - `https://adanalyzer.shincold.com/legal/`
  - `https://adanalyzer.shincold.com/legal/privacy/`
  - `https://adanalyzer.shincold.com/legal/terms/`

## 核心原則
- 在 `External / 測試` 模式下，只補 IAP allowlist 不夠。
- 每新增一位主管，必須同步補兩個地方：
  1. Google Auth Platform `目標對象 > 測試使用者`
  2. IAP backend service 的 `roles/iap.httpsResourceAccessor`
- 任一邊漏補，該帳號都不應視為可正常登入。

## 目前正式維護名單

### Google Auth Platform 測試使用者
- `foreverwow001@gmail.com`
- `ivyhousetw@gmail.com`
- `foreverjojo@gmail.com`
- `maomaohappymeow@gmail.com`

### IAP allowlist
- `user:foreverwow001@gmail.com`
- `user:ivyhousetw@gmail.com`
- `user:foreverjojo@gmail.com`
- `user:maomaohappymeow@gmail.com`
- `serviceAccount:971489052398-compute@developer.gserviceaccount.com`

### 本次範圍缺口
- 主管帳號缺口：0
- 說明：使用者已明確確認本次 3 個 email 就是全部需要開放的主管帳號，且 2026-03-08 已完成雙層名單補齊。

## 新增一位主管的最小步驟

### 1. 補 Google Auth Platform 測試使用者
1. 開啟 Google Cloud Console：`Google Auth Platform > 目標對象`
2. 確認 `發布狀態 = 測試`、`使用者類型 = 外部`
3. 在 `測試使用者` 區塊按 `Add users`
4. 輸入主管的 Google 帳號 email
5. 按 `Save`

### 2. 補 IAP allowlist
使用下列指令加入 IAP backend service：

```bash
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=ivyhouse-meta-iap-backend \
  --member='user:<manager-email>' \
  --role='roles/iap.httpsResourceAccessor' \
  --project=ivyhouse-ad-analyzer
```

## 最小驗證

### 驗證 test users
- 開啟 `Google Auth Platform > 目標對象`
- 確認 `測試使用者` 清單中看得到目標 email

### 驗證 IAP allowlist

```bash
gcloud iap web get-iam-policy \
  --resource-type=backend-services \
  --service=ivyhouse-meta-iap-backend \
  --project=ivyhouse-ad-analyzer \
  --format='json'
```

- 確認 `roles/iap.httpsResourceAccessor` binding 中含 `user:<manager-email>`

### 驗證網站入口仍正常

```bash
curl -I https://adanalyzer.shincold.com/
```

- 預期：未登入時回 `302` 到 Google OAuth，而不是 `401 invalid_client`

## 移除一位主管
- 從 `Google Auth Platform > 目標對象 > 測試使用者` 移除該 email
- 再移除 IAP binding：

```bash
gcloud iap web remove-iam-policy-binding \
  --resource-type=backend-services \
  --service=ivyhouse-meta-iap-backend \
  --member='user:<manager-email>' \
  --role='roles/iap.httpsResourceAccessor' \
  --project=ivyhouse-ad-analyzer
```

## 殘餘風險
- 帳號即使已列入雙層名單，若該 email 不是有效可登入的 Google 帳戶，實際登入仍可能失敗。
- 只要應用維持 `External / 測試`，就不適合擴到大量外部使用者；超過目前小範圍使用時，應改走正式發布與驗證流程。
