# FIELD_SPECS_META.md (v1.0 locked)
Meta 週會 MVP（Replit + Streamlit + OpenRouter）

## 0) Truth Source（鎖死）
- report_summary.v1.kpi_truth_source = "meta_adset_csv"
- report_summary.v1.ad_diagnostics_source = "meta_ad_csv"
- KPI 真值：僅使用 Adset 匯總（meta_adset_csv）
- Ad 層（meta_ad_csv）僅作素材/診斷，不得作 KPI 真值

## 1) Time & Attribution（鎖死）
- timezone: Asia/Taipei
- generated_at: 必須存在（Taipei time）
- attribution_setting: 必須一致且鎖死為：
  "點擊後 7 天、瀏覽後 1 天或互動觀看後 1 天"

## 2) 必做清洗規則（鎖死）
### 2.1 總計列（Total Row）固定 drop（必然存在）
- Adset CSV：若「廣告組合名稱」為空/NaN → 視為總計列 → drop
- Ad CSV：若「廣告名稱」為空/NaN → 視為總計列 → drop
- drop 後才允許做：
  - schema validate
  - KPI 彙總
  - insight / notes / workflow_state 產出

### 2.2 空值→0 的欄位（事件數類）
下列欄位若為空/NaN，解析時一律轉 0：
- 連結點擊次數
- 連結頁面瀏覽次數
- 加到購物車次數
- 開始結帳次數
- 購買次數
- 購買轉換值
- 網站直接購買次數
- 網站直接購買轉換值

> 原因：inactive / 分母=0 / 平台輸出 NaN 很常見；我們用「欄位必存在 + 空值轉0」維持週週可跑。

### 2.3 允許空值（平台計算欄）
下列欄位允許空/NaN（但欄位必須存在）：
- CTR（連結點閱率）
- CPC（單次連結點擊成本） (TWD)
- CPM（每千次廣告曝光成本） (TWD)
- 每次連結頁面瀏覽成本 (TWD)
- 每次購買的成本 (TWD)
- 品質排名 / 互動率排名 / 轉換率排名
- 結束時間 / 開始（可能為空或文字）

## 3) KPI 定義（鎖死）
### 3.1 KPI 真值（只吃網站直接）
- website_purchases（網站直接購買次數）= sum(adset.website_purchases)
- website_purchase_value（網站直接購買轉換值）= sum(adset.website_purchase_value)
- ROAS（真值）= website_purchase_value / spend_twd

### 3.2 差異偵測欄（保留，但不當真值）
為了對帳 / 監測歸因或轉換位置漂移，仍保留平台欄位作「差異偵測」：
- purchases（購買次數）
- purchase_value（購買轉換值）
並計算：
- delta_purchase_value = purchase_value - website_purchase_value
- delta_purchase_value_rate = delta_purchase_value / max(website_purchase_value, 1)

> 這兩組都會寫進 report_summary / workflow_state（作為觀測，不作拍板 KPI）。

---

## 4) 欄位規格（Adset = KPI Truth Source）
> 欄位名（raw）以你上傳的 ivyhouse_meta_adset_2025-W49_20251204-20251209.csv 為準（共 28 欄）
> 規則：下表所有 raw 欄位「必須存在」，避免匯出漂移。

| raw_field | canonical_key | type | must_exist | nullable | allow_0 | role | notes |
|---|---|---|---|---|---|---|---|
| 分析報告開始 | report_start | date | ✅ | ❌ | ❌ | KPI | YYYY-MM-DD |
| 分析報告結束 | report_end | date | ✅ | ❌ | ❌ | KPI | YYYY-MM-DD |
| 廣告組合名稱 | adset_name | string | ✅ | ❌* | — | dim | *drop 總計列後不可空 |
| 廣告組合投遞 | adset_delivery | string | ✅ | ❌ | — | dim | 例：active |
| 廣告組合預算 | adset_budget | int | ✅ | ❌ | ✅ | diag |  |
| 廣告組合預算類型 | adset_budget_type | string | ✅ | ❌ | — | diag | 例：每日 |
| 花費金額 (TWD) | spend_twd | number | ✅ | ❌ | ✅ | KPI | sum |
| 觸及人數 | reach | number | ✅ | ❌ | ✅ | diag | sum |
| 頻率 | frequency | number | ✅ | ❌ | ✅ | diag |  |
| 歸因設定 | attribution_setting | const string | ✅ | ❌ | — | lock | const |
| 結束時間 | end_time | string | ✅ | ✅ | — | diag | 可能空/文字 |
| 開始 | start_date | date/string | ✅ | ✅ | — | diag | 可能空 |
| 曝光次數 | impressions | number | ✅ | ❌ | ✅ | KPI | sum |
| CPM（每千次廣告曝光成本） (TWD) | cpm_twd | number | ✅ | ✅ | ✅ | diag | 可空 |
| 連結點擊次數 | link_clicks | number | ✅ | ❌** | ✅ | diag | **空→0 |
| CPC（單次連結點擊成本） (TWD) | cpc_link_twd | number | ✅ | ✅ | ✅ | diag | 可空 |
| CTR（連結點閱率） | ctr_link | number | ✅ | ✅ | ✅ | diag | 可空 |
| 連結頁面瀏覽次數 | lpv | number | ✅ | ❌** | ✅ | diag | **空→0 |
| 每次連結頁面瀏覽成本 (TWD) | cost_per_lpv_twd | number | ✅ | ✅ | ✅ | diag | 可空 |
| 購買次數 | purchases | number | ✅ | ❌** | ✅ | drift | **空→0（差異偵測） |
| 每次購買的成本 (TWD) | cpp_twd | number | ✅ | ✅ | ✅ | diag | 可空 |
| 加到購物車次數 | add_to_cart | number | ✅ | ❌** | ✅ | diag | **空→0 |
| 帳號名稱 | account_name | string | ✅ | ✅* | — | dim | *總計列 drop 後建議不可空 |
| 行銷活動名稱 | campaign_name | string | ✅ | ✅* | — | dim | 同上 |
| 購買轉換值 | purchase_value | number | ✅ | ❌** | ✅ | drift | **空→0（差異偵測） |
| 網站直接購買次數 | website_purchases | number | ✅ | ❌** | ✅ | KPI | **空→0（真值） |
| 網站直接購買轉換值 | website_purchase_value | number | ✅ | ❌** | ✅ | KPI | **空→0（真值） |
| 開始結帳次數 | initiate_checkout | number | ✅ | ❌** | ✅ | diag | **空→0 |

---

## 5) 欄位規格（Ad = Diagnostics Source）
> 欄位名（raw）以你上傳的 ivyhouse_meta_ad_2025-W49_20251204-20251209.csv 為準（共 32 欄）
> 規則：下表所有 raw 欄位「必須存在」。

| raw_field | canonical_key | type | must_exist | nullable | allow_0 | role | notes |
|---|---|---|---|---|---|---|---|
| 分析報告開始 | report_start | date | ✅ | ❌ | ❌ | diag |  |
| 分析報告結束 | report_end | date | ✅ | ❌ | ❌ | diag |  |
| 廣告名稱 | ad_name | string | ✅ | ❌* | — | dim | *drop 總計列後不可空 |
| 廣告投遞 | ad_delivery | string | ✅ | ❌ | — | dim |  |
| 廣告組合預算 | adset_budget | int | ✅ | ❌ | ✅ | diag |  |
| 廣告組合預算類型 | adset_budget_type | string | ✅ | ❌ | — | diag |  |
| 花費金額 (TWD) | spend_twd | number | ✅ | ❌ | ✅ | diag |  |
| 觸及人數 | reach | number | ✅ | ❌ | ✅ | diag |  |
| 頻率 | frequency | number | ✅ | ❌ | ✅ | diag |  |
| 歸因設定 | attribution_setting | const string | ✅ | ❌ | — | lock | const |
| 結束時間 | end_time | string | ✅ | ✅ | — | diag |  |
| 品質排名 | quality_ranking | string | ✅ | ✅ | — | diag | 可空 |
| 互動率排名 | engagement_ranking | string | ✅ | ✅ | — | diag | 可空 |
| 轉換率排名 | conversion_ranking | string | ✅ | ✅ | — | diag | 可空 |
| 曝光次數 | impressions | number | ✅ | ❌ | ✅ | diag |  |
| CPM（每千次廣告曝光成本） (TWD) | cpm_twd | number | ✅ | ✅ | ✅ | diag | 可空 |
| 連結點擊次數 | link_clicks | number | ✅ | ❌** | ✅ | diag | **空→0 |
| CPC（單次連結點擊成本） (TWD) | cpc_link_twd | number | ✅ | ✅ | ✅ | diag | 可空 |
| CTR（連結點閱率） | ctr_link | number | ✅ | ✅ | ✅ | diag | 可空 |
| 連結頁面瀏覽次數 | lpv | number | ✅ | ❌** | ✅ | diag | **空→0 |
| 每次連結頁面瀏覽成本 (TWD) | cost_per_lpv_twd | number | ✅ | ✅ | ✅ | diag | 可空 |
| 購買次數 | purchases | number | ✅ | ❌** | ✅ | diag | **空→0（不得真值） |
| 每次購買的成本 (TWD) | cpp_twd | number | ✅ | ✅ | ✅ | diag | 可空 |
| 加到購物車次數 | add_to_cart | number | ✅ | ❌** | ✅ | diag | **空→0 |
| 帳號名稱 | account_name | string | ✅ | ✅ | — | dim |  |
| 目標 | objective | string | ✅ | ❌ | — | dim | 例：銷售 |
| 行銷活動名稱 | campaign_name | string | ✅ | ❌ | — | dim |  |
| 購買轉換值 | purchase_value | number | ✅ | ❌** | ✅ | diag | **空→0 |
| 網站直接購買次數 | website_purchases | number | ✅ | ❌** | ✅ | diag | **空→0 |
| 網站直接購買轉換值 | website_purchase_value | number | ✅ | ❌** | ✅ | diag | **空→0 |
| 開始結帳次數 | initiate_checkout | number | ✅ | ❌** | ✅ | diag | **空→0 |
| 廣告組合名稱 | adset_name | string | ✅ | ❌ | — | join | 用於掛回 adset |

---

## 6) Machine-readable（YAML，供 parser / tests / schema 生成）
meta:
  truth_source:
    kpi_truth_source: meta_adset_csv
    ad_diagnostics_source: meta_ad_csv
  timezone: Asia/Taipei
  attribution_setting_const: "點擊後 7 天、瀏覽後 1 天或互動觀看後 1 天"
  total_row_drop:
    adset: "廣告組合名稱 is null/empty"
    ad: "廣告名稱 is null/empty"
  required_raw_columns:
    adset:
      - 分析報告開始
      - 分析報告結束
      - 廣告組合名稱
      - 廣告組合投遞
      - 廣告組合預算
      - 廣告組合預算類型
      - 花費金額 (TWD)
      - 觸及人數
      - 頻率
      - 歸因設定
      - 結束時間
      - 開始
      - 曝光次數
      - CPM（每千次廣告曝光成本） (TWD)
      - 連結點擊次數
      - CPC（單次連結點擊成本） (TWD)
      - CTR（連結點閱率）
      - 連結頁面瀏覽次數
      - 每次連結頁面瀏覽成本 (TWD)
      - 購買次數
      - 每次購買的成本 (TWD)
      - 加到購物車次數
      - 帳號名稱
      - 行銷活動名稱
      - 購買轉換值
      - 網站直接購買次數
      - 網站直接購買轉換值
      - 開始結帳次數
    ad:
      - 分析報告開始
      - 分析報告結束
      - 廣告名稱
      - 廣告投遞
      - 廣告組合預算
      - 廣告組合預算類型
      - 花費金額 (TWD)
      - 觸及人數
      - 頻率
      - 歸因設定
      - 結束時間
      - 品質排名
      - 互動率排名
      - 轉換率排名
      - 曝光次數
      - CPM（每千次廣告曝光成本） (TWD)
      - 連結點擊次數
      - CPC（單次連結點擊成本） (TWD)
      - CTR（連結點閱率）
      - 連結頁面瀏覽次數
      - 每次連結頁面瀏覽成本 (TWD)
      - 購買次數
      - 每次購買的成本 (TWD)
      - 加到購物車次數
      - 帳號名稱
      - 目標
      - 行銷活動名稱
      - 購買轉換值
      - 網站直接購買次數
      - 網站直接購買轉換值
      - 開始結帳次數
      - 廣告組合名稱
