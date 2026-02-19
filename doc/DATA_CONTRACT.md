<!-- 檔案用途：定義 Unified Schema 的資料契約（Data Contract），說明欄位語意、驗證規則與使用方式。 -->

# Unified Ad Data — Data Contract

本文件定義 `schemas/unified_ad_data.json` 的用途與欄位語意，作為各平台資料（Meta/Shopee/MOMO）匯入後的**統一資料契約**。

## 1. 為什麼需要 Unified Schema

- **跨平台對齊**：不同平台欄位名稱不同，但報表/KPI 計算需要一致的輸入欄位。
- **可驗證**：用 JSON Schema (draft 2020-12) 把「必填欄位、型別、最小值」寫死，避免資料漂移。
- **可擴充**：允許額外欄位（例如 `source.*`、平台特有指標）以保留溯源資訊，但不影響核心欄位驗證。

## 2. Schema 結構

`unified_ad_data` 以物件包裝輸出，核心資料放在 `data` 陣列。

- `data[]`：每筆為一個「廣告層級」的資料點（campaign / adset / ad）。

## 3. 欄位定義（Record：`data[]` 每筆）

### 3.1 必填欄位

- `platform`：平台代碼，固定為 `meta` / `shopee` / `momo`
- `level`：資料層級，固定為 `campaign` / `adset` / `ad`
- `id`：該層級的唯一識別值
  - 若平台匯出包含 ID 欄位，應優先使用原始 ID
  - 若無原始 ID，允許使用穩定衍生 ID（例如由 name + time_range 的雜湊產生）
- `name`：名稱（不可為空字串）
- `time_range.start`、`time_range.end`：報表日期範圍（`YYYY-MM-DD`）
- `currency`：幣別，預設 `TWD`

### 3.2 指標欄位（`metrics`）

- `metrics.spend`：花費金額（>= 0）
- `metrics.impressions`：曝光（>= 0，整數）
- `metrics.clicks`：點擊（>= 0，整數）

#### conversions（轉換：雙口徑）

`metrics.conversions` 以雙口徑表示轉換：

- `metrics.conversions.truth`：真值口徑（例如「網站直接」）
- `metrics.conversions.platform`：平台口徑（平台歸因/平台報表）

每個口徑都有：

- `count`：轉換次數（>= 0，整數）
- `value`：轉換金額（>= 0，數值）

#### funnel（漏斗事件）

`metrics.funnel` 用來承接漏斗事件（>= 0，整數）：

- `atc`：Add to cart
- `ic`：Initiate checkout
- `lpv`：Landing page view

## 4. 驗證規則摘要（JSON Schema）

Schema 層級的關鍵驗證規則如下：

- `data` 必須存在且至少 1 筆
- Record 必填：`platform`、`level`、`id`、`name`、`time_range`、`currency`、`metrics`
- `time_range.start/end` 必須符合 `YYYY-MM-DD`
- 所有金額/次數欄位皆為 `>= 0`

## 5. 使用方式（Adapters）

Adapters（例如 `scripts/adapters/meta_adapter.py`）負責：

1. 讀取平台原始 CSV/Excel
2. 清洗（移除總計列、空值轉 0、欄位名稱正規化）
3. 轉換為 Unified 格式並輸出 JSON
4. （可選）用 `scripts/validator.py` 依 `schemas/unified_ad_data.json` 進行驗證
