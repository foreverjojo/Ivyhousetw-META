# Idx-049 Log — 驗證 main push 是否自動觸發 Cloud Build 並部署 Cloud Run

## 結論

- 已完成端到端驗證：`main` push 會自動觸發 Cloud Build，並成功部署到 Cloud Run。
- 第一輪驗證證明 trigger 正常，但暴露 `cloudbuild.yaml` 的 `AUTH_FLAG` substitution 問題。
- 第二輪以最小修正將 `${AUTH_FLAG}` 改為 `$${AUTH_FLAG}` 後，build 與 deploy 均成功完成。

## 執行摘要

- Trigger ID：`a863974b-ba4a-4a80-aea4-b60517589a4b`
- Trigger 名稱：`deploy-cloudrun-main`
- 第一輪 commit：`4a576302b607ebcbefbc23bac8835b12ee4f52ba`
- 第一輪 commit message：`chore(Idx-049): validate main trigger deployment`
- 第一輪 build：`d86d2b49-ce08-42cd-a905-a1a09b2a1e09` → `FAILURE`
- 第二輪 commit：`672c36b5625f6283cae97a37ed28cf51fb94ba98`
- 第二輪 commit message：`fix(cloudbuild): escape AUTH_FLAG substitution`
- 第二輪 build：`d78f8a27-f5ef-47fe-87d0-06fa652d926c` → `SUCCESS`
- Cloud Run service：`ivyhouse-meta-analyzer`
- Cloud Run revision：`ivyhouse-meta-analyzer-00001-b22`
- Cloud Run URL：`https://ivyhouse-meta-analyzer-971489052398.asia-east1.run.app`

## 驗證證據

### 1. 第一輪：trigger 已被 main push 觸發

- `gcloud beta builds list --project=ivyhouse-ad-analyzer --region=asia-east1 --limit=10 --sort-by='~createTime'`
- build：`d86d2b49-ce08-42cd-a905-a1a09b2a1e09`
- createTime：`2026-03-06T14:07:51Z`
- 對應 trigger：`a863974b-ba4a-4a80-aea4-b60517589a4b`

### 2. 第一輪失敗原因

- `gcloud beta builds describe d86d2b49-ce08-42cd-a905-a1a09b2a1e09 --project=ivyhouse-ad-analyzer --region=asia-east1`
- `statusDetail`：

```text
generic::invalid_argument: invalid value for 'build.substitutions':
 key in the template "AUTH_FLAG" is not a valid built-in substitution
```

### 3. 第二輪修正

- 修正檔案：`cloudbuild.yaml`
- 修正內容：deploy step 的 `${AUTH_FLAG}` 改為 `$${AUTH_FLAG}`
- 目的：保留 shell 變數展開，避免 Cloud Build 在解析階段把 `AUTH_FLAG` 當成 substitution key

### 4. 第二輪成功結果

- `gcloud beta builds describe d78f8a27-f5ef-47fe-87d0-06fa652d926c --project=ivyhouse-ad-analyzer --region=asia-east1`
- 結果：`status: SUCCESS`
- finishTime：`2026-03-06T14:20:01.865262Z`
- image：`gcr.io/ivyhouse-ad-analyzer/ivyhouse-meta-analyzer:672c36b`

### 5. Cloud Run service / revision 已建立

- `gcloud run services describe ivyhouse-meta-analyzer --project=ivyhouse-ad-analyzer --region=asia-east1`
- service URL：`https://ivyhouse-meta-analyzer-971489052398.asia-east1.run.app`
- latest revision：`ivyhouse-meta-analyzer-00001-b22`
- deployed by：`971489052398-compute@developer.gserviceaccount.com`

- `gcloud run revisions list --project=ivyhouse-ad-analyzer --region=asia-east1 --service=ivyhouse-meta-analyzer --limit=5`
- revision：`ivyhouse-meta-analyzer-00001-b22`
- 狀態：`ACTIVE`

## 受影響檔案

- `CHANGELOG.md`：第一輪最小驗證 commit 載體
- `cloudbuild.yaml`：第二輪最小修正檔案

## QA 判定

- 結果：`PASS_WITH_RISK`
- 理由：技術目標已完成，但 QA 依賴直接的 GCP CLI 驗證，而非 OpenCode 終端輸出與獨立 cross-QA 報告。
