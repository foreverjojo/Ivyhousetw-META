# QA 審查報告（Agent）

本文件依照 `ivy_house_rules.md` 審查下列檔案：
- `scripts/skills/creative_fatigue.py`
- `scripts/skills/budget_rules.py`

審查項目：
1. 無 Hard-code Key（API Key/Token/密碼等敏感資料不得寫入源碼）
2. 有中文檔案註釋（檔案第一段註釋需說明用途/職責，且依規範需使用繁體中文）
3. 邏輯與錯誤處理是否完善

---

## 一、整體結論

- Hard-code Key：兩支檔案皆未發現疑似 API Key/Token/密碼等敏感字串（符合）。
- 中文檔案註釋：兩支檔案的檔頭 docstring 含英文標題（不符合「註解/文檔需繁中」規範）。
- 邏輯/錯誤處理：整體架構清楚、採用安全除法與型別轉換；但存在「欄位對應不一致」與「0 值被誤判為 None」等可導致報表失真之問題（建議修正）。

---

## 二、逐檔審查

### A. `scripts/skills/creative_fatigue.py`

#### 1) 無 Hard-code Key
- 結果：未發現 API Key/Token/密碼等敏感資訊硬編碼（符合）。

#### 2) 中文檔案註釋
- 現況：檔頭 docstring 第 2 行為英文：`Creative Fatigue Diagnostic Skill (Deterministic)`（不符合繁中規範）。
- 影響：違反 `ivy_house_rules.md`「所有程式碼註解、文檔說明嚴格使用繁體中文」。
- 建議：將檔頭 docstring 全面改為繁體中文；若需保留英文欄位名稱（例如 CSV 欄位），可在繁中描述中以「欄位原文」方式呈現，但避免英文作為敘述句。

#### 3) 邏輯與錯誤處理

**優點**
- 有 `_to_float()`、`_safe_div()` 避免型別錯誤與除以 0（穩定性佳）。
- 在 `ads_df_records` 為空或無足夠曝光樣本時，會回傳可讀的建議與 warnings（可用性佳）。

**主要問題（建議優先修正）**
- 欄位對應不一致：`_check_missing_video_fields()` 允許多種欄位名稱（如 `3-second video plays`、`ThruPlays`），但 `_extract_ad_metrics()` 實際只讀取 `video_3s`/`thruplays`（第 104–122 行 vs 第 69–101 行）。
  - 影響：即使資料中有 `3-second video plays`，也可能被當成 0，導致 Hook/Hold Rate 失真，且高潛力判斷偏誤。
  - 建議：統一「欄位別名」解析（同一套 key mapping 同時用於缺欄檢查與實際取值）。
- 0 值被誤判為 `None`：輸出時使用 `if metrics.ctr else None`、`if metrics.hook_rate else None`（第 195–205、215–223 行）。
  - 影響：當 CTR 或比率為 0.0 時，會被輸出為 `None`，造成報表誤解（0 與未知不同）。
  - 建議：改以 `is not None` 判斷（例如 `metrics.ctr is not None`）。
- `thresholds.hook_rate_min`、`thresholds.hold_rate_min` 目前未被使用（第 41–50 行、整體邏輯）。
  - 影響：門檻值存在但未生效，容易造成規則認知落差。
  - 建議：若不使用則移除；若要使用，需明確納入「高潛力」或「最低可判讀」條件。
- 參數 `report_summary` 未被使用（第 125 行起）。
  - 影響：介面看似需要摘要但實際不讀，可能造成呼叫端誤判。
  - 建議：若未使用可移除或在輸出/警告中明確說明。

**次要問題/可改善**
- `warnings` 內使用 `missing_fields:` 英文標籤（第 145–148 行）。
  - 建議：改為繁中，例如 `缺少欄位：...`（英文欄位名稱可保留在清單中）。
- `_to_float()` 轉換失敗直接回傳 0.0 且無警告，可能掩蓋資料品質問題。
  - 建議：至少在關鍵欄位（impressions/spend/purchases）遇到非數字時加入 warnings 記錄（避免靜默歸零）。

---

### B. `scripts/skills/budget_rules.py`

#### 1) 無 Hard-code Key
- 結果：未發現 API Key/Token/密碼等敏感資訊硬編碼（符合）。
- 補充：預設門檻值（例如 `target_cpa=500.0`、`breakeven_roas=2.0`）屬業務參數，非敏感金鑰；且可由 `manual_inputs` 覆寫（可接受）。

#### 2) 中文檔案註釋
- 現況：檔頭 docstring 第 2 行為英文：`Budget Rules Skill (Deterministic)`（不符合繁中規範）。
- 建議：同上，將檔頭 docstring 全面改為繁體中文。

#### 3) 邏輯與錯誤處理

**優點**
- `_determine_action()` 規則清楚，且先以 `min_spend_for_decision` 排除樣本不足情境（合理）。
- 當 truth purchases 為 0 但 platform 有值時會切換資料源並給 warnings（第 177–181 行），避免誤判（良好）。
- 缺少門檻值時會寫入 warnings，提升可追溯性（第 159–163 行）。

**主要問題（建議優先修正）**
- 0 值被誤判為 `None`：輸出 `roas`/`cpa_twd` 使用 `if overall_roas else None`、`if overall_cpa else None`（第 196–206 行與第 254–260 行）。
  - 影響：當 ROAS=0.0 或 CPA=0.0（例如 spend=0 或 purchases 極端值）時，可能被輸出成 `None`，造成「未知」與「為 0」混淆。
  - 建議：改以 `is not None` 判斷（例如 `overall_roas is not None`）。

**次要問題/可改善**
- `report_summary` 若缺少 `kpi/meta` 結構，程式會默默以 0 計算並進入 HOLD，可能讓使用者誤以為「表現普通」而非「資料不足」。
  - 建議：當 `kpi/meta` 為空或必要欄位缺失時，補一則 warnings（例如「缺少 kpi.meta，已以 0 代入」）以避免誤解。
- `_to_float()` 轉換失敗直接回傳 0.0 且無警告（同 creative_fatigue）。
  - 建議：針對 `spend_twd/purchases/purchase_value_twd` 等關鍵值，加入資料異常警告。

---

## 三、建議修正清單（依優先序）

1. 兩檔檔頭 docstring 全面改為繁體中文（符合規範）。
2. 修正輸出欄位中「0 值被當成 None」的判斷邏輯（避免報表失真）。
3. `creative_fatigue` 統一欄位別名解析：缺欄檢查與取值需一致（避免把有值當 0）。
4. 針對關鍵欄位的數值轉換失敗，加入 warnings（避免靜默歸零導致錯判）。
