# Task Execution Log Template

**Index**: Idx-000
**Plan Version**: YYYY-MM-DD-v1
**Task Description**: [簡短描述]

---

## Metadata

- **Start Time**: YYYY-MM-DD HH:MM:SS
- **End Time**: YYYY-MM-DD HH:MM:SS
- **Engineer**: @AgentName
- **QA**: @QAAgent
- **Duration**: X hours

---

## 🔧 Execution Information

**Execution Tool**: [codex-cli | opencode]
**Execution Start**: YYYY-MM-DD HH:MM
**Execution End**: YYYY-MM-DD HH:MM
**Exit Code**: 0

---

## Objective

[任務目標]

---

## Key Changes

### Files Created
- `path/to/file1.py` - 用途說明
- `path/to/file2.md` - 用途說明

### Files Modified
- `path/to/file3.py` - 變更說明
- `path/to/file4.json` - 變更說明

### Files Deleted
- `path/to/old_file.py` - 刪除原因

---

## Implementation Details

### 1. 步驟一
[具體執行內容]

### 2. 步驟二
[具體執行內容]

### 3. 步驟三
[具體執行內容]

---

## Decisions Made

| 決策點 | 選擇方案 | 理由 | 替代方案 |
|--------|---------|------|---------|
| 架構選型 | 方案A | 理由 | 方案B（未選） |
| 技術棧 | 工具X | 理由 | 工具Y（未選） |

---

## Challenges & Solutions

### Challenge 1: [問題描述]
**Solution**: [解決方案]

### Challenge 2: [問題描述]
**Solution**: [解決方案]

---

## 🔄 Rollback Records

| Level | Timestamp | Reason | Action | Result |
|-------|-----------|--------|--------|--------|
| - | - | - | - | - |

**Rollback Summary**: [若無 Rollback，填寫「無」]

---

## 🛠️ SKILLS_EXECUTION_REPORT

> 記錄本次任務執行的所有 skills（自動化工具）及其結果（status 小寫：pass|warning|fail|error|no_tests）

| Skill | Target | Status | Summary | Timestamp |
|-------|--------|--------|---------|-----------|
| `code_reviewer.py` | `path/to/file.py` | `pass` | 未發現問題 | YYYY-MM-DD HH:MM:SS |
| `test_runner.py` | `tests/` | `no_tests` | 未收集到測試 | YYYY-MM-DD HH:MM:SS |

---

## 📈 SKILLS_EVALUATION

> 記錄本次任務的 skills 執行統計（由 `skills_evaluator.py` 解析 `SKILLS_EXECUTION_REPORT` 產生）

**Command**: `python .agent/skills/skills_evaluator.py doc/logs/Idx-XXX_log.md`

```json
{
  "status": "pass | warning | error",
  "summary": "..."
}
```

---

## QA Status

- **Status**: ✅ PASS / ⚠️ PASS WITH RISK / ❌ FAIL
- **QA Date**: YYYY-MM-DD
- **QA Notes**: [審查意見]

### ✅ Cross-QA Compliance

**Executor**: [codex-cli | opencode]
**QA Tool**: [codex-cli | opencode] *(必須與 last_change_tool 不同)*
**QA Compliance**: [✅ PASS | ⚠️ WAIVER: 說明 | ❌ FAIL]

### Test Results
- [ ] 單元測試通過
- [ ] 整合測試通過
- [ ] 手動測試通過
- [ ] 文檔已更新
- [ ] Cross-QA 規則已遵守

---

## Tech Debt

| ID | 描述 | 優先級 | 記錄於 |
|----|------|--------|--------|
| TD-001 | [技術債描述] | Medium | tech_debt.md#TD-001 |

---

## Outcome

[任務成果總結]

---

## Next Steps

1. [ ] 下一步行動項目 1
2. [ ] 下一步行動項目 2
3. [ ] 下一步行動項目 3

---

## References

- [相關文檔或連結]
- [參考資料]

---

**Log Created**: YYYY-MM-DD
**Last Updated**: YYYY-MM-DD
