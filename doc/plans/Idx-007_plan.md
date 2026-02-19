# Plan: Idx-007

**Index**: Idx-007
**Created**: 2026-01-10
**Planner**: @Antigravity

---

## 🎯 目標

更新 `dev-team.md` 和 `planner.md`，明確規定每個任務必須產出獨立的 `Idx-NNN_plan.md` 文件，並建立對應的目錄結構與模板。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `doc/plans/.gitkeep` | 新增 | 建立 plans 目錄（已存在則跳過） |
| `doc/plans/Idx-000_plan.template.md` | 新增 | Plan 文件模板 |
| `.agent/workflows/dev-team.md` | 修改 | Step 1 增加「產出 plan.md」規範與必要停頓點 |
| `.agent/roles/planner.md` | 修改 | 增加「產出物保存規範」區段 |

---

## 📝 邏輯細節

### 1. `doc/plans/Idx-000_plan.template.md`
標準模板，包含：
- 目標區段
- 檔案變更表格
- 邏輯細節
- 注意事項
- 用戶確認 checkbox

### 2. `dev-team.md` Step 1 修改
- 新增第 4 點任務：「保存 Spec 為獨立文件」
- 新增模板引用說明
- 新增必要停頓點提示

### 3. `planner.md` 修改
- 新增「產出物保存規範」區段
- 明確指定保存位置 `doc/plans/`
- 明確指定命名規則 `Idx-NNN_plan.md`
- 說明保存流程（4 步驟）

---

## ⚠️ 注意事項

- **向後相容**：不影響既有 log 文件結構
- **模板欄位設計**：與 log template 互補（plan 記錄規劃，log 記錄執行）

---

## 🔗 相關資源

- Log Template: `doc/logs/Idx-000_log.template.md`
- Dev-Team Workflow: `.agent/workflows/dev-team.md`

---

## ✅ 用戶確認

- [x] Spec 已確認，可進入 Step 2 (Meta Expert)

---

**Template Version**: 1.0.0
**Last Updated**: 2026-01-10
