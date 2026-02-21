# Plan: Idx-036

**Index**: Idx-036
**Created**: 2026-02-20
**Planner**: GitHub Copilot (Ivy Coordinator)

---

## 🎯 目標

將「Stage 4 三顧問交叉審核（E2）」從概念落地為可實作的規格：包含第二輪交叉審核的輸出結構（schema）、提示詞規範（prompt contracts）、與風險控管（anti-debate / evidence-first / hard limits），作為後續工程整合（Idx-037）的一致性依據。

---

## 📋 SPEC

### Goal
把 Step E 的第二輪交叉審核（3→3）定義成可驗證、可落盤、可被 Moderator 消化的「結構化輸出」。

### Non-goals
- ❌ 不在本 Idx 內改動 UI 流程（UI/pipeline 整合放在 Idx-037）
- ❌ 不新增新的 Streamlit 頁面/大型 UI 元件
- ❌ 不在本 Idx 內重做 Step E1（三顧問第一輪）既有輸出 schema（維持 `consultant_notes.v1`）

### Acceptance Criteria
1. ✅ 新增並通過 `schemas/consultant_cross_review.v1.json`（schema 合法且可被 jsonschema 驗證）。
2. ✅ 明確定義 E2 輸出 object 結構與欄位限制（數量上限/字數上限/證據引用格式）。
3. ✅ 定義 E2 prompt contracts（包含 evidence-first、禁止新增未在輸入出現的數字、避免重述 E1 原文）。
4. ✅ 提供 deterministic 的「風險控管規則」：例如重複率、critical_issues 上限、out_of_scope 條件。

### Edge cases
- 顧問輸出非 JSON 或欄位缺失 → 必須明確規範 repair/retry 行為（可沿用既有 repair 機制；具體實作放 Idx-037）。
- evidence_ref 指向不存在欄位 → 規範為 `assumptions_to_validate` 或降級標註，避免硬湊。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- `doc/Implementation_Plan_index.md`（Phase 4 Stage 4 描述）
- `doc/AGENT_COLLABORATION.md`（交叉審核鐵律/治理精神）
- `schemas/consultant_notes.v1.json`（E1 既有輸出契約）
- `schemas/workflow_state.v1.json`（Moderator 產物契約，供後續 E2 整合參考）

### Assumptions
- ✅ VERIFIED - E2 交叉審核採用你選定的「方案 1：三位顧問兩輪（3→3），Moderator 以第二輪做總結」。
- ⚠️ RISK: unverified - OpenRouter/LLM 在不同模型下對「證據引用格式」遵循度不一，需靠 schema+prompt hard limits 壓制。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `schemas/consultant_cross_review.v1.json` - 新增 E2 交叉審核 schema（本 Idx 核心交付）
- `doc/Implementation_Plan_index.md` - 已新增 Idx-036/037 列（本次已完成）
- `doc/plans/Idx-036_plan.md` - 本 Plan 文件

> 本 Idx 僅允許上述檔案。任何程式碼變更（`core/`、`scripts/`、`ui/`）一律延後到 Idx-037。

### Done 定義
1. ✅ schema 檔新增完成且可被 `jsonschema` 驗證通過。
2. ✅ SPEC 中的欄位限制/規則可直接被 Engineer 依規格實作。

### Rollback 策略
- **Level**: L1
- **前置條件**: 僅新增 schema/doc，不影響 runtime。
- **回滾動作**: 移除 `schemas/consultant_cross_review.v1.json`（若引發爭議或需改版）。

### Max rounds
- **估計**: 1
- **超過處理**: 若 schema/欄位定義仍不穩定，改為拆出 `v1`（最小必需欄位）+ `v1.ext`（可選欄位）的兩階段落地。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| schemas/consultant_cross_review.v1.json | 新增 | 定義 E2 交叉審核輸出 schema |
| doc/Implementation_Plan_index.md | 修改 | 新增 Idx-036/037 任務列（已完成） |
| doc/plans/Idx-036_plan.md | 新增 | 本 Plan |

---

## 📝 邏輯細節

### 1. schemas/consultant_cross_review.v1.json

**輸出頂層**：單一 object（每位顧問各輸出一份；落盤時可聚合為 `cross_reviews: {A:...,B:...,C:...}`）

**必填欄位**（建議最小集合，避免模型亂跑）：
- `reviewer`: `"A" | "B" | "C"`
- `reviewed_targets`: array（必須包含另外兩位顧問，例如 A 的 review 必須 reviewed_targets = ["B","C"]）
- `strengths`: 1~3 條
- `critical_issues`: 1~3 條（每條必須含 evidence_ref；若無 evidence 只能去 assumptions_to_validate）
- `assumptions_to_validate`: 0~2 條（每條必須含 validation_step）
- `recommended_edits`: 1~3 條（「改哪句/加哪條/刪哪條」格式，禁止重寫全文）
- `stoploss_or_guardrails`: 1~2 條
- `confidence`: 0~1（數值）
- `why`: 簡短理由（避免只給分數）

**證據引用規則（schema 可用 pattern 約束）**：
- `evidence_ref` 格式：`source:path.to.field`
  - 例：`report_summary.kpi.meta.platform_purchase_value_twd`

**硬限制（避免為辯而辯）**：
- `critical_issues` 最大 3
- `recommended_edits` 最大 3
- 每條字數上限（例如 300 字；以 schema 的 `maxLength` 約束）

---

## ⚠️ 注意事項

- **風險提示**：若 schema 欄位過多，模型遵循率會下降；建議先用最小集合（上述必填）落地。
- **資安考量**：不得在 evidence/輸出中洩漏任何 token、API key、raw headers。
- **相依性**：後續 Idx-037 會需要：1) `core/validation.py` 增加驗證入口；2) `ui/steps.py` 新增 E2 pipeline；3) `scripts/moderator.py` 吃進 cross_reviews。

---

## 🔗 相關資源

- `doc/Implementation_Plan_index.md`（Phase 4 Stage 4 原始規格）
- `doc/AGENT_COLLABORATION.md`（交叉審核鐵律）

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-02-20
plan_approved: 2026-02-20
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: ivyhouse_monitor_extension_fallback
executor_tool_version: pending
executor_user: pending
executor_start: pending
executor_end: pending
session_id: pending
last_change_tool: pending

# QA 執行
qa_tool: codex-cli
qa_tool_version: pending
qa_user: pending
qa_start: pending
qa_end: pending
qa_result: pending
qa_compliance: pending

# 收尾
log_file_path: doc/logs/Idx-036_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

**預期 Rollback Level**: L1

---

## ✅ 用戶確認

- [ ] Spec 已確認，可進入 Idx-037（工程整合）
- [ ] Idx-037 的 executor_tool 已選擇（codex-cli 或 opencode）
- [ ] Idx-037 的 qa_tool 已選擇（必須 ≠ last_change_tool）
