# Ivy House｜Meta 週會 MVP (Streamlit)

## What this repo is
- Streamlit app for weekly Meta report ingestion (Adset CSV + Ad CSV + Web Excel)
- Step B produces `report_summary.json` and **forces schema validation** using `schemas/report_summary.v1.json`
- Validation errors are logged into `pipeline_state.json` with event step `B(validate_error)`


## Run app
```bash
streamlit run app.py


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
