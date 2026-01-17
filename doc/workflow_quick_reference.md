# Workflow 治理框架 - 快速參考

**版本**: 1.0
**日期**: 2026-01-10

---

## 🚀 完整工作流程（一頁速查）

### 1️⃣ 啟動新任務

```powershell
# 確認 Index 存在於 doc/Implementation_Plan_index.md
# 建立 Plan
# 範本：doc/plans/Idx-003_plan.md

# 建立分支
python scripts/task_branch.py create Idx-NNN

# 取得鎖
python scripts/check_active_task.py acquire Idx-NNN
```

---

### 2️⃣ 實作與提交

```powershell
# 在 task/Idx-NNN 分支上工作

# Commit 格式（重要！）
git commit -m "feat(Idx-NNN): 描述"

# 豁免格式：chore:, docs:, style:, ci:, build:, revert:

# Pre-commit 會自動檢查：
# - State Gate（Index 存在性）
# - 任務鎖一致性
# - Code quality (Ruff)
# - 私鑰洩漏
```

---

### 3️⃣ QA 審查

```powershell
# QA 執行驗證

# 若 PASS
python scripts/task_branch.py merge Idx-NNN
# → 更新 Index 狀態為 "COMPLETED"

# 若 FAIL
# → 記錄問題於 Log
# → 或中止：python scripts/task_branch.py abort Idx-NNN
```

---

### 4️⃣ 完成任務

```powershell
# 釋放鎖
python scripts/check_active_task.py release Idx-NNN

# 完成 Log（使用範本）
# 檔案：doc/logs/Idx-NNN_log.md
# 範本：doc/logs/Idx-000_log.template.md

# 驗證 Log
python scripts/validate_log.py doc/logs/Idx-NNN_log.md

# 更新 Index
# - Log Path: doc/logs/Idx-NNN_log.md
# - Commit Hash: <完成時的 commit hash>
# - Status: COMPLETED
```

---

## 🛠️ 常用指令速查

### 任務鎖管理

```powershell
# 查看當前鎖狀態
python scripts/check_active_task.py status

# 取得鎖（預設 TTL 24h）
python scripts/check_active_task.py acquire Idx-001

# 釋放鎖
python scripts/check_active_task.py release Idx-001

# 強制釋放（過期或緊急）
python scripts/check_active_task.py force-release
```

---

### 分支管理

```powershell
# 建立任務分支
python scripts/task_branch.py create Idx-001

# 合併到 main（QA PASS 後）
python scripts/task_branch.py merge Idx-001

# 中止任務並刪除分支（QA FAIL 後）
python scripts/task_branch.py abort Idx-001
```

---

### 驗證與檢查

```powershell
# 驗證 Commit Message
python scripts/validate_state_gate.py "feat(Idx-002): 描述"

# 驗證單一 Log
python scripts/validate_log.py doc/logs/Idx-001_log.md

# 驗證所有 Logs
python scripts/validate_log.py --all

# 檢查驗證計畫到期（提前 3 天提醒）
python scripts/check_verification_due.py
```

---

### 備份與恢復

```powershell
# 建立備份
python scripts/backup_logs.py

# 列出備份
python scripts/backup_logs.py --list

# 還原備份
python scripts/backup_logs.py --restore 20260110_120000
```

---

### Pre-commit Hooks

```powershell
# 安裝（首次）
pre-commit install

# 手動執行所有 hooks
pre-commit run --all-files

# 更新 hooks
pre-commit autoupdate

# 跳過 hooks（不推薦！）
git commit --no-verify -m "..."
```

---

## 📋 檔案範本位置

| 用途 | 範本位置 |
|------|----------|
| **Plan** | `doc/plans/Idx-003_plan.md` |
| **Log** | `doc/logs/Idx-000_log.template.md` |
| **Handoff** | `.agent/templates/handoff_template.md` |
| **ADR** | `doc/adr/0000-template.md` |

---

## 🔒 State Gate 規則

### Commit Message 格式

**標準格式**:
```
<type>(<index>): <description>

feat(Idx-001): 實作新功能
fix(Idx-002): 修復 bug
```

**豁免格式**（不需 Index）:
```
chore: 更新依賴
docs: 修正文檔
style: 程式碼格式化
ci: CI/CD 設定調整
build: 建置設定更新
revert: 回退某 commit
```

### 驗證規則

1. ✅ Commit Message 包含 `(Idx-NNN)` 或豁免關鍵字
2. ✅ Index 存在於 `Implementation_Plan_index.md`
3. ✅ 任務鎖一致性（若有鎖）

---

## 🚨 緊急處理

### 鎖住無法提交？

```powershell
# 檢查鎖狀態
python scripts/check_active_task.py status

# 若鎖過期，強制釋放
python scripts/check_active_task.py force-release

# 重新取得鎖
python scripts/check_active_task.py acquire Idx-NNN
```

---

### Pre-commit 阻擋提交？

```powershell
# 查看具體錯誤
git commit -m "..."

# 修正後重試
# 或臨時跳過（謹慎使用）
git commit --no-verify -m "..."
```

---

### 誤合併到 main？

```powershell
# 回退最後一次 commit（保留變更）
git reset --soft HEAD~1

# 或強制回退（丟棄變更）
git reset --hard HEAD~1

# 強制推送（謹慎！）
git push --force
```

---

### Log 驗證失敗？

```powershell
# 查看錯誤詳情
python scripts/validate_log.py doc/logs/Idx-NNN_log.md

# 對照 Schema
cat schemas/log.schema.json

# 對照範本
cat doc/logs/Idx-000_log.template.md
```

---

## 📅 定期維護

### 每週

- [ ] 執行：`python scripts/check_verification_due.py`
- [ ] 檢視技術債務：`doc/tech_debt.md`
- [ ] 檢查是否有過期鎖：`python scripts/check_active_task.py status`

### 每月

- [ ] 建立備份：`python scripts/backup_logs.py`
- [ ] 清理舊分支：`git branch --merged | grep -v main | xargs git branch -d`
- [ ] 更新 pre-commit hooks：`pre-commit autoupdate`

### 每季

- [ ] 技術債務清償規劃（從 `tech_debt.md`）
- [ ] ADR 檢視與補充
- [ ] GCP 金鑰輪換（90 天週期）

---

## 🔗 重要文件

| 文件 | 位置 |
|------|------|
| **工作流程分析** | `doc/workflow_process_analysis.md` |
| **實施報告** | `doc/workflow_implementation_report.md` |
| **技術債務** | `doc/tech_debt.md` |
| **ADR 索引** | `doc/adr/README.md` |
| **QA 角色說明** | `.agent/roles/qa.md` |
| **Planner 角色** | `.agent/roles/planner.md` |
| **Engineer 角色** | `.agent/roles/engineer.md` |

---

## 📞 故障排除

| 問題 | 解決方案 |
|------|----------|
| 鎖過期 | `python scripts/check_active_task.py force-release` |
| 分支衝突 | `git merge main` 然後解決衝突 |
| Pre-commit 錯誤 | 查看 `.pre-commit-config.yaml` 排除規則 |
| Log 驗證失敗 | 對照 `schemas/log.schema.json` |
| 私鑰洩漏警告 | 檢查 `doc/gcp_key_revocation_guide.md` |

---

## 💡 最佳實踐

1. **小步快跑**: 每個 Index 聚焦單一功能
2. **頻繁提交**: 每完成一個邏輯單元就 commit
3. **詳實記錄**: Log 中記錄決策理由和替代方案
4. **技術債登記**: 遇到 workaround 立即記錄到 `tech_debt.md`
5. **ADR 決策**: 重大技術選型寫成 ADR
6. **定期備份**: 每月至少一次完整備份
7. **安全優先**: 絕不提交金鑰、密碼、敏感資料

---

## 🎯 五條鐵律速記

1. **State Gate** → 每次 Commit 必須關聯 Index（或豁免）
2. **Execution Mode Recording** → 所有工作在專屬分支 + 任務鎖
3. **QA Grading** → 每個任務都有明確的 QA 結果
4. **Parallel Isolation** → 任務鎖防止衝突，TTL 防止死鎖
5. **Log Binding** → 每個 Index 都有對應的 Log 記錄

---

**工件為真值 (Artifacts as Source of Truth)**:
- **Index** → `Implementation_Plan_index.md`
- **Plan** → `doc/plans/Idx-NNN_plan.md`
- **Log** → `doc/logs/Idx-NNN_log.md`
- **Commit** → Git 歷史

---

**快速參考版本**: 1.0
**最後更新**: 2026-01-10
**維護者**: @Antigravity
