# GCP Service Account 金鑰作廢指南

**日期**: 2026-01-10
**原因**: Git 歷史洩漏檢測
**影響範圍**: `ivyhouse-ad-analyzer` 專案

---

## ⚠️ 背景說明

### 洩漏事件

- **檔案**: `ivyhouse-ad-analyzer-e3a920e555a7.json`
- **內容**: GCP Service Account 的 PRIVATE KEY
- **洩漏途徑**: 曾被 Git 追蹤並推送到 GitHub
- **已執行**:
  - ✅ 使用 `git filter-repo` 從歷史清除
  - ✅ 強制推送到遠端
  - ✅ 本地檔案已移除並 REDACT

### 為何仍需作廢？

即使已從 Git 歷史清除，仍必須假設：
1. GitHub 可能已緩存舊版本
2. 其他協作者可能已 clone 舊版本
3. 搜尋引擎可能已索引
4. **安全最佳實踐**: 任何曾公開的金鑰必須視為已洩漏

---

## 操作步驟

### Step 1: 登入 GCP Console

前往：https://console.cloud.google.com/

確認登入帳號有 `ivyhouse-ad-analyzer` 專案的管理權限

---

### Step 2: 前往 Service Accounts

1. 點擊左上角「☰」選單
2. 選擇「IAM & Admin」→「Service Accounts」
3. 或直接訪問：https://console.cloud.google.com/iam-admin/serviceaccounts

![GCP Console Navigation](https://cloud.google.com/iam/docs/images/service-accounts.png)

---

### Step 3: 選擇專案

在頂部專案選擇器中，選擇：

**ivyhouse-ad-analyzer**

![Project Selector](https://cloud.google.com/resource-manager/docs/images/project-selector.png)

---

### Step 4: 找到 Service Account

在 Service Accounts 列表中，找到：

**Email**: `firebase-adminsdk-XXXXX@ivyhouse-ad-analyzer.iam.gserviceaccount.com`

> 通常名稱包含 `firebase-adminsdk` 或類似識別符

![Service Account List](https://cloud.google.com/iam/docs/images/service-account-list.png)

---

### Step 5: 檢視金鑰

1. 點擊該 Service Account
2. 切換到「金鑰 (Keys)」分頁
3. 查看現有金鑰列表

![Keys Tab](https://cloud.google.com/iam/docs/images/keys-tab.png)

---

### Step 6: 識別洩漏的金鑰

洩漏的金鑰 ID：**e3a920e555a7...**

在列表中找到此 Key ID（通常顯示完整或部分 ID）

**提示**: 可能顯示為：
- Key ID: `e3a920e555a7...`
- 建立日期: `2024-XX-XX`（查看 JSON 檔案中的 `client_id` 或建立時間）

---

### Step 7: 刪除洩漏的金鑰

1. 勾選該金鑰
2. 點擊「刪除 (Delete)」按鈕
3. 確認刪除對話框中，輸入「DELETE」並確認

⚠️ **注意**: 刪除後此金鑰將立即失效，無法恢復

![Delete Key](https://cloud.google.com/iam/docs/images/delete-key.png)

---

### Step 8: 建立新金鑰

1. 點擊「新增金鑰 (Add Key)」→「建立新金鑰 (Create new key)」
2. 選擇「JSON」格式
3. 點擊「建立 (Create)」
4. **重要**: 立即下載並安全儲存新金鑰

![Create New Key](https://cloud.google.com/iam/docs/images/create-key.png)

---

### Step 9: 更新部署設定

新金鑰下載後，需更新以下位置：

#### 1. GCP Secret Manager（推薦）

```powershell
# 上傳新金鑰到 Secret Manager
gcloud secrets versions add ivyhouse-service-account-key \
  --data-file="./NEW-KEY.json"
```

#### 2. 本地開發環境

```powershell
# 將新金鑰放到安全位置
cp NEW-KEY.json ~/secrets/ivyhouse-ad-analyzer.json

# 確保不在 Git 追蹤範圍內（已加入 .gitignore）
```

#### 3. Cloud Run 環境變數（如果有使用）

前往 Cloud Run 服務，更新 Secret 或環境變數

---

### Step 10: 測試新金鑰

驗證新金鑰可正常運作：

```python
# test_new_key.py
from google.oauth2 import service_account
from google.cloud import secretmanager

# 測試金鑰載入
credentials = service_account.Credentials.from_service_account_file(
    './NEW-KEY.json'
)

print(f"✅ 金鑰載入成功: {credentials.service_account_email}")
```

執行測試：
```powershell
python test_new_key.py
```

預期輸出：
```
✅ 金鑰載入成功: firebase-adminsdk-XXXXX@ivyhouse-ad-analyzer.iam.gserviceaccount.com
```

---

## 驗證檢查清單

完成上述步驟後，確認：

- [ ] 舊金鑰（Key ID: `e3a920e555a7...`）已從 GCP Console 刪除
- [ ] 新金鑰已建立並下載
- [ ] 新金鑰已上傳到 Secret Manager（或其他安全儲存）
- [ ] 本地開發環境已使用新金鑰
- [ ] Cloud Run / 部署環境已更新金鑰
- [ ] 測試腳本確認新金鑰可正常運作
- [ ] 舊金鑰檔案已從本地刪除（`ivyhouse-ad-analyzer-e3a920e555a7.json`）
- [ ] Git 歷史已驗證清除（`git log --all --full-history -- "**/*e3a920e555a7*"` 無輸出）

---

## 安全最佳實踐

### 未來防止金鑰洩漏

1. **使用 Secret Manager**
   - 不要在專案中直接儲存金鑰檔案
   - 使用 GCP Secret Manager 或 GitHub Secrets

2. **Pre-commit Hooks**（已實施）
   - `.pre-commit-config.yaml` 包含 `detect-private-key`
   - 自動阻止金鑰提交

3. **`.gitignore` 規則**（已實施）
   ```gitignore
   # ---- secrets (NEVER commit) ----
   secrets/
   *.pem
   *.key
   *-key.json
   ```

4. **定期輪換金鑰**
   - 建議每 90 天輪換一次 Service Account 金鑰
   - 使用 `scripts/check_verification_due.py` 追蹤輪換時間

5. **最小權限原則**
   - 為每個用途建立專用 Service Account
   - 只授予必要的 IAM 角色

---

## 緊急聯絡

若發現金鑰洩漏或異常活動：

1. **立即作廢金鑰**（上述 Step 7）
2. **檢查 GCP Audit Logs**：
   ```
   https://console.cloud.google.com/logs/query
   ```
   搜尋：
   ```
   resource.type="service_account"
   protoPayload.authenticationInfo.principalEmail="firebase-adminsdk-XXXXX@ivyhouse-ad-analyzer.iam.gserviceaccount.com"
   ```

3. **檢視異常活動**：
   - 前往「IAM & Admin」→「Audit Logs」
   - 查看過去 30 天的使用記錄
   - 尋找異常的 API 呼叫或資源存取

4. **通報**：
   - 若發現未授權使用，立即聯絡 GCP Support
   - 參考：https://cloud.google.com/support

---

## 參考資料

- [GCP Service Account Keys Best Practices](https://cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Detecting Leaked Credentials](https://cloud.google.com/architecture/detecting-leaked-credentials)

---

**最後更新**: 2026-01-10
**下次檢視**: 2026-04-10（90 天金鑰輪換）
