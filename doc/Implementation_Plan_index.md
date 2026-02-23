# Ivy House Meta Weekly MVP - 開發計劃與待辦清單

## 🎯 當前狀態：Phase 4 Stage 2 完成，Meta V2 核心整合達成 (100%)

**最後更新**：2026-02-23

---

## 📊 任務追蹤表（State Gate 與治理）

> 本表用於追蹤核心任務的狀態、執行者與 QA 結果。遵循五條鐵律。
>
> 📌 **Dev-Team workflow / 治理相關的 plan/log 已遷移至 `.agent/Workflow_Plan_index.md`**。
> 本 Index 僅追蹤「專案功能與交付」的任務，避免 index 混雜與路徑失效。

| Index | 任務標題 | 優先級 | Status | Executor Tool | QA Result | Plan Version | Log 檔 | 備註 |
|-------|----------|--------|--------|---------------|-----------|-------------|--------|------|
| Idx-001 | 建立 `doc/logs/` 資料夾 + Log 範本 | P0 | ✅ 已完成 | Manual | PASS | — | — | 已建立範本 `Idx-000_log.template.md` |
| Idx-002 | 更新 Index 表欄位與治理資訊 | P0 | ✅ 已完成 | Copilot Chat | PASS | 2026-01-10-v1 | `doc/logs/Idx-002_log.md` | Index 清理與統一完成 |
| Idx-003 | Workflow 治理框架落地 | P0 | ✅ 已完成 | Copilot Chat | PASS | 2026-01-10-v1 | `doc/logs/Idx-003_log.md` | 26 檔案 + smoke tests 全數通過 |
| Idx-004 | 補齊 `engineer.md` 加入「Scope 檢測 Checklist」 | P1 | ✅ 已完成 | Copilot Chat | PASS | 2026-01-10-v2 | `doc/logs/Idx-004_log.md` | 9 項檢核 + 違規處理機制 |
| Idx-005 | 建立 `.agent/execution_log.json` Schema | P2 | ✅ 已完成 | Copilot Chat | PASS | 2026-01-10-v2 | `doc/logs/Idx-005_log.md` | 會話級別 Schema + 範例檔 |
| Idx-006 | 清償 TD-001：修復 skill_converter.py 語法錯誤 | P2 | ✅ 已完成 | Copilot Chat | PASS | 2026-01-10-v3 | `doc/logs/Idx-006_log.md` | 修正縮排錯誤，TD-001 已清償 |
| Idx-007 | 補齊 Plan.md 產出規範 | P1 | ✅ 已完成 | Copilot Chat | PASS | 2026-01-10-v4 | `doc/logs/Idx-007_log.md` | 建立 plan template + 更新 workflow |
| Idx-008 | 實現 Plan Summary + 完成後刪除 plan.md | P1 | ✅ 已完成 | Copilot Chat | PASS | 2026-01-10-v5 | `doc/logs/Idx-008_log.md` | log template 加入 summary 區段 |
| Idx-016 | Trace ID 追蹤（Correlation ID） | P1 | ✅ 已完成 | OpenCode | PASS | 2026-01-18-v1 | `.agent/logs/Idx-016_log.md` | core.tracing + logger trace_id（logs 已遷移至 .agent/） |
| Idx-017 | Implementation Plan 移除 MCP Roadmap | P2 | ✅ 已完成 | OpenCode | PASS | 2026-01-18-v1 | `.agent/logs/Idx-017_log.md` | Plan 不再以 MCP 作為 roadmap 概念（logs 已遷移至 .agent/） |
| Idx-036 | 三顧問交叉審核（E2）schema 規格落地 | P0 | ✅ 已完成 | Manual | PASS | 2026-02-20-v1 | `doc/logs/Idx-036_log.md` | 交付物：`schemas/consultant_cross_review.v1.json`；commit `2310b05` |
| Idx-037 | 三顧問交叉審核（E2）工程整合（pipeline + graceful degradation） | P0 | ✅ 已完成 | OpenCode | PASS | 2026-02-20-v1 | `doc/logs/Idx-037_log.md` | Plan：`doc/plans/Idx-037_plan.md`；workflow `wf_20260221181253_dce27f` |
| Idx-038 | 修正 E2 交叉審核輸出對齊 schema（移除 schema 驗證警告） | P0 | ⏳ 待處理 | TBD | TBD | 2026-02-23-v1 | pending | Plan：`doc/plans/Idx-038_plan.md` |

### 狀態說明
- ✅ 已完成 (CLOSED)
- 🔄 進行中 (IN_PROGRESS)
- ⏳ 待處理 (NOT_STARTED)
- ⚠️ 有風險 (PASS_WITH_RISK)
- ❌ 不通過 (FAIL)

### Executor Tool 選項
- **Copilot Chat**: Moderator 主工具
- **Continue**: 備用 Moderator（複雜多輪）
- **Codex**: 代碼執行
- **Manual**: 手動操作

### QA Result 選項
- **PASS**: 全部通過，可合併
- **PASS WITH RISK**: 通過但有記錄風險
- **FAIL**: 不通過，需重做

## ✅ 已完成項目

### 核心功能 (M0-M4)

- [X] **M0**: 環境穩定與 dotenv 設定
- [X] **M1**: History 落盤與版本規則
- [X] **M2**: Deterministic KPI 計算
- [X] **M3**: LLM 洞察 + 三位顧問
- [X] **M4**: Moderator 週會模板生成

### 開發工具與規範

- [X] IDE Agent 角色定義 (`.agent/roles/`)
- [X] 開發團隊工作流程 (`.agent/workflows/dev-team.md`)
- [X] 艾薇手工坊系統開發核心守則 (`ivy_house_rules.md`)
- [X] 專案審計報告

### 程式碼品質改善

- [X] `app.py` 繁體中文註釋
- [X] 英文註解翻譯為繁體中文
- [X] **app.py 模組化重構** ✅ (1234行 → 808行)
  - [X] 建立 `utils/` 模組 (file_io, hash, week, path)
  - [X] 建立 `core/` 模組 (env, config, validation, pipeline, session)
  - [X] 建立 `ui/` 模組 (components)
  - [X] 重寫 `app.py` 使用新模組
  - [X] Bug 修復與包裝函式
  - [X] 端到端測試（一鍵快篩、一鍵 Final）

---

### Meta Ads V2 整合 ✅ (2026-01-06)

- [X] **雙語別名系統** (`column_aliases.json`): 支援全球 Meta CSV 格式
- [X] **日資料自動聚合**: 支援「單日」與「累積」格式自動轉換
- [X] **KPI 邏輯修復**: 修正 ROAS 真值取向、頻率計算、日期區間判定
- [X] **程式碼規範達標**: `kpi_calc.py` 拆分為兩模組，行數均 < 500 行

---

## 🚀 Phase 2 - 2026 AI 戰略升級（進行中）

### 1. Agent Skills (專案外部與動態獲取)

- [X] **Agent Skills 基礎架構**
  - [X] 建立 `.agent/skills/` 資料夾
  - [X] 實作 `code_reviewer.py` (自動審查代碼品質)
  - [X] 實作 `doc_generator.py` (自動生成技術文件)
  - [X] 實作 `test_runner.py` (獨立測試執行工具)
- [X] **動態技能獲取 (GitHub Explorer)**
  - [X] 實作 `github_explorer.py`：根據需求在 GitHub 搜尋 `SKILL.md` 或腳本
  - [X] 實作 **技能轉換流水線**：自動下載、安全掃描並改寫為專案規範代碼
- [X] **金鑰安全立即修補**
  - [X] 將 `ifp.env` 加入 `.gitignore` 防止洩漏
  - [X] 建立 `ifp.env.example` 範本檔 (支援 OpenRouter 共用 Key)
- [X] **Agent 角色整合**
  - [X] 在 `.agent/roles/` 對應角色中加入「GitHub 技能搜索」與「本地技能調用」指令
- [X] **環境與資安優化** ✅ 完成
  - [X] 優化 `.gitignore`，排除 `.python311/` 與大型二進位檔案 (如 `uv.exe`)
  - [X] 文件化技能安裝路徑策略 (`doc/SKILL_INSTALL_STRATEGY.md`)
  - [X] **記憶重置準備 (Memory Reset Prep)** ✅ (2026-01-06)
    - [X] 實作 `scripts/skills/reset_memory_prep.py`
    - [X] 自動備份與 Handover 文件生成
    - [X] Atomic Write 安全機制實作

### 1.5 工程補強計畫 (基於 Codex 專業審計) 🆕

> [!IMPORTANT]
> **工程補強優先級**：根據 Codex 專業團隊審計，系統性補強 7 大關鍵缺口。
> 詳細內容請參閱下方「工程補強任務」章節。

#### 🔴 P0: 立即執行（本週內）

- [X] **CI/CD Pipeline** (INFRA-001~003)

  - [X] 建立 `.github/workflows/ci.yml` 與 PR gate
  - [X] 配置 Ruff linting (`.ruff.toml`, `pyproject.toml`)
  - [X] 建立基礎測試框架 (`tests/conftest.py`, `tests/test_kpi_golden.py`)

  - **DoD**: PR 必須通過 CI 才能合併，執行時間 < 5 分鐘
- [X] **Skills 供應鏈安全** (SEC-001~005) ✅ 完成

  - [X] 建立 `doc/SKILL_SECURITY_POLICY.md`
  - [X] 實作 manifest 記錄 (`.agent/skills/skill_manifest.json`)
  - [X] 實作白名單檢查 (`.agent/skills/skill_whitelist.json`)
  - [X] 實作審計 log (`.agent/skills/audit.log`)
  - [X] 實作技能回滾功能

  - **DoD**: 每個下載的技能都有 manifest、白名單驗證、可追溯、可回滾

#### 🟡 P1: 本月完成 ✅

- [X] **統一資料模型** (DATA-001~005) ✅

  - [X] 設計 `schemas/unified_ad_data.json` ✅
  - [X] 實作 Meta to Unified 轉換器 (`scripts/adapters/meta_adapter.py`) ✅
  - [X] 建立 `doc/DATA_CONTRACT.md` ✅
  - [X] Shopee/Momo 轉換器 ✅（Phase 3 已落地）

  - **DoD**: Meta/Shopee/Momo 通路已轉換為統一格式
- [X] **驗收標準 (DoD)** (TEST-001~003) ✅

  - [X] 建立 `doc/ACCEPTANCE_CRITERIA.md` ✅
  - [X] 建立 Golden Test Files (`tests/golden/`) ✅
  - [X] 實作 KPI 計算回歸測試 ✅
  - [X] 安裝 pytest 並驗證 Golden Test 全數通過 ✅

  - **DoD**: 每個 Phase 都有明確驗收條件

#### 🟢 P2: 下個月規劃 ✅ 完成

- [X] **觀測性與監控** (OPS-001~004) ✅

  - [X] 結構化 Logging (`core/logging.py`)
  - [X] LLM 呼叫監控 (`core/llm_monitor.py`)
  - [X] Trace ID 追蹤 (`core/tracing.py`) ✅（Idx-016）
  - [X] Runbook 文件 (`doc/RUNBOOK.md`) ✅
- [X] **版本管理** (VER-001~003) ✅

  - [X] `CHANGELOG.md` (Keep a Changelog 格式，100% 繁中)
  - [X] 語意化版本 (`VERSION`)
  - [X] 自動化發布流程 (`.github/workflows/release.yml`) ✅

#### 🔴 P0: QA 報告修正 (2026-01-04) ✅ 完成

- [X] **ivy_house_rules.md 規範現代化** (QA-001)

  - [X] 從嚴格 500 行改為分級制（主程式 ≤800、UI ≤600、業務邏輯 ≤500、工具 ≤400）
  - [X] Antigravity + Codex CLI 雙重專業分析驗證

  - **DoD**: 符合業界標準（Google, Streamlit），避免過度碎片化
- [X] **語言合規 100%** (QA-002~004) ✅

  - [X] ui/steps.py 英文 docstring 改為繁中（3 處）
  - [X] CHANGELOG.md 所有標題繁中化（含 Security→資安）
  - [X] scripts/llm_insights.py 所有錯誤訊息繁中化（含 error→錯誤）

  - **DoD**: 100% 繁體中文註釋、標題、錯誤訊息

### 2. 三顧問多模態模型升級 (2026 配置 - Shared OpenRouter Key)

- [X] **模型核心切換 (透過 OpenRouter 一把金鑰調用三種模型)** ✅ 完成
  - [X] **顧問 A (數據)**: **gpt-5.2** - 強化複雜邏輯與計算
  - [X] **顧問 B (視覺)**: **gemini 3.0 pro** - 強化圖片與**原生影片分析**
  - [X] **顧問 C (策略)**: **claude opus 4.5** - 強化市場洞察與文案
  - [X] **Moderator**: 使用 **gpt-5.2** 或 **claude opus 4.5** 進行總結
- [X] **多模態 Pipeline** ✅ 完成
  - [X] 實作圖片與影片之 OpenRouter Multimodal 呼叫邏輯
  - [X] 顧問 B 自動讀取素材庫並進行成效關聯分析

### 3. 總司令模式 (Commander Mode) 建立 ✅ 完成
- [X] **協作與審核機制優化**
  - [X] 建立 `.agent/skills/use_codex.md` 指導主 Agent 協作規則
  - [X] 建立 `doc/AGENT_COLLABORATION.md` 戰略指南 (含「**交叉審核鐵律**」)
  - [X] 優化 `.agent/workflows/dev-team.md`：支援「 Antigravity 實作 vs Codex 代理」分支
  - [X] 實作「**技能注入 (Skill Injection)**」：產出的 Codex 指令自動包含角色定義與 QA 腳本呼叫
- **DoD**: 主 Agent 遇到大規模修改時，能產出具備角色意識與自動化審核腳本的 `codex edit` 複合指令。

- [X] **報告自動命名與辨識** ✅ 完成
  - [X] 自動從報表內容辨識日期範圍與 Week ID
  - [X] 自動將上傳檔案重新命名為標準格式
- [X] **媒體素材上傳與備份 (Phase 2.3 Stage 3)** ✅ 完成
  - [X] 在 `app.py` 增加素材上傳 Step A+ (含 Sanitization)
  - [X] 實作素材自動命名機制 (Material_Type_Timestamp)
  - [X] 素材同步備份至 Google Drive 與本機
- [X] **Google Drive 整合 (主儲存)** ✅ 完成
  - [X] 🔄 **方案**：採用直連 API + SA JSON 認證

  - [X] **自動子資料夾分類**：
    - [X] `reports/`：存通 CSV/JSON 報表
    - [X] `assets/images/`：存放圖片素材
    - [X] `assets/videos/`：存放影片素材
  - [X] 串接 Google Drive API (Service Account)
  - [X] 實作自動備份邏輯與 Step G UI
- [X] **Google Secret Manager (安全管理)** ✅ 完成
  - [X] 配置雲端環境變數支援
  - [X] 實施「Git 零金鑰」原則，金鑰存放於 `secrets/`

---

## 📋 Phase 3 - 多通路擴充（規劃中）

### 蝦皮整合 ✅

- [X] `scripts/adapters/shopee_adapter.py` - 蝦皮 CSV 解析器 ✅
- [X] `doc/FIELD_SPECS_SHOPEE.md` - 欄位規格文件 ✅
- [X] `tests/test_shopee_adapter_golden.py` - Golden Test ✅

### Momo 整合 ✅

- [X] `scripts/adapters/momo_adapter.py` - Momo CSV 解析器 ✅
- [X] `doc/FIELD_SPECS_MOMO.md` - 欄位規格文件 ✅
- [X] `tests/test_momo_adapter_golden.py` - Golden Test ✅

---

## 🖥️ Phase 4 - Streamlit Crew Console

### Stage 1 - 多頁面 MVP ✅ 完成 (2026-01-04)

- [X] **UI/UX 設計** ✅
  - [X] 分析官網品牌風格（Cocoa Brown #3f2f24, Gold/Sand #cea87a, Warm Cream #fbf7ef）
  - [X] 生成 4 個 UI Mockups（Dashboard, Report, History, AI Assistant）
- [X] **共用 UI 模組** ✅
  - [X] `ui/theme.py` - 品牌主題設定（174 行）
  - [X] `ui/navigation.py` - 統一側邊欄導航（101 行）
  - [X] `ui/layout.py` - 共用佈局元件（167 行）
- [X] **多頁面介面** ✅
  - [X] `pages/01_dashboard.py` - 系統首頁（133 行）
  - [X] `pages/02_report_generation.py` - 報告生成（314 行）
  - [X] `pages/03_history_viewer.py` - 歷史檢視（260 行）
  - [X] `pages/04_ai_assistant.py` - AI 助手對話（299 行）
- [X] **QA 審查通過** ✅

### Stage 2 - 工具整合（GitHub Explorer）✅ 完成 (2026-01-05)

- [X] **GitHub Explorer 工具鏈整合** ✅
  - [X] 將 `github_explorer.py` 封裝為可被工具調用的服務
  - [X] 實現 5 個工具操作：search、preview、download、list、rollback
  - [X] 成功整合 Codex CLI（透過工具註冊機制）
- [X] **工具部署與使用規範** ✅
  - [X] 建立 `.agent/mcp/` 資料夾結構（保留既有實作）
  - [X] 文件化工具使用規範（`doc/MCP_USAGE.md`，保留既有文件）


---

### Stage 3 - 即時可讀輸出 ✅ 完成 (2026-01-05)

目標：在不增加 LLM token 成本的前提下，讓使用者在 UI 上更早、更好讀地看到 Step C / Step E 的產出，同時流程不中斷繼續執行後續步驟。

- [X] **Step C：report_insights 即時可讀** ✅
  - [X] `scripts/json_to_readable.py` 實作 `render_report_insights()` (420 行)
  - [X] `ui/steps.py` 第 496, 540 行呼叫並顯示
- [X] **Step E：三顧問逐一完成即時可讀** ✅
  - [X] `render_consultant_note()` 已實作並整合
  - [X] `ui/steps.py` 第 635, 668 行呼叫並顯示
- [X] **Skeleton Screen (骨架屏)** ✅
  - [X] `render_skeleton_insight()` 已實作
- [X] **成本/一致性原則** ✅
  - [X] 自然語句由同一份 JSON 轉出
  - [X] 不新增額外 LLM 呼叫

---

### Stage 4 - 三顧問交叉審核（Red-Team Review，規劃中）

目標：提升週會決策的「穩定性 / 可辯護性 / 少踩坑」，以結構化交叉審核取代自由辯論（避免模型互相帶偏、為辯而辯）。

- **資源有限則優先執行 Stage 3**：提升使用者即時感是目前最迫切的 UI 優化。

#### 🛠️ Agent Skill 擴充 (整合至 Workflow) - ⏳ 進行中

> [!NOTE]
> 詳細技能規格請參閱：[Agent Skills 執行方針](doc/agent_skills_execution_guideline.md)

##### 🎯 Top 1：全漏斗指標樹診斷 (Metric Tree Diagnostic)
- [X] 實作 `scripts/skills/metric_tree_diagnostic.py` ✅
- [X] 輸出 JSON：ROAS/CPA/AOV 拆解、漏斗率、Website vs Platform 漂移偵測 ✅
- [X] Step C 注入：在 LLM 呼叫前執行，結果寫入上下文 ✅ (`ui/steps.py` 呼叫)

##### 🎨 Top 2：素材疲乏偵測 (Creative Fatigue + Hook/Hold)
- [X] 實作 `scripts/skills/creative_fatigue.py` ✅
- [X] 輸出 JSON：Hook Rate、Hold 指標、Fatigue 判斷與建議 ✅
- [X] Step E 顧問 B 專用：素材策略輸入 ✅

##### 💰 Top 3：預算配置與擴量規則 (Budget Allocation & Scaling)
- [X] 實作 `scripts/skills/budget_rules.py` ✅
- [X] 輸出 JSON：`[KILL]`/`[SCALE_DOWN]`/`[SCALE_UP]` + Learning Phase Guardrail ✅
- [X] Step E 顧問 C 專用：預算/投放操作規則輸入 ✅

##### 🔗 Pipeline 整合
- [X] **Step C 串接**: 在 `llm_insights.py` 呼叫並注入 `compact_input.skills` ✅
- [X] **Step E 串接**: 三顧問 prompt 分別引用對應技能 JSON ✅
- [X] **Step F 串接**: Moderator 以技能 JSON 作為「事實來源」 ✅

##### 🖥️ UI 展示
- [X] 在 Step G 增加「技能包管理員」，顯示已執行技能清單與狀態 ✅
- [X] 技能結果可視化（Top/Worst 表格、漏斗圖） ✅


---

#### ✅ 核心設計原則（必須遵守）

- **交叉審核不是辯論賽**：每位顧問只做「挑漏洞 + 給驗證/修正」，禁止追求輸贏或延伸不相關議題。
- **證據優先**：反駁/修正必須引用輸入欄位（`report_summary / report_insights / consultant_notes`）的具體欄位或數字；若缺證據只能提出假設，且必須附驗證步驟。
- **收斂優先**：每一輪交叉審核都有 strict token/字數/回合上限，超出直接截斷。
- **Moderator 做裁決**：最後由 Moderator 統一產出決策與派工，且需明示「採用/不採用」的原因與止損/驗證路徑。

#### 🔄 流程（建議落地到 Step E2）

- **Step E1（現行）**：顧問 A/B/C 各自獨立輸出 JSON（不得看到彼此內容）。
- **Step E2（新增：交叉審核 1 輪）**
  - 每位顧問拿到「其他兩位顧問的輸出摘要（或全 JSON，但建議做 compact）」後，輸出一份 `review` JSON（只做審核，不重寫整份建議）。
  - 建議順序：A→(review B/C)、B→(review A/C)、C→(review A/B)（可平行呼叫）。
- **Step F（現行）**：Moderator 讀入 `report_summary + report_insights + consultant_notes + cross_reviews` 產出最終 `workflow_state.json` + `meeting.md`。

#### 📦 交叉審核輸出規格（建議 schema：`consultant_cross_review.v1`）

每位顧問在 E2 輸出「單一 JSON object」，欄位固定且數量上限嚴格：

- `reviewer`: "A" | "B" | "C"
- `reviewed_targets`: ["A","B","C"]（不含自己）
- `strengths`: 1-3 條（每條需 `evidence_ref`）
- `critical_issues`: 1-3 條（每條需 `evidence_ref`，必須可驗證）
- `assumptions_to_validate`: 0-2 條（若無證據，必須提供 `validation_step`）
- `recommended_edits`: 1-3 條（以「改哪句/加哪條/刪哪條」形式，避免重寫整份）
- `stoploss_or_guardrails`: 1-2 條（具體可執行）
- `confidence`: 0~1（主觀信心，但必須附 `why`）

#### 🧱 規則（防互相帶偏 / 防為辯而辯）

- **Hard limits**
  - 每位顧問 E2 最多輸出：`critical_issues <= 3`、`recommended_edits <= 3`
  - 禁止重複 E1 原文超過 20%（避免把 token 花在重述）
  - 禁止新增「未在輸入出現的數字」
- **Evidence rules**
  - `evidence_ref` 格式：`source:path.to.field`（例如 `report_summary.kpi.meta.platform_purchase_value_twd`）
  - 若無 evidence：只能放到 `assumptions_to_validate`，並提供「3 天內可驗證」的步驟
- **Topic scope**
  - 僅允許針對固定議題：口徑/追蹤、預算動作、主力組合、素材方向、風險/止損、驗證計畫
  - 超出範圍一律判定為 `out_of_scope`（由 Moderator 忽略）

#### 🧑‍⚖️ Moderator 仲裁輸出規則（建議加到 workflow_state）

Moderator 針對每個「爭議點」必須輸出：
- `decision`: 採用哪一方建議（或折衷）
- `rationale`: 引用 evidence 的理由
- `rejected_options`: 未採用的選項 + 為何不採用
- `validation_plan`: 若有不確定性，給出最短驗證路徑（3/7/14 天）

#### 💰 成本與時間影響（需在 UI 呈現提醒）

- E2 會讓 Step E 的 LLM 呼叫從 3 次 → 6 次（每顧問多 1 次審核輸出），通常 **token/費用與時間都會上升**。
- 可提供開關（預設 OFF）：`enable_cross_review=true/false`，並在 UI 顯示預估 token 與延遲。
- 若成本敏感：可改成「只讓 A 交叉審核 B/C」的 Lite 版本（3 次 → 5 次）。

---

## 🗒️ 記事（不納入 Phase）

> 用途：記錄「值得留存但不必放進 Phase/Stage」的做法、指令、除錯手法與操作備忘。

| 日期       | 變更內容                                          | 狀態 |
| ---------- | ------------------------------------------------- | ---- |
| 2026-01-06 | **Meta V2 核心整合完成**：雙語別名、日資料聚合、模組拆分達標 | ✅ |
| 2026-01-05 | **Phase 4 Stage 2 完成**：工具整合（GitHub Explorer）上線 | ✅ |
| 2026-01-04 | **Phase 4 Stage 1 完成**：4 頁面 + 3 UI 模組 + 品牌主題 | ✅ |
| 2026-01-04 | P0 QA 修正完成：ivy_house_rules.md 分級制 + 語言合規 100% | ✅ |
| 2026-01-04 | P2 完成：結構化 Logging + LLM 監控 + 版本管理（CHANGELOG.md 繁中） | ✅ |
| 2026-01-04 | Phase 3 MOMO 整合完成：momo_adapter + Golden Test 通過 | ✅ |
| 2026-01-04 | Phase 3 蝦皮整合完成：shopee_adapter + Golden Test 通過 | ✅ |
| 2026-01-04 | P1 全部完成：統一資料模型、驗收標準、Golden Test 通過 | ✅ |
| 2026-01-04 | P1 Golden Test 驗證通過：安裝 pytest，修復 meta_adapter ID 問題 | ✅ |
| 2026-01-04 | Phase 2.3 全階段完成：GDrive 整合、UI 串接、Codex QA 通過 | ✅ |
| 2026-01-04 | Phase 2.3 Stage 1+2 完成：核心工具與文件同步實作 | ✅ |
| 2026-01-04 | 建立「總司令模式」與「交叉審核鐵律」(Commander Mode) | ✅ |
| 2026-01-04 | 整合工具整合戰略建議於 Phase 2.3 與 Phase 4        | 🆕   |
| 2026-01-04 | Stage 3 規劃：Step C/E 產物即時可讀顯示（不中斷流程、token 成本不變） | 🆕   |
| 2026-01-05 | 新增 Headless Debug Pipeline：`scripts/debug_pipeline.py` | 🆕 |
| 2026-01-04 | Phase 2.1 完成：GitHub Explorer + Skill Converter | ✅ |
| 2026-01-03 | 整合動態技能獲取 (GitHub Explorer) 於 Phase 2.1   | ✅ |
| 2026-01-03 | 整合 OpenRouter 單一金鑰與 2026 多模態升級細節    | ✅ |
| 2026-01-03 | 整合金鑰安全修補與 Secret Manager 計畫            | ✅ |
| 2026-01-03 | app.py 模組化重構完成                             | ✅ |
| 2026-01-02 | Gemini 支援整合                                   | ✅ |
| 2026-01-02 | 開發團隊工作流程建立                              | ✅ |
| 2026-01-06 | Memory Reset Prep Skill 完成 (Atomic Write + Handover) | ✅ |
| 2026-01-06 | Step G 技能包管理員 UI 整合完成                   | ✅ |
