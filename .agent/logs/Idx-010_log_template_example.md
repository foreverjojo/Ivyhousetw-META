# Execution Log: Idx-XXX

**Plan**: `doc/plans/Idx-XXX_plan.md`
**Created**: YYYY-MM-DD HH:mm:ss
**Status**: IN_PROGRESS | COMPLETED | FAILED

---

## EXECUTION TIMELINE

| Round | Stage | Tool | User | Start | End | Result |
|-------|-------|------|------|-------|-----|--------|
| 1 | Engineer | [codex-cli\|opencode] | @user | ... | ... | DONE |
| 1 | QA | [codex-cli\|opencode] | @user | ... | ... | PASS |

---

## SCOPE GATE

### Files changed
```bash
# Project terminal / VS Code SCM only
git status --porcelain
```

### Whitelist compliance
- Result: PASS | FAIL
- Out-of-scope files: [None | file list]

### UI/UX triggered
- UI/UX triggered: YES | NO
- Triggered files (if YES): [file list]
- Reason (if YES): [path pattern matched]

---

## QA REPORT

### Test results
- Commands run: [list]
- Result summary: [pass/fail + key output]

### Cross-QA compliance
- qa_tool: [codex-cli | opencode]
- last_change_tool: [codex-cli | opencode]
- qa_compliance: [✅ 符合 | ⚠️ 例外：原因]

### Conclusion
- qa_result: PASS | PASS_WITH_RISK | FAIL
- Summary: [1–3 lines]

---

## UI/UX CHECK *(triggered)*

> ⚠️ 本段落僅在 `UI/UX triggered: YES` 時出現；未觸發則不出現（不寫 N/A）。

**觸發原因**: [變更文件包含 ...]

### 檢核範圍（code review 為主）

#### UX（流程/文案）
- 空狀態：✅/⚠️/❌ - [說明]
- 錯誤提示：✅/⚠️/❌ - [說明]
- Loading/長操作回饋：✅/⚠️/❌ - [說明]
- 主要操作可達與文案：✅/⚠️/❌ - [說明]

#### UI（基本一致性）
- 元件狀態一致（disabled/help text）：✅/⚠️/❌ - [說明]
- 表單基本驗證回饋：✅/⚠️/❌ - [說明]

### Result
- Conclusion: PASS | PASS_WITH_RISK | FAIL
- Route on FAIL: Engineer | SPEC_MODE | Planner | N/A
- Must fix: [list | N/A]
- Should fix: [list | N/A]
- Manual spot-check needed: [list | N/A]

---

## MAINTAINABILITY REVIEW *(triggered)*

> ⚠️ 本段落僅在 Maintainability Gate 觸發時出現；未觸發則不出現（不寫 N/A）。
> Reviewer 永不改 code（只輸出 Must/Should/Nice）。

### Result
- Must fix: [list | N/A]
- Should: [list | N/A]
- Nice: [list | N/A]

---

## IF FAIL *(only when qa_result=FAIL)*

**Reason**: [QA FAIL | UI/UX FAIL | Scope violation | Maintainability Must-fix]
**Route back to**: Engineer | SPEC_MODE | Planner
**Next action**: [具體下一步]

---

## EVIDENCE *(optional)*

> ⚠️ 只有在 Evidence Gate 閾值命中時才允許新增 `doc/logs/Idx-XXX_evidence.md`。
> 未命中：本段落可保留一句「未產生 Evidence」或直接省略。

- Evidence file: `doc/logs/Idx-XXX_evidence.md`
- Summary: [為何需要 Evidence 的一句話]

---

## FINAL STATUS

- Conclusion: PASS | PASS_WITH_RISK | FAIL
- Commit hash: [pending|hash]
- Risks: [list | None]
