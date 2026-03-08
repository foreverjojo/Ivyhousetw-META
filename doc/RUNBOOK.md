# Runbook — Ivyhousetw-META

版本：2026-01-18
目的：為開發與運維團隊提供標準化的操作指引、故障排查與人工回復流程（包含一鍵恢復與發佈備援）。

## 摘要與範圍
- 適用對象：專案維運人員、開發人員（在沒有自動化或自動化失敗時）。
- 涵蓋範圍：Dev Container 啟動、GHCR image pull（digest）、一鍵恢復 playbook、手動 Release、常見故障排查。

## 前置條件 / 帳號權限
- GitHub repo 存取權（讀寫），如 repo/private 則需對應權限。
- GHCR pull 權限：建議使用 Classic PAT（至少 `read:packages`，必要時 `repo`）。
- 本機需安裝：`git`, `docker` (或 Docker Desktop + WSL2), `python3`。
- 建議環境變數（Windows PowerShell 範例）：

```powershell
setx GHCR_TOKEN "<your_pat>"
setx GHCR_USERNAME "<your_github_username>"
```

## 一鍵恢復 Playbook（標準流程）
1. Clone / pull 最新 `main`：

```bash
git clone https://github.com/foreverjojo/Ivyhousetw-META.git
cd Ivyhousetw-META
git pull origin main
```

2. （選擇性）設定 GHCR Token 並 login：

```powershell
# Windows PowerShell
docker login ghcr.io -u $env:GHCR_USERNAME -p $env:GHCR_TOKEN
```

3. 若要 full‑fidelity（容器層 pinned image）：

```bash
python scripts/portable/pin_devcontainer_image.py
# 然後在 VS Code: Dev Containers: Reopen in Container
```

4. 驗證環境（不修改系統）：

```bash
python scripts/portable/verify_restore_state.py --json
python scripts/portable/check_extensions_consistency.py --verbose
```

5. 啟動應用（容器或本機）：

```bash
# 容器內
streamlit run app.py
# 或本機 venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 手動 Release（若未啟用 CI release workflow）
- 若你沒有 `.github/workflows/release.yml`，手動發佈步驟：
  1. 更新 `VERSION` 文件（例如 `1.2.3`）。
  2. 產生 Changelog（手動或腳本）。
  3. 建立 Git tag 並 push：

```bash
git tag -a v1.2.3 -m "release v1.2.3"
git push origin v1.2.3
```

  4. 在 GitHub Releases 建立 Release，附上發行資產。

- 若要自動化（建議）：新增 `.github/workflows/release.yml`，觸發條件可設為 `push` 到 `main` 帶 `release/*` 分支或 `create` tag。

## 常見故障排查（快速指令）
- Docker not running / container failed to start：

```bash
# 檢查 docker
docker info
# 重新啟動 Docker Desktop / daemon (Linux)
sudo systemctl restart docker
```

- GHCR pull 401/403：
  - 確認 `docker login ghcr.io` 成功。
  - 確認 PAT scopes 有 `read:packages`，且你的帳號對 package 有讀取權限。

- `uv sync --frozen` 失敗：
  - 檢查 `uv.lock` 是否存在並為最新；若 workspace member missing，重新產生 `uv.lock`：

```bash
uv lock
uv sync --frozen
```

- Extensions 不一致：

```bash
python scripts/portable/check_extensions_consistency.py --verbose
# 若要自動修復（會覆寫部分列表）
python scripts/portable/check_extensions_consistency.py --fix
```

- `adanalyzer.shincold.com` 無法進入或只看到 403/404：
  - 先確認 DNS 是否解析到 Load Balancer IP `34.95.93.163`。
  - 檢查 Google-managed certificate 是否為 `ACTIVE`：

```bash
gcloud compute ssl-certificates describe ivyhouse-meta-iap-managed-cert \
  --global \
  --project=ivyhouse-ad-analyzer \
  --format='yaml(managed.status,managed.domainStatus)'
```

  - 檢查 backend service 的 IAP 是否啟用且 client ID 正確：

```bash
gcloud compute backend-services describe ivyhouse-meta-iap-backend \
  --global \
  --project=ivyhouse-ad-analyzer \
  --format='json(iap)'
```

  - 檢查 IAP backend service IAM 是否真的包含目標使用者 / service account：

```bash
gcloud iap web get-iam-policy \
  --resource-type=backend-services \
  --service=ivyhouse-meta-iap-backend \
  --project=ivyhouse-ad-analyzer
```

  - 檢查 Cloud Run ingress 是否已收斂為 `internal-and-cloud-load-balancing`：

```bash
gcloud run services describe ivyhouse-meta-analyzer \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer \
  --format='value(spec.template.metadata.annotations.run.googleapis.com/ingress)'
```

  - 若要重建入口資源，重新執行：

```bash
export IAP_OAUTH_CLIENT_ID="<iap-client-id>"
export IAP_OAUTH_CLIENT_SECRET_NAME="iap-oauth-client-secret"
# 如需跨專案取 secret，可另外提供：
# export IAP_OAUTH_CLIENT_SECRET_PROJECT="ivyhouse-ad-analyzer"
# 若要同時清理不在 allowlist 內的既有 accessor，另外提供：
# export IAP_ACCESS_MEMBERS="user:foreverwow001@gmail.com,serviceAccount:971489052398-compute@developer.gserviceaccount.com"

bash scripts/setup_cloud_run_iap_entry.sh \
  ivyhouse-ad-analyzer \
  asia-east1 \
  ivyhouse-meta-analyzer \
  adanalyzer.shincold.com
```

執行腳本的操作者需具備目標 secret 的讀取權限，例如 `roles/secretmanager.secretAccessor`。

  - 快速診斷：
    - `302` 到 `accounts.google.com`：IAP 前門正常，接著檢查登入帳號是否在 IAP IAM allowlist。
    - `401 invalid_client` / `The OAuth client was not found`：目前 live client 不存在、redirect URI 不正確，或入口仍在吐舊 client。先檢查 `gcloud compute backend-services describe ... --format='json(iap)'` 與 `curl -I https://adanalyzer.shincold.com/` 的 `Location` 是否一致；必要時重新執行 `gcloud iap web enable ...` 或可重跑腳本。
    - `403`：優先檢查 `roles/iap.httpsResourceAccessor` 是否綁在正確的 backend service，而不是只看 project IAM。
    - `404` 來自 `run.app`：這通常表示 Cloud Run ingress 收斂正常，`run.app` 已不是對外入口。
    - 憑證錯誤：優先檢查 DNS 是否已切到 `34.95.93.163`，以及 managed certificate 是否已 `ACTIVE`。

## 回滾/回復（手動）
- 回滾 container image：修改 `.devcontainer/devcontainer.json` 中的 `image` 欄位回到先前已知 digest，或在本地使用舊 tag。
- 回滾程式碼：

```bash
git revert <commit>
git push origin main
```

## 通知與升級流程
- 若無法在 15 分鐘內恢復，依序通知：Repo Owner → Dev Lead → Oncall（Slack / Pager）。
- 任何重大回滾或 hotfix 必須撰寫簡短 Post‑mortem，並放入 `doc/logs/`。

## 驗證成功的判定
- Dev Container 可成功啟動且 `streamlit run app.py` 在 既定端口回應。
- `python scripts/portable/verify_restore_state.py --strict` 回傳 PASS。
- Extensions 三方一致性檢查 PASS。

---

## Testing 小範圍使用：新增主管帳號 SOP

> **適用情境**：OAuth consent screen 維持 `External / 測試` 狀態，需要新增一位主管帳號讓其可登入 `adanalyzer.shincold.com`。
>
> ⚠️ **重要**：Testing 模式下必須同步更新以下**兩個地方**，缺一不可。僅更新 IAP allowlist 而未補 Google Auth Platform test users，該帳號仍會被 OAuth 同意頁擋回。

### 為什麼只補 IAP allowlist 不夠？

```
瀏覽器 → IAP（驗身分）→ Google Auth Platform OAuth consent screen（驗是否 test user）→ Cloud Run
```

- **IAP allowlist**（`roles/iap.httpsResourceAccessor`）：決定「誰被允許通過 IAP 閘道」。
- **Google Auth Platform test users**（`目標對象 > 測試使用者`）：決定「OAuth consent screen 在 Testing 模式下允許哪些 Google 帳號完成登入授權」。
- 若 OAuth consent screen 為 `Testing` 狀態，不在 test users 清單內的帳號會在 OAuth 階段收到 `Error 403: access_denied`，即使 IAP allowlist 已有該帳號。

### 新增一位主管的最小步驟

**Step 1：Google Auth Platform — 新增 test user（Console 操作）**

1. 開啟 [Google Auth Platform](https://console.cloud.google.com/auth/audience?project=ivyhouse-ad-analyzer)。
2. 左側選 **目標對象**。
3. 確認目前在 `External / 測試` 狀態，找到 **測試使用者** 區塊。
4. 點 **新增使用者** → 輸入主管 email → 儲存。
5. 儲存後頁面應顯示該 email 已列入清單。

**Step 2：IAP IAM — 新增 accessor（CLI 操作）**

```bash
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=ivyhouse-meta-iap-backend \
  --project=ivyhouse-ad-analyzer \
  --member='user:<新主管 email>' \
  --role='roles/iap.httpsResourceAccessor'
```

> ✅ 此指令為**追加**操作，不會影響現有 principals。

### 如何查詢目前名單

**IAP allowlist（CLI）**

```bash
gcloud iap web get-iam-policy \
  --resource-type=backend-services \
  --service=ivyhouse-meta-iap-backend \
  --project=ivyhouse-ad-analyzer \
  --format='json'
```

**Google Auth Platform test users（Console）**

開啟 [Google Auth Platform > 目標對象](https://console.cloud.google.com/auth/audience?project=ivyhouse-ad-analyzer) → 測試使用者區塊。

### 目前正式維護名單（2026-03-08 更新）

| 帳號 | IAP allowlist | Google test users | 說明 |
|------|:---:|:---:|------|
| `foreverwow001@gmail.com` | ✅ | ✅ | 原始開發者帳號（Idx-051 建立） |
| `ivyhousetw@gmail.com` | ✅ | ✅ | 主管帳號（Idx-052 新增） |
| `foreverjojo@gmail.com` | ✅ | ✅ | 主管帳號（Idx-052 新增） |
| `maomaohappymeow@gmail.com` | ✅ | ✅ | 主管帳號（Idx-052 新增） |
| `serviceAccount:971489052398-compute@developer.gserviceaccount.com` | ✅ | — | Compute SA（程式呼叫用） |

> **注意**：Google Auth Platform test users 需由持有 GCP project owner/editor 的帳號在 Console 操作，無 CLI 批次指令可用。Idx-052 的 3 位主管帳號已由操作者手動加入，IAP allowlist 部分也已由 Idx-052 以 CLI 完成。各帳號的首次真人登入 smoke check 仍需由帳號持有人在實際登入時補驗。

### 移除主管帳號

**IAP allowlist（CLI）**

```bash
gcloud iap web remove-iam-policy-binding \
  --resource-type=backend-services \
  --service=ivyhouse-meta-iap-backend \
  --project=ivyhouse-ad-analyzer \
  --member='user:<主管 email>' \
  --role='roles/iap.httpsResourceAccessor'
```

**Google Auth Platform test users**：在 Console 的測試使用者區塊手動移除。

---

如需，我可以：
- 1) 將此檔加入 repo（commit & push）；
- 2) 同時建立一個簡短 `scripts/ops/checks.sh` 來執行關鍵驗證指令。

請選擇要我下一步做哪一項。
