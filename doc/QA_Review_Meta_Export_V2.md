# QA 審查報告：Meta Export V2 整合（Step 4）

## 1) 審查範圍
- [NEW] `schemas/column_aliases.json`
- [MODIFY] `scripts/kpi_calc.py`

## 2) Checklist 結果
| 項目 | 結果 | 備註 |
|---|---|---|
| 無 Hard-code API Key | 未通過 | `secrets/ivyhouse-ad-analyzer-e3a920e555a7.json:5` 出現 `BEGIN [REDACTED] KEY`（高風險敏感金鑰） |
| 有中文檔案註釋 | 通過 | `scripts/kpi_calc.py:1`、`schemas/column_aliases.json` 的 `$comment` |
| 符合 `ivy_house_rules.md` | 未通過（需修正） | `scripts/kpi_calc.py` 行數 511（> 500 上限），且仍有英文段落/註解 |
| 邏輯正確（alias 查詢、fallback 機制） | 未通過（有 P0） | 日期區間推導在 v2 匯出下會錯（見問題 P0-1） |
| 向後相容（舊中文 CSV 仍可解析） | 部分通過（有風險） | alias 機制有助相容，但日期推導與部分欄位仍 hard-code 中文（見問題 P0-1 / P1-2 / P1-3） |

## 3) 發現的問題

### P0-1：`parse_date_range_from_meta()` 會取到錯誤日期區間（影響 `week_id`/`date_range`）
**現象**
- 目前 `scripts/kpi_calc.py:145` 使用 `_first_str()` 讀取「第一列」的 `Reporting starts/ends`（alias `date_start/date_end`）。
- 但 `build_report_summary()` 在更早的清洗階段會呼叫 `_drop_total_rows()` 移除「名稱空白的總計列」（`scripts/kpi_calc.py:467` 起），導致 DataFrame 的第一列變成某一天的日資料。
- 以目前 v2 範例資料為例，`examples/102796323413794-Ad-sets-Dec-4-2025-Dec-10-2025 (2).csv` 的第一筆資料是總計列（`Ad set name` 空白，區間為 2025-12-04~2025-12-10），會被移除；剩下第一筆日資料通常是最後一天（例如 2025-12-10）。結果 `date_range` 可能被錯誤縮成單日。

**影響**
- `report_summary.week_id` 與 `report_summary.date_range` 可能錯誤，進而影響後續報告歸檔與敘事。

**建議修正**
- `parse_date_range_from_meta()` 不應依賴第一列，改成在有效列上做：
  - `date_start = min(parsed(starts))`
  - `date_end = max(parsed(ends))`
- 或者：優先從原始 df 讀取總計列的區間（若存在），再進行 `_drop_total_rows()` 清洗。

**定位**
- `scripts/kpi_calc.py:145`
- `scripts/kpi_calc.py:467`

---

### P1-2：Top tables 的 `frequency` 仍 hard-code 中文欄位
**現象**
- `calc_top_tables()` 的保留欄位仍包含 `頻率`（`scripts/kpi_calc.py:358`），`to_records()` 也只讀 `頻率`（`scripts/kpi_calc.py:419`）。

**影響**
- 英文匯出欄位為 `Frequency` 時，Top tables 的 `frequency` 會是 `None`，導致素材疲乏或投放診斷（若依賴此欄位）失真。

**建議修正**
- 直接輸出 `__frequency`（已在 `add_roas()` 以 alias 解析出來，`scripts/kpi_calc.py:298`），並在 `to_records()` 讀取 `__frequency`。

**定位**
- `scripts/kpi_calc.py:298`
- `scripts/kpi_calc.py:358`
- `scripts/kpi_calc.py:419`

---

### P1-3：`ads_has_rankings` 判斷仍 hard-code 中文欄位
**現象**
- `calc_meta_kpis()` 以 `["品質排名", "互動率排名", "轉換率排名"]` 判斷（`scripts/kpi_calc.py:270`），未使用 alias。

**影響**
- 英文匯出（`Quality ranking` / `Engagement rate ranking` / `Conversion rate ranking`）會被判定為沒有 rankings，導致報告少掉可用診斷訊號。

**建議修正**
- 改用 alias keys：`quality_ranking` / `engagement_ranking` / `conversion_ranking` 來判斷存在性。

**定位**
- `scripts/kpi_calc.py:270`
- `schemas/column_aliases.json`（對應 keys 已存在）

---

### P0-Security：Repo 內存在私鑰檔案（不在本次變更清單，但會阻擋安全審核）
**現象**
- `secrets/ivyhouse-ad-analyzer-e3a920e555a7.json:5` 含 `private_key` / `BEGIN [REDACTED] KEY`。

**影響**
- 一旦外流將造成不可逆風險（GCP Service Account 私鑰）。

**建議處置**
- 立刻撤下檔案、旋轉/作廢金鑰、改用 Secret Manager 或環境變數注入，並加入 `.gitignore` 防止再次提交。

## 4) 結論
**需要修正（未通過）**
- 必修：P0-1（日期區間推導錯誤）與 P0-Security（私鑰存在 repo）。
- 建議同修：P1-2 / P1-3（alias-aware 一致性），並將 `scripts/kpi_calc.py` 拆分模組以符合 `ivy_house_rules.md` 的行數與註解語言規範。
