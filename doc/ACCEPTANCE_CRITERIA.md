<!-- 檔案用途：定義 PR 合併的 DoD（Definition of Done）鐵律與各階段驗收標準。 -->

# Acceptance Criteria（DoD 鐵律）

本文件定義此專案在 PR 合併前必須滿足的「不可妥協」驗收標準，避免功能看似完成但資料契約/品質缺失導致後續報表失真。

## 1. DoD（合併鐵律）

PR 必須同時滿足以下全部條件才可合併：

1. **所有新增/修改檔案第一行有繁體中文用途註釋**
2. **單檔不超過 500 行**
3. **不得 Hard-code API Key/Token/密碼**（需使用 `os.getenv`）
4. **Schema 與 Adapter 互相對齊**
   - `scripts/adapters/*` 產出的 JSON 能通過 `schemas/*` 驗證
5. **測試必須通過**
   - `pytest` 全數通過（或明確標註 skip 且有原因）
6. **自審必須完成**
   - 執行 `python .agent/skills/code_reviewer.py` 並確認無紅線問題

## 2. 驗收分階段標準

### 2.1 資料契約（Data Contract）

- `schemas/unified_ad_data.json` 使用 JSON Schema draft 2020-12
- Record 必填欄位與型別符合 `doc/DATA_CONTRACT.md` 描述
- Schema 可被 `jsonschema` 正常載入與驗證

### 2.2 Adapter（Meta）

- 能讀取 Meta Adset/Ad CSV（支援常見編碼）
- **總計列必須移除**（name 空值列不進入輸出）
- 空值/非數字必須安全處理（轉為 0 或合理預設）
- 需使用 `utils/naming.py` 擷取日期範圍等元資料（最少 `time_range`）

### 2.3 測試（Golden Files）

- `tests/golden/meta_sample_input.csv` 至少 3 筆 adset 測試資料
- `tests/golden/meta_expected_output.json` 與 Adapter 產出一致
- 新增的 golden test 在 CI/本機可穩定重跑（不依賴外部 API）

### 2.4 文件

- `doc/DATA_CONTRACT.md` 清楚說明欄位語意與驗證規則
- `doc/ACCEPTANCE_CRITERIA.md` 清楚列出 PR 合併鐵律與驗收分階段標準

