# Implementation Plan: Idx-003

**Index**: Idx-003
**Plan Version**: 2026-01-10-v1
**Title**: Workflow 治理框架實施
**Status**: COMPLETED
**Priority**: P0

---

## Objective

實施基於五條鐵律的多代理工作流程治理框架，補強關鍵缺口（P0），並完成重要改進（P1）和 Nice to have 項目（P2）。

---

## Background

根據 `doc/workflow_process_analysis.md` 分析，現有工作流程存在以下缺口：

### P0（關鍵缺口）
1. 任務鎖管理缺失
2. State Gate 驗證缺失
3. Git 分支管理腳本缺失
4. Log/Plans 資料夾未追蹤
5. QA Rollback SOP 缺失
6. Pre-commit hooks 缺失

### P1（重要改進）
1. 技術債務登記表缺失
2. Log 完整性驗證缺失
3. 驗證計畫到期提醒缺失
4. 安全掃描 CI Job 缺失
5. 工具切換提綱範本缺失
6. Log 錯誤資料需修正

### P2（Nice to have）
1. ADR 決策日誌系統缺失
2. 災難恢復腳本缺失
3. 性能基準測試需補強
4. 用戶反饋回路（可選）

---

## Scope

### In Scope
- 所有 P0、P1、P2 項目的實施
- 相關文檔的建立與更新
- 安全修復（GCP 私鑰洩漏）

### Out of Scope
- 用戶反饋回路（單人團隊，暫不需要）
- 舊有技術債的清償（單獨排程）

---

## Implementation Plan

### Phase 1: P0 關鍵缺口補強

#### Task 1.1: 任務鎖管理
- **檔案**: `scripts/check_active_task.py`
- **功能**: acquire, release, status, force-release
- **驗收**: 可正常取得/釋放鎖，TTL 機制運作正常

#### Task 1.2: State Gate 驗證
- **檔案**: `scripts/validate_state_gate.py`
- **功能**: 驗證 Commit Message 格式、Index 存在性、鎖一致性
- **驗收**: 正確阻擋不合規的 commit

#### Task 1.3: Git 分支管理
- **檔案**: `scripts/task_branch.py`
- **功能**: create, merge, abort
- **驗收**: 可正常建立/合併/中止任務分支

#### Task 1.4: Log/Plans 資料夾追蹤
- **檔案**: `doc/logs/.gitkeep`, `doc/plans/.gitkeep`, `doc/plans/Idx-003_plan.md`
- **驗收**: 資料夾被 Git 追蹤，範例檔案完整

#### Task 1.5: QA Rollback SOP
- **檔案**: `.agent/roles/qa.md`
- **變更**: 加入 Rollback SOP 章節
- **驗收**: SOP 清晰且可執行

#### Task 1.6: Pre-commit Hooks
- **檔案**: `.pre-commit-config.yaml`
- **Hooks**: trailing-whitespace, end-of-file-fixer, check-yaml, check-json, check-added-large-files, detect-private-key, check-ast, check-docstring-first, ruff
- **驗收**: 所有 hooks 可正常運作

---

### Phase 2: P1 重要改進

#### Task 2.1: 技術債務登記表
- **檔案**: `doc/tech_debt.md`
- **欄位**: ID, 描述, 優先級, 預估工作量, 相關 Index, 建立日期, 狀態
- **驗收**: 範本完整且易於維護

#### Task 2.2: Log 完整性驗證
- **檔案**: `schemas/log.schema.json`, `scripts/validate_log.py`
- **功能**: 驗證 Log 格式符合 Schema
- **驗收**: 可正確驗證 Log 並提示錯誤

#### Task 2.3: 驗證計畫到期提醒
- **檔案**: `scripts/check_verification_due.py`
- **功能**: 掃描 Index 中的 Verification Due Date，提前 3 天提醒
- **驗收**: 可正確識別到期項目

#### Task 2.4: 安全掃描 CI Job
- **檔案**: `.github/workflows/ci.yml`
- **變更**: 加入 `security-scan` job
- **驗收**: CI 可正常執行 safety check

#### Task 2.5: 工具切換提綱範本
- **檔案**: `.agent/templates/handoff_template.md`
- **用途**: VS Code → 其他工具切換時的上下文傳遞
- **驗收**: 範本完整且易於填寫

#### Task 2.6: Log 錯誤資料修正
- **檔案**: `doc/logs/Idx-000_log.template.md`
- **變更**: `Plan Hash` → `Plan Version`
- **驗收**: 範本正確

---

### Phase 3: P2 Nice to Have

#### Task 3.1: ADR 決策日誌系統
- **資料夾**: `doc/adr/`
- **檔案**: `README.md`, `0000-template.md`, `0001-0003` 三個 ADR
- **驗收**: ADR 結構完整，範例清晰

#### Task 3.2: 災難恢復腳本
- **檔案**: `scripts/backup_logs.py`
- **功能**: 備份、列出、還原
- **驗收**: 可正常備份/還原 logs, plans, index

#### Task 3.3: 性能基準測試
- **檔案**: `scripts/benchmark.py`
- **狀態**: 已存在，標記為完成

#### Task 3.4: 用戶反饋回路
- **狀態**: 標記為可選，暫不實施

---

### Phase 4: 安全修復

#### Task 4.1: GCP 私鑰洩漏處理
- **檔案**: `doc/gcp_key_revocation_guide.md`
- **內容**: 詳細的私鑰作廢指南
- **驗收**: 指南完整且可執行

---

## Dependencies

- Python 3.10+
- Git 2.30+
- pre-commit 3.0+

---

## Risks & Mitigations

| 風險 | 影響 | 機率 | 緩解措施 |
|------|------|------|----------|
| Pre-commit 阻擋舊技術債提交 | 高 | 高 | Ruff 只檢查高風險錯誤 (E9, F821-823) |
| 分支管理腳本與現有流程衝突 | 中 | 低 | 提供確認提示，允許使用者覆寫 |
| 任務鎖死鎖 | 中 | 低 | TTL 機制 + force-release |

---

## Testing Plan

### Unit Tests
- 所有 Python 腳本的基本功能測試

### Integration Tests
- 完整工作流程測試（啟動任務 → 實作 → QA → 完成）

### Manual Tests
- Pre-commit hooks 觸發測試
- State Gate 阻擋測試
- 分支管理流程測試

---

## Rollback Plan

若發現嚴重問題：

1. 停用 pre-commit hooks: `pre-commit uninstall`
2. 切回 main 分支: `git checkout main`
3. 回退變更: `git reset --hard <commit-hash>`
4. 記錄問題於 Log 並標記為 ABORTED

---

## Success Criteria

- [ ] 所有 P0 項目完成（6 項）
- [ ] 所有 P1 項目完成（6 項）
- [ ] 所有 P2 項目完成（4 項，排除可選項目）
- [ ] Pre-commit hooks 可正常運作
- [ ] 至少執行一次完整工作流程驗證
- [ ] 文檔完整且易於理解
- [ ] GCP 私鑰已作廢並更新

---

## Timeline

- **Phase 1**: 4 小時
- **Phase 2**: 3 小時
- **Phase 3**: 2 小時
- **Phase 4**: 1 小時
- **Total**: ~10 小時

---

## Deliverables

### 新建檔案（21 個）
1. `scripts/check_active_task.py`
2. `scripts/validate_state_gate.py`
3. `scripts/task_branch.py`
4. `doc/logs/.gitkeep`
5. `doc/logs/Idx-000_log.template.md`
6. `doc/plans/.gitkeep`
7. `doc/plans/Idx-003_plan.md`
8. `.pre-commit-config.yaml`
9. `doc/tech_debt.md`
10. `schemas/log.schema.json`
11. `scripts/validate_log.py`
12. `scripts/check_verification_due.py`
13. `.agent/templates/handoff_template.md`
14. `doc/adr/README.md`
15. `doc/adr/0000-template.md`
16. `doc/adr/0001-use-streamlit-for-ui.md`
17. `doc/adr/0002-openrouter-unified-api.md`
18. `doc/adr/0003-multi-agent-workflow.md`
19. `scripts/backup_logs.py`
20. `doc/workflow_implementation_report.md`
21. `doc/gcp_key_revocation_guide.md`

### 修改檔案（6 個）
1. `.gitignore`
2. `.ruff.toml`
3. `.agent/roles/qa.md`
4. `scripts/debug_pipeline.py`
5. `.github/workflows/ci.yml`

---

## Next Steps (Post-Implementation)

1. 執行完整工作流程驗證
2. 作廢 GCP 私鑰並更新
3. 建立第一份備份
4. 安排技術債清償計畫

---

**Plan Created**: 2026-01-10
**Plan Owner**: @Antigravity
**Last Updated**: 2026-01-10
