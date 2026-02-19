# 📊 MOMO ADS 報表分析與交叉驗證報告

此報告旨在提供 MOMO ADS 報表結構分析結果，供 Codex (或工程團隊) 進行交叉驗證與實作參考。

## 1. 檔案結構分析

| 檔案名稱 | 格式 | 內容層級 | 適用性 | 結論 |
|:---|:---|:---|:---|:---|
| `momo廣告素材報表.xlsx` | XLSX | 商品 (Sku) | ⭐⭐⭐⭐⭐ | **採用 (Primary)**<br>包含完整的商品編號、花費、轉換與 **ATC (加購)** 數據。 |
| `momo廣告活動類型報表.xlsx` | XLSX | 廣告類型 | ⭐⭐ | **參考 (Reference)**<br>僅區分「推薦/關鍵字」，顆粒度太粗，適合高階概覽。 |
| `momo品類分析_20260104.xls` | XLS | 商品 (Sku) | ⭐⭐⭐ | **備用 (Backup)**<br>格式較舊 (.xls)，且 Header 位於第 5 行，解析成本較高。 |

## 2. 數據邏輯驗證 (Meta Expert Review)

### ✅ 關鍵發現
1.  **商品編號 (ID)**：MOMO 直接提供 `商品編號`，可直接映射至 Unified Schema `id`，**無需**像 Meta/Shopee 使用複雜的 fallback ID 生成策略。
2.  **漏斗數據 (Funnel)**：MOMO 提供 `加入購物車數`，這比 Shopee 更完整！Schema 中的 `metrics.funnel.atc` 必須填入。
3.  **金額格式**：欄位包含千分位 (`,`) 與幣別 (NTD)，例如 `7,768.00`，需進行清理。
4.  **ROAS 計算**：
    *   公式：`商品訂購金額 (NTD)` / `已花費 (NTD)`
    *   驗證：以範例數據為例，`12,399 / 7,768 = 1.596` (報表顯示 1.60)，邏輯一致。

### ⚠️ 潛在風險
*   **日期範圍缺失**：MOMO 匯出的 XLSX 內容中**完全沒有**日期區間資訊。
    *   **解決方案**：必須依賴**檔名** (如 `_20251201-20251231`) 或由 User 手動輸入。目前的 Adapter 需具備從檔名解析日期的能力。

## 3. 開發規格建議 (Spec for Codex)

請依據此規格開發 `scripts/adapters/momo_adapter.py`：

*   **輸入**：MOMO 廣告素材報表 (.xlsx)
*   **輸出**：Unified Ad Data JSON
*   **Library**：使用 `pandas` (需安裝 `openpyxl`)
*   **關鍵邏輯**：
    *   讀取 Header = 0
    *   清洗數值 (remove `,`, `%`)
    *   Mapping:
        *   `metrics.funnel.atc` <= `加入購物車數`
        *   `metrics.conversions.platform.count` <= `訂單數`
    *   Date Parsing: 優先嘗試從檔名解析 `YYYYMMDD` 格式。

## 4. Codex 交叉驗證指令

> 當您準備好開發時，請將此文件與 `doc/FIELD_SPECS_MOMO.md` 提供給 Codex，並執行：
> `實作 momo_adapter.py 且需包含 Golden Test`
