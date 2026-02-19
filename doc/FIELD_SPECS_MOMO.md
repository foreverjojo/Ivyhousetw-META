<!-- 檔案用途：定義 MOMO ADS 廣告報表欄位規格與 Unified Schema 對應關係 -->

# MOMO ADS 廣告報表欄位規格 (FIELD_SPECS_MOMO)

## 1. 來源檔案

- **主要來源**: `momo廣告素材報表.xlsx` (或類似格式的 xlsx)
- **Header 位置**: 第 1 行 (Index 0)
- **廣告層級**: 商品層級 (Ad Level)

## 2. 欄位映射 (Schema Mapping)

| MOMO 欄位名稱 | Unified Schema | 資料型態轉換 | 備註 |
|:--------------|:---------------|:-------------|:-----|
| **商品編號** | `id` | String | 優先使用，若無則 fallback |
| **商品名稱** | `name` | String | |
| **曝光數** | `metrics.impressions` | Int (去除 `,`) | |
| **點擊數** | `metrics.clicks` | Int (去除 `,`) | |
| **已花費 (NTD)** | `metrics.spend` | Float (去除 `,` ) | |
| **訂單數** | `metrics.conversions.platform.count` | Int | 代表成交訂單筆數 |
| **商品訂購金額 (NTD)** | `metrics.conversions.platform.value` | Float (去除 `,`) | GMV |
| **加入購物車數** | `metrics.funnel.atc` | Int | ✅ MOMO 特有漏斗數據 |
| **投入產出比** | - | - | 驗算用 (ROAS) |
| **點擊率** | - | - | 驗算用 |

> **注意：** MOMO 報表中的 `投入產出比` (ROAS) 為 `商品訂購金額 / 已花費`。
> 目前無「直接轉換」與「瀏覽轉換」區分，統一視為 `platform` 歸因。

## 3. 特殊處理邏輯

1. **日期範圍**：
   - 報表內容本身**不包含**日期範圍 (Header 上方無 Metadata)。
   - **必需**從檔名解析日期 (例如 `momo廣告素材報表_20251201_20251231.xlsx`)，或由使用者輸入。
   - **本次實作**：若檔名無日期，預設使用當下日期或留空，並發出警告。

2. **數值清理**：
   - 需處理 `1,234` (千分位)。
   - 需處理 `4.53%` (百分比)。
   - 需處理 `Nan` 或 `0.00`。

3. **Fallback ID**：
   - 若 `商品編號` 為空，使用 `hash(商品名稱)`。
