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
| Idx-009 | Terminal 管理完整方案 | P0 | 🔄 進行中 | GitHub Copilot | ⏳ 待 QA | 2026-01-12-v1 | `.agent/logs/Idx-009_log.md` | Terminal Manager + Codex CLI 整合 + Role Selection Gate |
| Idx-010 | Agent Architecture Enhancement - Research/Reviewer/UI-UX Gates | P0 | ✅ 已完成 | GitHub Copilot | PASS | 1.0.3 | `.agent/logs/Idx-010_log.md` | 三個條件式 Gate + 機械化判定規則 |
| Idx-011 | Skills System Enhancement - 9 builtin skills + graceful degradation | P0 | ✅ 已完成 | GitHub Copilot | PASS | 1.0.0 | `.agent/logs/Idx-011_skills_system_enhancement_log.md` | 9 個 builtin skills 完成 + manifest_updater + plan_validator |
| Idx-012 | JSON Schema Validation & VSCode System Config | P0 | ✅ 已完成 | GitHub Copilot | PASS | 1.0.0 | `.agent/logs/Idx-012_skills_schema_validation_and_evaluation_log.md` | 7 個 JSON schemas + graceful degradation + VSCode system files |
| Idx-013 | One-Click Restore Hardening - Env vars + Extensions Sync | P1 | ✅ 已完成 | GitHub Copilot | PASS | 1.0.0 | `.agent/plans/Idx-013_one_click_restore_hardening.md` | 移除硬編碼 token + extensions 三方一致性檢查 + CI workflow |
| Idx-014 | One-Click Restore Reproducibility Hardening | P1 | 🔄 進行中 | GitHub Copilot | ⏳ 待 QA | 1.0.0 | `.agent/logs/Idx-014_log.md` | 可重現性補強：base image digest pin + restore verify 工具鏈 |
| Idx-015 | Full-Fidelity Restore via Pinned Devcontainer Image (GHCR) | P1 | 🔄 進行中 | GitHub Copilot | ⏳ 待 QA | 1.0.0 | `.agent/logs/Idx-015_log.md` | GHCR 發佈 pinned image + 新機器 digest pin 流程 |
| Idx-018 | Dev-Team Folder Segregation & File Ownership (Dual Index) | P0 | ✅ 已完成 | OpenCode | PASS | 1.0.0 | `.agent/logs/Idx-018_log.md` | segregate dev-team files from project (方案 B) |
| Idx-019 | Sync Template Repo with Ivyhousetw-META Workflow (Remove SendText Bridge) | P1 | 🔄 進行中 | codex-cli | PASS | 2026-01-19-v1 | `.agent/logs/Idx-019_log.md` | QA PASS（Round 2）：blocking issues 已於 template commit `3d61350` 修復；可建立 PR 並進入 Cross-QA |

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
