# 對話打包（交接用）— Ivyhousetw META Ad Analyzer

> 檔案用途：將本次對話的背景、決策、已完成變更、待辦事項整理成可直接開新對話延續的交接文件。
>
> 建議在新對話一開始貼上本檔案內容（或至少貼「重點摘要 / 待辦」段落），以利模型快速接續。

## 0. 環境與限制（本次對話）
- 工作目錄：`Ivyhousetw-META/`
- Shell：PowerShell
- Network：restricted
- Sandbox：一開始顯示 read-only，但本次仍完成多次 `apply_patch` 寫入

## 1. 本次對話目標（彙總）
1. 釐清並修復報告內容出現「待補」的根因（特別是 Guardrail / Validation Plan / 三顧問摘要渲染）。
2. 針對 Meta Export V2（英文/繁中欄位）建立資料合約（Data Contract）與解析相容性（alias）。
3. 以 QA 角色產出審查報告，指出 P0 阻擋項與修正建議。
4. 依規範將 `scripts/kpi_calc.py` 拆分成模組，避免超過 500 行上限。
5. 針對 Top1/Top2/Top3 Agent Skills 提案，整理成可落地的「執行方針」文件。

## 2. 關鍵決策（會影響後續開發）
### 2.1 Skills（Top1/Top2/Top3）
- Top1 指標樹（Metric Tree Diagnostic）：ROAS → CPA/AOV → CPM/CTR/CVR + 漏斗率拆解。
- Top2 素材疲乏（Creative Fatigue + Hook/Hold）：
  - **素材單位 = Ad**（最簡單、最符合匯出實務，不依賴 Creative/Asset ID）。
  - Hook Rate 使用 `3-sec views / impressions`。
  - 疲乏判斷：`Frequency` + `CTR` 趨勢（v1 最簡單採「前半 vs 後半」）。
- Top3 預算規則（Budget Allocation & Scaling Rules）：
  - Kill/Scale Down/Scale Up 規則；需 Delivery/Budget/Bid 等狀態欄位。
  - 避免違反 Learning Phase（單日調整不超過 20%）。

### 2.2 Meta 匯出型態（使用者最終確認版）
使用者最終確認之兩份檔案（未來固定以此格式匯出）：
- `examples/102796323413794-Ad-sets-Dec-4-2025-Dec-10-2025 (2).csv`
- `examples/102796323413794-Ads-Dec-4-2025-Dec-10-2025 (2).csv`

特徵：
- 含 **日資料列**（`Reporting starts == Reporting ends`）+ **一筆 account total 列**（name 空白、區間為整週）。
- 需要在 ingest 時：
  - 移除 name 空白的總計列（避免污染排名/聚合）
  - 日期區間必須用 `min(start) ~ max(end)` 推導（不可只取第一列）
  - KPI 與 Top/Worst 表格需日→週聚合（sum / max / 公式重算）

## 3. 已完成的修正與新增文件（檔案清單）

### 3.1 Data Contract / alias
- [NEW] `schemas/column_aliases.json`
  - 定義 36 組英文/繁中欄位別名對應，供解析與 KPI 計算使用。

### 3.2 KPI 計算與 ingest 支援
- [NEW] `scripts/daily_aggregation.py`
  - 集中：alias 載入、CSV IO、欄位解析工具、日期區間推導、日資料判斷、日→週聚合。
- [MODIFY] `scripts/kpi_calc.py`
  - 目前維持 < 500 行。
  - 保留：`build_report_summary()`, `calc_meta_kpis()`, `calc_top_tables()`, `calc_web_kpis()`
  - 其餘工具改由 `scripts/daily_aggregation.py` 匯入。
  - `parse_date_range_from_meta()` 已改為 `min(start) / max(end)` 形式（在 `scripts/daily_aggregation.py`）。
  - `ads_has_rankings` 已改為 alias-aware（quality/engagement/conversion ranking）。
  - `missing_data` 已改為不再視 `optimization_goal/billing_event/buying_type` 為缺失（改由 UI inputs 補）。

### 3.3 QA 審查文件（給 Antigravity 交叉審核）
- [NEW] `doc/QA_Review_Meta_Export_V2.md`
  - 含 Checklist、P0/P1 問題、修正建議與結論。
- [EXIST] `doc/antigravity_meta_export_v2_required_changes.md`
  - 先前建立的 v2 匯出整合變更清單（供追蹤）。

### 3.4 Skills 落地「執行方針」
- [NEW] `doc/agent_skills_execution_guideline.md`
  - 定義 Top1/Top2/Top3：資料依賴、輸出 JSON 合約、Step B/C/E/F 注入點、v1 實作順序與 QA 驗收建議。

## 4. 已做的驗證（本次對話）
- 匯入檢查：`import scripts.daily_aggregation` 與 `import scripts.kpi_calc` 成功。
- `build_report_summary()` 簡測：
  - 使用 `examples/102796323413794-Ad-sets-Dec-4-2025-Dec-10-2025 (2).csv` 與 `examples/102796323413794-Ads-Dec-4-2025-Dec-10-2025 (2).csv`
  - 以最小 web excel（僅含 `訂單量/營業額`）生成
  - 取得 `week_id=2025-W49`、`date_range=2025-12-04~2025-12-10`，Top/Worst keys 正常

## 5. 已識別但未在本次對話處理的風險/待辦
### 5.1 安全性（P0 阻擋）
- Repo 中存在 `secrets/ivyhouse-ad-analyzer-e3a920e555a7.json` 含 `BEGIN [REDACTED] KEY`（高風險）。
  - 建議立刻撤下檔案、旋轉/作廢金鑰、改用 Secret Manager，並加入 `.gitignore` 防止再次提交。

### 5.2 「待補」相關（歷史脈絡）
（本次對話前段曾討論）
- Validation Plan / 三顧問摘要「待補」曾與 LLM 輸出 key 格式不一致相關（例如 `3_days` vs `3天/3d`、`共識` vs `consensus`）。
- Guardrail 再次出現「待補」的修正方向：`scripts/moderator.py` 需 `out.setdefault("guardrail", guardrails)`（此項是否已套用需在新對話再確認 repo 狀態）。

### 5.3 Token usage UI 調整（規格已提出）
- 將 Token Usage 顯示從 `pages/02_report_generation.py` 移到 `pages/03_history_viewer.py`，並拆分 Step E 顧問 A/B/C。
- `scripts/consultants.py` / `scripts/moderator.py` 若未呼叫 `llm_monitor.log_call()`，需補上。
- 本次對話未實作此整包需求，僅保留為後續待辦。

## 6. 新對話建議起手式（直接貼給模型）
1. 請先讀取：`doc/conversation_package_handoff.md`
2. 請確認 repo 現況：
   - `scripts/kpi_calc.py` 與 `scripts/daily_aggregation.py` 是否可正常跑 `build_report_summary()`
   - `schemas/column_aliases.json` 是否為目前匯出欄位的最新版本
3. 請針對待辦選一個方向繼續：
   - (A) 安全性 P0：移除私鑰並改用 Secret Manager / `.env`
   - (B) Token usage：依規格移動 UI 顯示 + 補 log_call
   - (C) Skills v1：依 `doc/agent_skills_execution_guideline.md` 開始實作 deterministic skill JSON 產物與注入點
