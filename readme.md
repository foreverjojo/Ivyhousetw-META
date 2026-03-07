# Ivy House｜Meta 週會 MVP (Streamlit)

## What this repo is
- Streamlit app for weekly Meta report ingestion (Adset CSV + Ad CSV + Web Excel)
- Step B produces `report_summary.json` and **forces schema validation** using `schemas/report_summary.v1.json`
- Validation errors are logged into `pipeline_state.json` with event step `B(validate_error)`

## Release / Changelog
- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Latest: `0.3.0` (2026-01-04) — Phase 3 多通路擴充（Shopee/MOMO）+ 觀測性基礎建設（structured logging / LLM monitor）
- Unreleased: Phase 4 Streamlit Crew Console MVP、Trace ID 追蹤系統（詳見 `CHANGELOG.md`）

## Public legal pages
- GitHub Pages source: `public_site/`
- Default public home: `https://foreverjojo.github.io/Ivyhousetw-META/`
- Privacy policy: `https://foreverjojo.github.io/Ivyhousetw-META/privacy/`
- Terms of service: `https://foreverjojo.github.io/Ivyhousetw-META/terms/`
- OAuth consent screen publication checklist: `doc/OAUTH_CONSENT_PUBLICATION.md`


## Run app
```bash
streamlit run app.py
```

### Development environment（Dev Container & Cloud IDE）
- 本專案維護下列 extension 清單：`.devcontainer/devcontainer.json`（Dev Container）、`.vscode/extensions.json`（工作區建議）、`.idx/dev.nix`（IDX / Firebase Studio）。
- 在 Dev Container 中開啟工作區時，VS Code 會根據 `.devcontainer/devcontainer.json` 安裝 extensions；在 IDX / Firebase Studio 開啟時，會安裝 `.idx/dev.nix` 內列的 extensions，以確保本地與雲端 IDE 的一致性。

### 一鍵自檢入口指令（建議）

恢復/重建環境後，建議先跑一次「可機械化」自檢（不修改系統）：

```bash
python scripts/portable/self_check.py --strict
```

若提示缺少 `ruff/pytest`（dev dependencies 未安裝），可用以下方式（擇一）：

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### When to use local workflow
- 適用於快速測試或效能敏感的任務，例如處理大量數據或執行性能測試。
- 當容器啟動過慢或 Docker 無法正常運行時。
- 如果本機環境已經配置完成，且不需要 Dev Container 的隔離性。

### Quick steps: Run locally
1. **建立虛擬環境**：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. **安裝依賴**：
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. **執行應用程式**：
   ```bash
   streamlit run app.py
   ```

> **注意**：確保本機已安裝 Python 3.11+ 和必要工具（如 pip）。

### ========================================
## Data Contracts（唯一真值 / 不可漂移）
### ========================================

### 1) 固定 Schema 檔名（pipeline 僅認這幾份）
本專案的 pipeline 產物驗證只使用以下 schema（其餘命名視為非主流程規格或歷史檔，不得替代）：

- schemas/report_summary.v1.json
- schemas/inputs_snapshot.v3.json
- schemas/report_insights.v1.json
- schemas/consultant_notes.v1.json
- schemas/workflow_state.v1.json

> 原則：程式更新必須同步更新 schemas/；schemas/ 納入版本控管，避免口徑漂移。

### 2) Truth Source 鎖死（Report Summary 口徑）
report_summary.v1 固定：
- kpi_truth_source = "meta_adset_csv"（KPI 真值以 Adset 匯總為準）
- ad_diagnostics_source = "meta_ad_csv"（Ad 層僅用於素材/診斷，不作為 KPI truth）

### 3) 時區與時間戳
- 全部時間戳統一使用 Asia/Taipei
- report_summary.generated_at 必填

### 4) Meta CSV 匯出規範（避免語系漂移）
- 必須使用「中文欄位」匯出 Meta 報表；若偵測缺失必填中文欄位，parser 會直接報錯並提示重新匯出。
- Attribution setting 必須一致（固定口徑），否則視為不可比較的資料。

### 5) 清洗規則（總計/空名稱列）
- Meta CSV 若包含「總計 / 名稱為空」列，parser 會固定 drop，避免污染 KPI 與 top tables。
