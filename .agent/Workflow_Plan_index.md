# Dev-Team Workflow Plan Index

> 本 Index 追蹤「dev-team workflow 本身的改善與治理」相關的 plan。
> 專案功能開發的 plan 請見 `doc/Implementation_Plan_index.md`。

## 遷移對照表

以下 workflow 任務原本在 `doc/Implementation_Plan_index.md`，於 2026-01-19 遷移至此：
- Idx-009 ~ Idx-015：workflow 治理與基礎設施任務
- Idx-018：資料夾隔離與雙 Index 架構

**注意**：Idx-016（Trace ID）和 Idx-017（MCP Roadmap）是專案功能任務，保留在 `doc/Implementation_Plan_index.md`

---

## 📊 任務追蹤表（Workflow & Governance）

> 本表追蹤 dev-team workflow、agents、skills、治理相關的改善任務。

| Index | 任務標題 | 優先級 | Status | Executor Tool | QA Result | Plan Version | Log 檔 | 備註 |
|-------|----------|--------|--------|---------------|-----------|-------------|--------|------|
| Idx-009 | Terminal 管理完整方案 | P0 | ✅ 已完成 | GitHub Copilot | PASS | 2026-01-12-v1 | `.agent/logs/Idx-009_log.md` | Terminal Manager + Codex CLI 整合 + Role Selection Gate |
| Idx-010 | Agent Architecture Enhancement - Research/Reviewer/UI-UX Gates | P0 | ✅ 已完成 | GitHub Copilot | PASS | 1.0.3 | `.agent/logs/Idx-010_log.md` | 三個條件式 Gate + 機械化判定規則 |
| Idx-011 | Skills System Enhancement - 9 builtin skills + graceful degradation | P0 | ✅ 已完成 | GitHub Copilot | PASS | 1.0.0 | `.agent/logs/Idx-011_skills_system_enhancement_log.md` | 9 個 builtin skills 完成 + manifest_updater + plan_validator |
| Idx-012 | JSON Schema Validation & VSCode System Config | P0 | ✅ 已完成 | GitHub Copilot | PASS | 1.0.0 | `.agent/logs/Idx-012_skills_schema_validation_and_evaluation_log.md` | 7 個 JSON schemas + graceful degradation + VSCode system files |
| Idx-013 | One-Click Restore Hardening - Env vars + Extensions Sync | P1 | ✅ 已完成 | GitHub Copilot | PASS | 1.0.0 | `.agent/plans/Idx-013_one_click_restore_hardening.md` | 移除硬編碼 token + extensions 三方一致性檢查 + CI workflow |
| Idx-014 | One-Click Restore Reproducibility Hardening | P1 | ✅ 已完成 | GitHub Copilot | PASS | 1.0.0 | `.agent/logs/Idx-014_log.md` | 可重現性補強：base image digest pin + restore verify 工具鏈 |
| Idx-015 | Full-Fidelity Restore via Pinned Devcontainer Image (GHCR) | P1 | ✅ 已完成 | GitHub Copilot | PASS | 1.0.0 | `.agent/logs/Idx-015_log.md` | GHCR 發佈 pinned image + 新機器 digest pin 流程 |
| Idx-018 | Dev-Team Folder Segregation & File Ownership (Dual Index) | P0 | ✅ 已完成 | OpenCode | PASS | 1.0.0 | `.agent/logs/Idx-018_log.md` | segregate dev-team files from project (方案 B) |
| Idx-019 | Sync Template Repo with Ivyhousetw-META Workflow (Remove SendText Bridge) | P1 | ✅ 已完成 | codex-cli | PASS | 2026-01-19-v1 | `.agent/logs/Idx-019_log.md` | QA PASS（Round 2）：blocking issues 已於 template commit `3d61350` 修復；已建立 PR，可進入 Cross-QA |
| Idx-020 | Auto-start Codex/OpenCode in visible interactive terminals via sendText | P1 | ✅ 已完成 | GitHub Copilot | PASS | 2026-01-20-v1 | `.agent/logs/Idx-020_log.md` | local VS Code extension：自動啟動兩個專屬 terminal，指令下達僅使用 terminal.sendText；提供安裝腳本 |
| Idx-021 | Restore service_manager --pty + add OpenCode retry recovery | P0 | ✅ 已完成 | opencode | PASS | 2026-01-20-v1 | `.agent/logs/Idx-021_log.md` | 不再追溯：歷史 log 缺失，僅補占位以維持稽核鏈 |
| Idx-022 | SendText + read terminal output (Codex /status capture) | P0 | 🔄 進行中 | opencode | T.B.D. | 2026-01-20-v1 | （尚未產出） | 原預期 log：.agent/logs/Idx-022_log.md |
| Idx-023 | Workflow Loop：sendText 編排（Engineer→QA→Fix 直到 PASS）+ 落檔輪詢 | P0 | ✅ 已完成 | opencode | PASS | 2026-01-20-v1 | `.agent/logs/Idx-023_log.md` | 不再追溯：歷史 log 缺失，僅補占位以維持稽核鏈 |
| Idx-024 | Workflow Loop Reliability Hardening（ready/retry/observability） | P0 | 🔄 進行中 | opencode | T.B.D. | 2026-01-21-v1 | `.agent/logs/Idx-024_log.md` | 修補 workflow loop：以 ready gate 取代固定 sleep，加入注入重試與 events log，降低「停在啟動畫面不執行」風險；目前僅 [ENGINEER_DONE]，尚無 [QA_DONE] |
| Idx-025 | Restore/Standardize HTTP SendText Bridge (Chat→sendText) | P0 | ✅ 已完成 | opencode | PASS | 2026-01-21-v1 | `.agent/logs/Idx-025_log.md` | 不再追溯：歷史 log 缺失，僅補占位以維持稽核鏈 |
| Idx-026 | SendText Bridge Hardening + Evidence/Docs Consistency | P0 | 🔄 進行中 | opencode | T.B.D. | 2026-01-22-v1 | （尚未產出） | 原預期 log：.agent/logs/Idx-026_log.md |
| Idx-027 | Workflow Marker Detection Hardening（避免誤判） | P0 | ✅ 已完成 | opencode | PASS | 2026-01-22-v1 | `.agent/logs/Idx-027_log.md` | 不再追溯：歷史 log 缺失，僅補占位以維持稽核鏈 |
| Idx-028 | Coordinator 主動盯進度 + Stop Workflow Loop 規則落地 | P1 | ⚠️ 有風險 | GitHub Copilot | PASS WITH RISK | 2026-01-22-v1 | `.agent/logs/Idx-028_log.md` | 不再追溯：歷史 log 缺失，僅補占位以維持稽核鏈 |
| Idx-029 | Workflow Loop：QA 完成判定韌性補強（防 wrong marker / near-miss） | P0 | ✅ 已完成 | opencode | PASS | 2026-01-22-v1 | `.agent/logs/Idx-029_log.md` | Codex CLI QA 報告：PASS（strict scope 通過）；已回填 log/index |
| Idx-030 | Workflow Loop：統一 Completion 判定（tail-only + timestamp + nonce/env） | P0 | ✅ 已完成 | opencode | PASS | 2026-01-23-v1 | `.agent/logs/Idx-030_log.md` | Plan：`.agent/plans/Idx-030_plan.md` |
| Idx-031 | 治理閉環：commit/push + log 不再追溯占位 + tasks 跨平台 | P0 | ✅ 已完成 | manual | PASS WITH RISK | 2026-01-23-v1 | `.agent/logs/Idx-031_log.md` | Plan：`.agent/plans/Idx-031_plan.md` |
| Idx-032 | 健康檢查 + extensions 同步 + 一鍵恢復對齊現況 | P0 | ✅ 已完成 | manual | PASS WITH RISK | 2026-01-23-v1 | `.agent/logs/Idx-032_log.md` | Plan：`.agent/plans/Idx-032_plan.md` |
| Idx-033 | 一鍵自檢入口 + Template workflow/skills 回推包（不含 portable） | P0 | ✅ 已完成 | manual | PASS WITH RISK | 2026-01-23-v1 | `.agent/logs/Idx-033_log.md` | Plan：`.agent/plans/Idx-033_plan.md` |
| Idx-034 | 固定終端完整 /dev 流程演練（native-primary） | P1 | ✅ 已完成 | codex-cli | PASS | 2026-02-17-v1 | `.agent/logs/Idx-034_log.md` | Demo run：固定 Codex/OpenCode 終端完成 GOAL→PLAN Gate→EXECUTE→QA→LOG |
| Idx-035 | 固定終端可視化 /dev 流程演練（terminal 可見 STEP） | P1 | ✅ 已完成 | codex-cli | PASS | 2026-02-17-v1 | `.agent/logs/Idx-035_log.md` | Visual run：terminal 顯示 STEP 1~5，固定 Codex/OpenCode 終端完成 marker |
| Idx-038 | Workflow Loop：注入穩定性修復（submit/不重啟/script 汙染防護） | P0 | ✅ 已完成 | opencode | PASS | 2026-02-20-v1 | `.agent/logs/Idx-038_log.md` | VSIX 0.0.10：PASS 後立即 stop，狀態不再卡 running |
| Idx-041 | Role Selection Gate：納入 Copilot Chat（小修正）+ 強制工具一致性 | P0 | ⚠️ 有風險 | opencode | PASS WITH RISK | 2026-02-25-v1 | `.agent/logs/Idx-041_log.md` | Plan：`.agent/plans/Idx-041_plan.md` |

### 狀態說明
- ✅ 已完成 (CLOSED)
- 🔄 進行中 (IN_PROGRESS)
- ⏳ 待處理 (NOT_STARTED)
- ⚠️ 有風險 (PASS_WITH_RISK)
- ❌ 不通過 (FAIL)

### Executor Tool 選項
- **Copilot Chat**: Moderator 主工具
- **Codex CLI**: 代碼執行（VS Code Terminal）
- **OpenCode**: 代碼執行（VS Code Terminal）
- **Manual**: 手動操作

### QA Result 選項
- **PASS**: 全部通過，可合併
- **PASS WITH RISK**: 通過但有記錄風險
- **FAIL**: 不通過，需重做
