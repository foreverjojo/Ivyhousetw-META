# Agent Skills 執行方針（Top1/Top2/Top3）

> 檔案用途：定義「確定性技能（Deterministic Skills）」在本專案中的落地方式、資料合約、執行流程與產物格式，供 Antigravity IDE 交叉審核與後續開發依循。

## 1. 目標與原則

### 1.1 目標
- 讓使用者上傳 Meta Ads 匯出報表後，一鍵執行流程即可產出「可重現、可驗證」的分析結果。
- 將 Top1/Top2/Top3 變成「可在程式中被呼叫的技能」，並把結果注入到三顧問（Step E）與主持人（Step F）的輸入上下文，使 LLM 以技能結果為基礎撰寫內容，而不是憑空推論。

### 1.2 核心原則（必須遵守）
- **技能以程式執行為主**：LLM 不會真的「讀 skill.md 就自動執行」。`skill.md` 是規格/說明；真正執行要有對應的 Python 模組。
- **確定性優先**：能用公式/規則算出的就不要交給 LLM（例如 Hook Rate、ROAS 拆解、Kill Rule）。
- **輸出可溯源**：每個技能要輸出結構化 JSON（含使用的欄位、公式、門檻、樣本數、缺失欄位），方便 QA 與除錯。
- **向後相容**：CSV 欄位支援英文/繁中，統一由 `schemas/column_aliases.json` 管理。

## 2. 三個技能（Top1/Top2/Top3）定義

### Top 1：全漏斗指標樹診斷（Metric Tree Diagnostic）
**解決問題**
- 「ROAS 變差」到底壞在 CPM、CTR、CVR、AOV、或漏斗哪一段？

**核心依賴資料**
- Spend、Impressions、Link Clicks、LPV、ATC、IC、Purchases、Purchase Conversion Value（含 Website/Platform 兩套）
-（可選）Quality/Engagement/Conversion ranking（素材診斷補充）

**主要輸出（JSON）**
- ROAS/CPA/AOV 拆解與異常原因排序（例如：CTR 下降 → 素材吸引力不足）
- 漏斗率：Click→LPV、LPV→ATC、ATC→IC、IC→Purchase
- 漂移偵測：Website vs Platform conversion value 差異

---

### Top 2：素材疲乏偵測（Creative Fatigue + Hook/Hold）
**解決問題**
- 「這支素材還能不能用？」以及「該關還是該改落地頁？」

**決策單位**
- **以 Ad 為素材單位**（最簡單、最符合匯出實務；不依賴 Creative/Asset ID）

**核心依賴資料**
- Impressions、Frequency、CTR（link）、Link Clicks
- 影片：3-second video plays、Video plays at 95/100%、ThruPlays、Video average play time（擇一或多個）
-（建議）日資料：用於趨勢判斷（最簡單採「前半 vs 後半」）

**主要輸出（JSON）**
- Hook Rate：`3-sec views / impressions`
- Hold 指標（擇一）：
  - `100% views / impressions`（或 95%）
  - 或以 `ThruPlays / impressions` 作 proxy
- Fatigue 判斷：
  - `Frequency > 門檻` 且 `CTR 下降`（趨勢）
- 分類標記（例）：
  - `素材疲乏 → 建議關閉/換素材`
  - `Hook 高但 ROAS 低 → 高潛力但轉換差（建議優化落地頁/offer）`

---

### Top 3：預算配置與擴量規則（Budget Allocation & Scaling Rules）
**解決問題**
- 「這個廣告該加錢、降錢、還是關掉？」並避免違反學習期規則。

**核心依賴資料**
- Delivery、Bid strategy / Bid type、Budget / Budget type、Ends
- Spend、Purchases、CPA、ROAS（由 Top1 或 KPI 計算提供）
-（建議）日資料：判斷 3–7 天穩定性；v1 可先用「前半 vs 後半」或「最近 3 天 vs 前 3 天」

**主要輸出（JSON）**
- `[KILL]`：花費 > `1.5 * CPA 目標` 且轉換 0
- `[SCALE_DOWN]`：ROAS < Break-even 但仍有單 → 降預算 20%
- `[SCALE_UP]`：ROAS > 目標且連續 3 天穩定 → 加預算 20%
- `Learning Phase Guardrail`：一天內調整幅度不超過 20%

## 3. 專案落地架構（建議）

### 3.1 目錄建議
- `project_skills/`：存放技能規格（`skill.md`）與（可選）提示模板/範例輸入輸出
- `scripts/skills/`：存放技能的 Python 實作（確定性計算）
- `schemas/`：存放資料合約（例如 `column_aliases.json`）
- `history/<week>/.../`：每次跑完流程輸出版本化產物（技能 JSON、workflow_state、report）

### 3.2 技能規格與程式的關係
- `project_skills/<skill_name>/SKILL.md`：人類可讀的技能規格（門檻、公式、輸出欄位、例子）
- `scripts/skills/<skill_name>.py`：可被 pipeline 呼叫的實作，輸出結構化 JSON

## 4. 執行流程與注入點（對應 Step B/C/E/F）

### Step B（資料處理）
- 輸入：Meta Adset CSV、Meta Ads CSV、Web Excel
- 產出：`report_summary`（KPI、Top/Worst tables、date_range/week_id）
- 補強：
  - 支援日資料 → 週彙總（KPI/表格）
  - 保留日序列（供 Top2/Top3 趨勢判斷）

### Step C（LLM Insights）
- 建議做法：在呼叫 LLM 前，先執行 Top1（指標樹）並把結果寫入上下文，讓 LLM 只負責「語言化」與「策略整理」。

### Step E（三顧問）
- 建議做法：三顧問共享同一份技能結果（Top1/Top2/Top3 JSON），但每位顧問的提示詞強調不同面向：
  - 顧問 A：指標樹診斷 + 漏斗修正優先序（Top1）
  - 顧問 B：素材疲乏 + 素材策略（Top2）
  - 顧問 C：預算/投放操作規則（Top3）

### Step F（主持人）
- 主持人整合三顧問內容，並**以技能 JSON 作為「事實來源」**，避免出現「待補」或技術欄位名稱外露。

## 5. 技能輸出（Data Contract）最小規格

每個技能輸出 JSON 至版本資料夾（範例命名）：
- `skill_metric_tree.json`
- `skill_creative_fatigue.json`
- `skill_budget_rules.json`

建議共通欄位（每份都要有）：
- `schema_version`
- `generated_at`
- `inputs`: 使用到的欄位清單、缺失欄位清單
- `thresholds`: 本次使用的門檻值
- `results`: 技能主輸出（可供 LLM/報告引用）
- `warnings`: 例如資料不足（天數不足、影片指標缺失）

## 6. v1 實作順序（高性價比）
1. **Top1 指標樹（先做）**：最能提升「定位問題」的價值，且資料依賴最通用。
2. **Top2 素材疲乏**：只要有 3s/完播與 Frequency/CTR，就能給出可執行建議。
3. **Top3 預算規則**：需要目標 CPA/Break-even ROAS 等 UI inputs；v1 先做 Kill/Scale Up/Scale Down 的簡化版。

## 7. QA 驗收建議（必測）
- 同一份 CSV（英文/繁中欄名）輸出應一致（允許四捨五入差異）。
- 日資料模式下：
  - `date_range` 必須是整段（min start ~ max end）
  - KPI/Top tables 必須是週彙總而非單日排名
- 缺欄位時技能 JSON 必須回報 `warnings/missing_fields`，且報告不得顯示「待補」。

