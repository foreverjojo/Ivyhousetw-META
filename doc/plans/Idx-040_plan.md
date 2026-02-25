# Plan: Idx-040

**Index**: Idx-040
**Created**: 2026-02-24
**Planner**: GitHub Copilot (Coordinator)

---

## 🎯 目標

把 `meeting.md` 的前段改成你已確認的 A~E 決策導向格式（含 Ad Set/Ad 表現、LPV/Click、CPP vs 客單損益平衡點、原因+門檻），並同時修正 deterministic fallback 的 `decisions` 生成策略，避免「Meeting Summary 與 Key Insights 幾乎一樣」的重複現象。

---

## 📋 SPEC

### Goal
1. `meeting.md` 開頭輸出固定段落 A~E：
   - A：這週先講重點（1–2 分鐘版，含 Spend/購買/平台回傳/官網營收/CTR/CPC/頻次/LPV/Click）
   - B：Ad Set 表現對比（表格）+ 每個 adset 的一句話判讀
   - B+：Ad（素材）表現（按 adset 分組，每組列 Top 1–2 + 需要處置 0–1）
   - B2：損益平衡點（CPP vs 客單；顯示安全墊倍數或成本占比）
   - C：今天立刻要做的調整（每條都含：動作 / 原因 / 驗收門檻 / 停損）
   - D：下次回來我看這 5 個數字（CPP、ROAS、CTR、LPV/Click、頻次）
   - E：風險檢查（對帳 + 疲勞）含決策樹/分級應對
2. deterministic fallback 產出的 `workflow_state.decisions` 不再「直接改寫 executive_summary」，而是優先使用 `report_insights.actions` / 顧問 next_7d_actions 產生「可執行」且與 Key Insights 不重複的決策項。
3. `report_summary.tables.top_ads_by_roas / worst_ads_by_roas` 補齊可選欄位 `adset_name`（若來源 CSV 有此欄位），以支援 meeting renderer 做「每個 adset 內的 ad 分析」。

### Non-goals
- ❌ 不改 UI/頁面結構（Streamlit tabs/sidebar 不動），僅改 `meeting.md` 內容渲染。
- ❌ 不改 LLM prompt/模型選型，不追求讓模型產出更長；以 deterministic renderer 控制格式。
- ❌ 不引入新依賴套件。
- ❌ 不新增額外報表檔案（僅在既有 artifacts 內更新 `meeting.md` 與相容欄位）。

### Acceptance Criteria
1. `meeting.md` 在「策略快照」後，出現 A~E 五段落標題，且 C/D/E 含原因與門檻。
2. `meeting.md` 含 Ad Set 表格，並含「按 adset 分組」的 Ad（素材）表現摘要（每組至少 1 則 ad，最多 3 則）。
3. `meeting.md` 含 LPV/Click 指標（若資料缺失，顯示可讀的缺失提示，不得顯示大量「（待補）」）。
4. `meeting.md` 含損益平衡點資訊：使用 `web.aov_twd_calc` 優先；若為 0 或缺失，回退到 `meta.aov_platform_twd_calc`；若仍缺失，顯示「（缺 AOV，無法計算）」並不中斷。
5. deterministic fallback 產出的 `workflow_state.decisions` 不得逐條等同於 `report_insights.executive_summary`（新增回歸測試保護）。
6. `pytest` 相關測試通過，且新增/更新測試涵蓋：A~E 段落存在、fallback decisions 去重、adset/ad 區塊渲染不出現 placeholder。

### Edge cases
- `report_insights` 為 error payload（`{"status":"error",...}`）：A 段仍可照 `report_summary` 輸出，Key Insights 區塊仍顯示 actionable warning。
- `report_summary.tables` 缺欄位或空陣列：Ad Set / Ad 段落輸出「（資料不足，建議重跑 Step B）」而非 crash。
- Ads 表格缺 `adset_name`：meeting renderer fallback 改為「不分組」列出 top/worst ads（並提示可透過 Idx-040 的 kpi_calc 改動補齊）。
- `web.aov_twd_calc` = 0：損益平衡點改用 platform AOV；兩者皆無則跳過計算。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- `examples/meeting_summary_style_analysis.md`（你指定的 A~E 模板與原則）
- `examples/chatgpt.txt`、`examples/gemini.txt`（語氣/篇幅參考）
- `scripts/moderator_meeting.py`（meeting.md deterministic renderer）
- `scripts/moderator_fallback.py`（deterministic workflow_state fallback；目前造成 decisions/exec_summary 重疊）
- `scripts/kpi_calc.py`（report_summary.tables 產生；已含 top_ads/worst_ads，但缺 adset 關聯欄位）
- `tests/test_moderator_meeting_key_insights_fallback.py`、`tests/test_moderator_meeting_consultant_summary.py`（既有 meeting 渲染測試基礎）

### Assumptions
- ✅ VERIFIED：`report_summary.tables` 目前同時提供 adset 與 ad 層級的 top/worst ROAS 表。
- ⚠️ RISK: unverified：Meta 匯出的 Ads CSV 一定含 adset name 欄位（若沒有，`adset_name` 只能留空）。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `scripts/moderator_meeting.py` - 週會 markdown 改為 A~E 版型，並保留既有後段章節作附錄。
- `scripts/moderator_fallback.py` - 調整 decisions fallback 來源優先序，避免複製 executive_summary。
- `scripts/kpi_calc.py` - 在 ads 的 top/worst 表格 row 內新增可選欄位 `adset_name`（若可解析）。
- `tests/test_moderator_meeting_key_insights_fallback.py` - 依新段落結構調整斷言定位。
- `tests/`（新增或修改 1–2 個測試檔）- 覆蓋 A~E 段落與 decisions 去重回歸。
- `doc/Implementation_Plan_index.md` - 新增 Idx-040 任務列（避免 state gate/稽核缺項）。

### Done 定義
1. ✅ 新 meeting renderer 產出的 meeting.md 前段符合你確認的 1500 字左右風格（A~E + adset/ad + 原因/門檻）。
2. ✅ fallback decisions 不再與 Key Insights 重複（以測試保護）。
3. ✅ ruff/pytest 全綠（至少 `pytest tests/ -q`）。

### Rollback 策略
- **Level**: L2
- **前置條件**: worktree 乾淨或可辨識本任務變更。
- **回滾動作**: `git restore --worktree --staged -- .`（由 Project terminal / SCM 執行）。

### Max rounds
- **估計**: 2（Engineer 1 回合 + Fix 1 回合）
- **超過處理**: 超過 2 回合仍未穩定 → 停止擴改，改以「最小可用」先合併 meeting 版型，fallback 決策去重拆到新 Idx。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| scripts/moderator_meeting.py | 修改 | 以 deterministic 方式輸出 A~E 段落；加入 adset/ad 表現區塊與損益平衡點；保留既有 Guardrail/KPI/Key Insights/Actions 等附錄段落 |
| scripts/moderator_fallback.py | 修改 | decisions fallback 改由 report_insights.actions / consultant next_7d_actions 組裝，避免複製 executive_summary |
| scripts/kpi_calc.py | 修改 | Ads top/worst rows 新增可選欄位 `adset_name`（若欄位存在） |
| tests/... | 修改/新增 | 新增 A~E 段落存在性測試；新增 decisions 去重測試；調整既有測試定位 |
| doc/Implementation_Plan_index.md | 修改 | 登記 Idx-040 任務列 |

---

## 📝 邏輯細節

### 1) meeting.md 新格式（scripts/moderator_meeting.py）
- 將原本 `## Meeting Summary（做 / 不做 / 延後）` 改為：
  - `## A. 這週先講重點（1 分鐘版）`
  - `## B. Ad Set 表現對比`
  - `## B+. Ad（素材）表現（按 adset）`
  - `## B2. 損益平衡點（CPP vs 客單）`
  - `## C. 今天立刻要做的調整（照做就好）`
  - `## D. 下次回來我看這 5 個數字（驗收門檻）`
  - `## E. 風險檢查（必做 2 件事）`
- A 段數字來源（全部 deterministic）：
  - Spend / Purchases / CTR / CPC / Frequency：`report_summary.kpi.meta.*`
  - LPV/Click：`report_summary.kpi.meta.funnel.landing_page_views` / `...link_clicks`
  - 平台回傳金額/平台 ROAS：`meta.platform_purchase_value_twd` / `meta.roas_platform_calc`
  - 官網營收/訂單/客單：`report_summary.kpi.web.*`
- B 段 Ad Set 表格來源：`report_summary.tables.top_adsets_by_roas`（依 spend>0 過濾，最多 6 列）
  - 排序策略：優先用 truth ROAS；若 `meta.purchase_value_twd==0` 或 truth ROAS 全為 0，改用 `roas_platform` 由高到低排序（並在段落中註明「因追蹤回傳異常，暫以平台口徑排序」）。
- B+ 段 Ad 表現來源：
  - 首選：`report_summary.tables.top_ads_by_roas` + `worst_ads_by_roas` 合併後按 `adset_name` 分組（每組最多 3 則）
    - 排序策略同上：truth ROAS 無法辨識時，以 `roas_platform` 排序。
  - fallback：若無 `adset_name`，先不分組，列出 Top 3 + 需要處置 2
- B2 損益平衡點：
  - AOV 優先 `web.aov_twd_calc`；若為 0 → 用 `meta.aov_platform_twd_calc`；兩者皆缺則跳過。
  - 顯示：`CPP / AOV`（成本占比）與 `AOV / CPP`（安全墊倍數）。
- C/D/E 的門檻與動作：
  - 固定沿用你確認的版本（CPP ≤ 320、平台 ROAS ≥ 5、CTR ≥ 2.5、LPV/Click ≥ 90%、頻次 < 2.0）
  - 內容來源：以 adset/ads 表現與 `report_insights.actions`（若存在）補足「原因/停損」語句；但不得捏造不存在的數字。
- 保留原本章節作附錄：Guardrail Check、KPI Snapshot、Key Insights、三顧問摘要、Department Actions、Risks、Validation Plan。

### 2) decisions fallback 去重（scripts/moderator_fallback.py）
- 現況：decisions 以 `executive_summary` 為主 → 會與 Key Insights 重複。
- 改法（優先序）：
  1. `report_insights.actions`：轉為 decisions（dict 形狀，含 action/reason/impact 或 kpi/stoploss）
  2. `consultant_notes.*.next_7d_actions`：補足「可執行」項
  3. `data_issues`：只用於「延後/風險」類 decisions（避免重複洞察）
  4. 最後才用一條通用決策（例如：先對帳/修追蹤）
- 新增測試：確保 deterministic decisions 不等於 executive_summary（字串包含關係亦需避免）。

### 3) Ads rows 補 adset_name（scripts/kpi_calc.py）
- 在 `calc_top_tables()` 內針對 ads_df：
  - 解析 ads_df 的 `adset_name` 欄位（alias-aware）
  - 在 add_roas 結果保留 `__adset_name`，並在 `to_records()` 輸出 `adset_name`（若存在）
- 相容性：schema `additionalProperties: true`，新增欄位不破壞既有 consumers。

---

## ⚠️ 注意事項
- **避免臆測**：meeting 內容只引用 `report_summary/report_insights/workflow_state` 已存在的數字與文字；無資料時用「資料不足/建議重跑 Step」提示。
- **長度控制**：renderer 需限制列數（adset ≤6、每 adset ads ≤3、actions ≤6），避免 meeting.md 暴增。
- **測試穩定性**：測試應以「段落標題存在、區塊不含 placeholder、關鍵字存在」為主，避免對完整文字內容做 brittle 斷言。

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-02-24 17:57:53 +0000
plan_approved: 2026-02-24 19:14:19 +0000
scope_policy: strict
expert_required: true
expert_conclusion: ✅ 通過（含風險提示）：ROAS/CPP/CTR/CPC/LPV/Click/AOV 計算口徑正確；AOV 優先 web.aov_twd_calc、fallback meta.aov_platform_twd_calc，並需 guard 除以 0。注意 website_purchase_value_twd 可能為 0（追蹤/回傳異常）時，meeting 必須明確標註平台/官網口徑差異，避免誤讀。
execution_backend_policy: extension-sendtext-required
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: proposed_api_monitor
executor_tool_version: unknown
executor_user: unknown
executor_start: unknown
executor_end: unknown
session_id: N/A
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: 0.104.0
qa_user: vscode
qa_start: 2026-02-25T13:32:00Z
qa_end: 2026-02-25T13:32:47Z
qa_result: PASS
qa_compliance: ✅ 符合（qa_tool=codex-cli != last_change_tool=opencode）

# 收尾
log_file_path: doc/logs/Idx-040_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 用戶確認

- [ ] Spec 已確認，可進入 Step 2 (Meta Expert)
- [ ] Expert Review 需要/不需要（預設需要，因涉及指標與決策呈現）
- [ ] Engineer Tool 已選擇：`[codex-cli|opencode]`
- [ ] QA Tool 已選擇：`[codex-cli|opencode]`（必須 ≠ last_change_tool）
- [ ] Execution Backend Policy 已確認：`extension-sendtext-required`
- [ ] Monitor Backend Policy 已確認：`proposed-primary-with-extension-fallback`
