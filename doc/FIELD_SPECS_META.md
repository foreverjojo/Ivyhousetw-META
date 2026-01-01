# FIELD_SPECS_META.md
Meta 匯出報表欄位規格（Ivy House｜Meta 週會 MVP）

> Source of Truth：Meta 後台匯出 CSV（Adset 層 + Ad 層）  
> 目的：提供 Step B（deterministic KPI 計算）固定口徑；Step C/E/F 僅引用、不重算。  
> 版本：v1（對應 inputs_fingerprint.v2 / report_summary.v1）

---

## 0) 檔案清單（固定）
每週必上傳 2 份 Meta CSV：

1. **Meta Adset CSV（廣告組合層）**
2. **Meta Ads CSV（廣告層）**

> 依據：你已定案要同時上傳 Adset + Ad 兩份報表（用於「KPI 彙總 + 素材/廣告診斷」）。

---

## 1) 檔案格式假設（Importer 契約）
- 檔案格式：CSV（逗號分隔）
- 編碼：優先 `utf-8-sig`（若失敗再 fallback utf-8/cp950/big5）
- 幣別：欄位中標示 `(TWD)` 視為新台幣；`帳號名稱` 末尾可能含幣別字樣（例如 `1027...， TWD`）
- 日期：`分析報告開始` / `分析報告結束` 為 `YYYY-MM-DD` 字串
- 允許存在「總計列」：`廣告組合名稱`/`廣告名稱` 為空（NaN）或 `0` 類型值；**必須在解析時剔除，避免雙重計算**

---

## 2) 共通清洗規則（所有 Meta CSV 都要做）
### 2.1 總計列（Summary Row）剔除
- Adset CSV：`廣告組合名稱` 為空（NaN）→ 視為總計列 → 必剔除
- Ad CSV：`廣告名稱` 為空（NaN）→ 視為總計列 → 必剔除

> 推理依據：你上傳的兩份檔案第一列即為總計列（名稱為 NaN，投遞/預算等欄位為 0），若不剔除會造成 spend/轉換重複。

### 2.2 缺值與佔位符
- `-` 視為空值（常見於品質/互動率/轉換率排名）
- NaN 視為 0（適用於數值欄位）或空字串（適用於文字欄位），依欄位型別處理

### 2.3 百分比欄位口徑
- `CTR（連結點閱率）` 在匯出中為 **百分比數值**（例如 1.53 代表 1.53%），不是 0.0153  
  → 內部若需要小數，需除以 100；若只做展示，可保留原值。

### 2.4 投遞狀態（Delivery）
- `廣告組合投遞` / `廣告投遞` 常見值：`active` / `inactive`（總計列可能為 `0`）
- 若出現其他值：保留原字串、不要報錯（避免 Meta 介面更新造成崩潰）

---

## 3) Meta Adset CSV（廣告組合層）欄位規格（Schema v1）
> 檔案用途：Step B 主要 KPI 彙總（花費、曝光、點擊、LPV、ATC、IC、Purchase、Value…）＋ Adset 維度切分

### 3.1 必填欄位（缺一即報錯）
| Meta 欄位名（CSV Header） | Canonical Key | 型別 | 用途 |
|---|---|---|---|
| 分析報告開始 | report_start | string(date) | 僅用於顯示/稽核（不參與 KPI 計算） |
| 分析報告結束 | report_end | string(date) | 僅用於顯示/稽核（不參與 KPI 計算） |
| 行銷活動名稱 | campaign_name | string | 維度：Campaign |
| 廣告組合名稱 | adset_name | string | 維度：Adset（同時用於剔除總計列） |
| 花費金額 (TWD) | spend_twd | number | KPI：Spend |
| 曝光次數 | impressions | number | KPI：Impressions |
| 觸及人數 | reach | number | KPI：Reach |
| 頻率 | frequency | number | KPI：Frequency |
| 連結點擊次數 | link_clicks | number | KPI：Link Clicks |
| 連結頁面瀏覽次數 | lpv | number | KPI：LPV |
| 加到購物車次數 | add_to_cart | number | KPI：ATC |
| 開始結帳次數 | initiate_checkout | number | KPI：IC |
| 購買次數 | purchases | number | KPI：Purchases |
| 購買轉換值 | purchase_value | number | KPI：Purchase Value（ROAS 分子） |
| 帳號名稱 | account_name_raw | string | 稽核/帳號識別（可選擇解析 account_id/currency） |
| 歸因設定 | attribution_setting | string | 稽核（展示用） |

### 3.2 可選欄位（缺了不報錯）
| Meta 欄位名 | Canonical Key | 型別 | 用途 / 備註 |
|---|---|---|---|
| CPM（每千次廣告曝光成本） (TWD) | cpm_twd | number | 展示用；也可回算驗證 |
| CPC（單次連結點擊成本） (TWD) | cpc_link_twd | number | 展示用；也可回算驗證 |
| CTR（連結點閱率） | ctr_link_pct | number | 展示用（百分比）；必要時轉小數 |
| 每次連結頁面瀏覽成本 (TWD) | cplpv_twd | number | 展示用；也可回算驗證 |
| 每次購買的成本 (TWD) | cpp_twd | number | 展示用；也可回算驗證 |
| 網站直接購買次數 | website_purchases | number | 可保留；若長期為 0 不納入主 KPI |
| 網站直接購買轉換值 | website_purchase_value | number | 可保留；若長期為 0 不納入主 KPI |
| 廣告組合投遞 | adset_delivery | string | active/inactive（維運用） |
| 廣告組合預算 | adset_budget | number | 展示用 |
| 廣告組合預算類型 | adset_budget_type | string | 例如：每日 |
| 結束時間 | end_time | string | 多為空；保留不影響 |
| 開始 | start_time | string | 多為空；保留不影響 |

### 3.3 允許存在但 Step B 永遠忽略（Ignore List）
- 分析報告開始 / 分析報告結束（只做稽核顯示，不做 KPI）
- 任何未列入上述欄位表的新增欄位：允許存在、直接忽略（避免 Meta 匯出欄位變動導致崩潰）

---

## 4) Meta Ad CSV（廣告層）欄位規格（Schema v1）
> 檔案用途：素材/廣告診斷（找出高 CPA、低 CTR、低轉換率排名的廣告）  
> Step B 可用來做「Ad 維度」的 Spend/Conversion 分佈，但主 KPI 建議仍以 Adset 為主。

### 4.0 廣告層（Ad CSV）在本系統的定位（重要：避免口徑漂移）
- **Step B（report_summary.json）的總 KPI 真值口徑：以 Adset CSV 為主。**
- **Ad CSV 僅用於「素材/廣告診斷」**：找出高花費低回收、低 CTR、低轉換率排名的廣告，用於顧問與主持人提出具體優化動作。
- 若需計算 Ad 層指標（ROAS/CPA/CTR/CPC），僅作為診斷欄位或 Top/Bottom ranking 使用，**不得與 Adset 口徑加總混用**，避免因總計列、拆分邏輯、或匯出差異造成重複或失真。

> 推理依據：週會拍板的決策單位更接近 Adset（受眾/優化/預算策略）；Ad 層波動較大，適合做 winner/loser 診斷而非總 KPI 結算。

### 4.1 必填欄位（缺一即報錯）
| Meta 欄位名（CSV Header） | Canonical Key | 型別 | 用途 |
|---|---|---|---|
| 分析報告開始 | report_start | string(date) | 稽核顯示 |
| 分析報告結束 | report_end | string(date) | 稽核顯示 |
| 行銷活動名稱 | campaign_name | string | 維度：Campaign |
| 廣告組合名稱 | adset_name | string | 維度：Adset（對齊 Adset 報表） |
| 廣告名稱 | ad_name | string | 維度：Ad（同時用於剔除總計列） |
| 花費金額 (TWD) | spend_twd | number | KPI：Spend |
| 曝光次數 | impressions | number | KPI：Impressions |
| 觸及人數 | reach | number | KPI：Reach |
| 頻率 | frequency | number | KPI：Frequency |
| 連結點擊次數 | link_clicks | number | KPI：Link Clicks |
| 連結頁面瀏覽次數 | lpv | number | KPI：LPV |
| 加到購物車次數 | add_to_cart | number | KPI：ATC |
| 開始結帳次數 | initiate_checkout | number | KPI：IC |
| 購買次數 | purchases | number | KPI：Purchases |
| 購買轉換值 | purchase_value | number | KPI：Purchase Value |
| 帳號名稱 | account_name_raw | string | 稽核/帳號識別 |
| 歸因設定 | attribution_setting | string | 稽核（展示用） |

### 4.2 可選欄位（缺了不報錯）
| Meta 欄位名 | Canonical Key | 型別 | 用途 / 備註 |
|---|---|---|---|
| 目標 | objective | string | 例如：銷售（展示/稽核） |
| 品質排名 | quality_ranking | string | 允許值：高於平均/平均/低於平均 或 `-`（視為空） |
| 互動率排名 | engagement_rate_ranking | string | 同上 |
| 轉換率排名 | conversion_rate_ranking | string | 同上 |
| CPM（每千次廣告曝光成本） (TWD) | cpm_twd | number | 展示/回算驗證 |
| CPC（單次連結點擊成本） (TWD) | cpc_link_twd | number | 展示/回算驗證 |
| CTR（連結點閱率） | ctr_link_pct | number | 百分比數值（1.5=1.5%） |
| 每次連結頁面瀏覽成本 (TWD) | cplpv_twd | number | 展示/回算驗證 |
| 每次購買的成本 (TWD) | cpp_twd | number | 展示/回算驗證 |
| 網站直接購買次數 | website_purchases | number | 可保留（若長期為 0 不納入主 KPI） |
| 網站直接購買轉換值 | website_purchase_value | number | 可保留（若長期為 0 不納入主 KPI） |
| 廣告投遞 | ad_delivery | string | active/inactive（維運用） |
| 廣告組合預算 | adset_budget | number | 展示用 |
| 廣告組合預算類型 | adset_budget_type | string | 例如：每日 |
| 結束時間 | end_time | string | 多為空；保留不影響 |

### 4.3 允許存在但 Step B 永遠忽略（Ignore List）
- 分析報告開始 / 分析報告結束（只做稽核顯示，不做 KPI）
- 任何未列入上述欄位表的新增欄位：允許存在、直接忽略

---

## 5) Meta 匯出缺欄位的補齊（manual_inputs）
Meta 後台匯出目前拿不到（已確認）：
- Optimization goal
- Billing event
- Buying type
- Buying type / Billing event 等策略欄位

處理方式：
- 由 Streamlit 的 `manual_inputs` 每週人工填一次
- 寫入 `inputs.json.manual_inputs`
- Moderator 週會稿固定輸出「策略快照」段落（未填也顯示未填）

---

## 6) 匯出前快速驗收（Operator Checklist）
每次匯出後，先用「欄位名」做 10 秒檢查：

- Adset CSV 必須包含：  
  `廣告組合名稱`、`行銷活動名稱`、`花費金額 (TWD)`、`曝光次數`、`連結點擊次數`、`連結頁面瀏覽次數`、`加到購物車次數`、`開始結帳次數`、`購買次數`、`購買轉換值`

- Ad CSV 必須包含：  
  `廣告名稱`、`廣告組合名稱`、`行銷活動名稱`、`花費金額 (TWD)`、`曝光次數`、`連結點擊次數`、`購買次數`、`購買轉換值`

- 兩份 CSV 都允許第一列是總計列（名稱為空），但解析必須剔除。
