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

如需，我可以：
- 1) 將此檔加入 repo（commit & push）；
- 2) 同時建立一個簡短 `scripts/ops/checks.sh` 來執行關鍵驗證指令。

請選擇要我下一步做哪一項。
