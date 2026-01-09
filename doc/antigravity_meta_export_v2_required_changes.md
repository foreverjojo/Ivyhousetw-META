# Antigravity Review Notes — Meta Export v2 (Daily Rows + Total Row)

依據你最後定版的兩份匯出檔（English columns / 日資料 + 一行總計）：
- `examples/102796323413794-Ad-sets-Dec-4-2025-Dec-10-2025 (2).csv`
- `examples/102796323413794-Ads-Dec-4-2025-Dec-10-2025 (2).csv`

本文件整理「專案需要修正/擴充」的地方，作為 Antigravity IDE 交叉審核用的變更清單（Data Contract → Code）。

---

## 0) 這兩份 CSV 的結構特徵（會影響 ingest）

1. **同一份檔案同時包含：**
   - 每日列：`Reporting starts == Reporting ends`（例如 `2025-12-10`）
   - 一行「整體總計」：`Ad set name` / `Ad name` 為空，且 `Reporting starts=2025-12-04`、`Reporting ends=2025-12-10`
2. **沒有「每個 adset/ad 的週總計列」**（只有 daily rows + account total row）。
3. **欄位為英文，且部分名稱與現行 parser alias 不一致**（例如 `Checkouts initiated` / `Purchases conversion value` / `Website purchases conversion value`）。

結論：若要維持「每週匯出一次、只用這兩份檔案」，必須在 ingest 端同時做到：
- drop 掉全帳戶 total row（name 空白）
- 由 daily rows **自動聚合出週彙總**（供現有週報 top/worst 與 KPI）
- 同時保留 daily series（供 Skill 2/3 的趨勢判斷）

---

## 1) 影響範圍總覽（需要改哪些模組）

### A. Step B / 報表摘要生成（核心）
- `scripts/kpi_calc.py`
  - `parse_date_range_from_meta()`
  - `_drop_total_rows()`
  - `calc_meta_kpis()`
  - `calc_top_tables()`
  - `build_report_summary()`

### B. Unified adapter（若仍要維持 unified_ad_data）
- `scripts/adapters/meta_adapter.py`

### C. Skills（資料準備面）
- Skill 2/3 若要用「同一份檔案」的 daily rows 做趨勢，需要在 `report_summary`（或 skill runner）保留 daily series。
  - 建議：`report_summary._context.daily_series` 或獨立 artifact（例如 `meta_daily_series.json`）避免塞爆 LLM context。

---

## 2) 需要修正的行為（按需求分組）

## 2.1 現行週報流程（KPI + top/worst tables）需要能吃「英文日資料」

### (1) 日期區間與 week_id 產生
現況：`scripts/kpi_calc.py` 讀中文欄位 `分析報告開始/結束`。

需求：
- 支援 `Reporting starts` / `Reporting ends`
- 不依賴 total row（因為 total row 可能會被使用者不小心刪掉）
- 建議算法：忽略 name 空白列後
  - `date_start = min(Reporting starts)`
  - `date_end = max(Reporting ends)`

### (2) Total row 處理
需求：
- 依「name 欄位空白」判定為總計列並丟棄：
  - Adset 檔：`Ad set name == ""`
  - Ads 檔：`Ad name == ""`
- 並把 dropped 數量紀錄到 `report_summary.data_cleaning` 以利 QA。

### (3) 由日資料聚合出週彙總（供現行排序/報告）
需求：
- 在 `build_report_summary()` 內部建立：
  - `adset_weekly_df = groupby("Ad set name").sum(additive metrics)`
  - `ads_weekly_df = groupby(["Ad set name","Ad name"] 或至少 "Ad name").sum(additive metrics)`
- additive metrics（可直接 sum）：
  - `Amount spent (TWD)`, `Impressions`, `Link clicks`, `Landing page views`,
    `Adds to cart`, `Checkouts initiated`, `Purchases`, `Purchases conversion value`,
    `Website purchases`, `Website purchases conversion value`,
    `3-second video plays`, `ThruPlays`, `Video plays at 75%/95%/100%`, ...
- non-additive metrics（不可直接 sum）：
  - `Reach`, `Frequency`
  - v1 建議：weekly 用 `max`（或 `last day`），並在輸出標註口徑（例如 `frequency_agg: max_daily`）。
  - Skill 2 的 fatigue 判斷可仍用 daily frequency（不需要週聚合）。

### (4) 英文欄位 alias（確保 KPI/表格不讀成 0）
需要在 `scripts/kpi_calc.py` 的 `_sum_col()` candidates 補齊下列英文別名（至少）：
- Spend：
  - `Amount spent (TWD)` / `Amount spent`
- Purchases/value（platform）：
  - `Purchases`
  - `Purchases conversion value`（目前程式偏好 `Purchase Conversion Value`，需補 plural 版本）
- Purchases/value（truth / website direct）：
  - `Website purchases`
  - `Website purchases conversion value`
- Funnel：
  - `Landing page views`
  - `Adds to cart`
  - `Checkouts initiated`（目前程式用 `Initiate Checkout`，需補這個別名）
- Clicks：
  - `Link clicks`

### (5) top/worst tables 欄位擴充（支援 Skill 2/更完整的顯示）
建議把下列欄位帶入 `tables.top_ads_by_roas` / `worst_ads_by_roas`：
- `3_second_video_plays`, `thruplays`, `video_75`, `video_95`, `video_100`
- 並可在 deterministic skill 內計算 Hook/Hold（避免在 table 內算太多）

---

## 2.2 Skill 2（素材疲勞 / Hook & Hold / 趨勢）需要的資料形狀

已具備（來源：Ads CSV v2）：
- Hook/Hold 分子：`3-second video plays`, `Video plays at 75%/95%/100%`, `ThruPlays`
- 分母：`Impressions`
- Fatigue 變數：`Frequency`, `Link clicks`（CTR 的分子）, `Impressions`（分母）

仍需在 ingest/skill runner 補上：
1. **daily series 對每個 Ad 的切片**（才能做「前半週 vs 後半週」CTR 趨勢）
2. **一致的 join key**
   - v1 以 `Ad name` 作為素材 key（你已定版「以 Ad 當素材」）
   - 但長期強烈建議匯出並使用 `Ad ID`（避免改名/重名）

建議產出一份 deterministic artifact（避免塞進 LLM）：
- `meta_ad_daily_series.json`（按 `Ad name` 分組，每天存 clicks/impressions/frequency/3sec views 等）

---

## 2.3 Skill 3（預算規則）需要的狀態欄位

你最新 v2 已包含（Adset/Ads 都有）：
- `Ad set delivery` / `Ad delivery`
- `Ad set budget`
- `Ad set budget type`（例：Daily）
- `Ends`（例：Ongoing / 日期）
- `Bid type`（例：ABSOLUTE_OCPM）

仍建議補（若 Meta 允許匯出）：
- `Schedule`（若匯出拿不到，至少在 UI 手動輸入或由 Ends + 當前日期推估）
- `Bid strategy`（你瀏覽器欄位清單中有；但 CSV 目前輸出的是 `Bid type`，可能不是同概念）
- `Buying type` / `Billing event` / `Optimization goal`（若拿不到，維持 `inputs.json` 補）

---

## 3) 最終定版 CSV：合規性判定

### ✅ 符合（可以支持 Skills v1）
- Skill 2：Hook/Hold 必要欄位齊全
- Skill 3：預算規則核心欄位（budget + ends + delivery）齊全
- 補上 `Account name` / `Campaign name` / `Ad set name`（可讀性與派工上下文改善）

### ⚠️ 仍需工程處理
- 日資料需聚合成週彙總（否則週報 top/worst 失真）
- 英文欄位 alias 需要補齊（避免部分 KPI 讀成 0）
- ID 欄位缺失（非阻斷，但建議盡快補）

---

## 4) 建議的驗收點（QA Checklist）

1. 用 v2 CSV 跑 Step B 後：
   - `report_summary.kpi.meta` 的 spend/impressions/link_clicks/lpv/atc/ic/purchases/value 不為 0（除非真的為 0）
   - `report_summary.tables.top_ads_by_roas` 只包含「每個 ad 一列」（不是每天一列）
2. Skill 2（素材疲勞）：
   - 能算出 Hook Rate（3-sec / impressions）
   - 能算出 CTR 前半週 vs 後半週（使用 daily rows）
3. Skill 3（預算規則）：
   - 能讀到 budget / ends / delivery，且對 Ongoing 與日期都能處理

---

## 5) 建議後續（非阻斷，但會大幅提升穩定性）

- 匯出加入 `Ad ID` / `Ad set ID` / `Campaign ID`
- 若要「只匯出兩份檔」又要日/週共用：維持目前格式即可（daily rows + account total row），但工程端必須做聚合與 drop total row
