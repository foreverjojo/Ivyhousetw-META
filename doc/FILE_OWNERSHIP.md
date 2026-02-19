# 檔案所有權與領域劃分

> 本文件定義 Ivyhousetw-META 專案中各資料夾的**領域所有權**與**變更規範**。
> 目的：防止混淆、明確 Index 選擇、確保 State Gate 正確路由。

---

## 📂 領域劃分

### `.agent/**` - Workflow / 治理 / 工具鏈領域

**所有權**: Dev-Team Workflow、CI/CD、工程治理改善

**包含內容**:
- `.agent/workflows/` - 開發團隊工作流程定義
- `.agent/roles/` - Agent 角色定義
- `.agent/skills/` - Agent 技能工具
- `.agent/scripts/` - Workflow 相關腳本（如 State Gate、Dev Team 腳本）
- `.agent/plans/` - Workflow 改善任務的 Plan 文件（Idx-009 起）
- `.agent/logs/` - Workflow 改善任務的 Log 文件（Idx-009 起）
- `.agent/Workflow_Plan_index.md` - Workflow 改善任務追蹤表

**變更規範**:
- 修改此領域的檔案時，commit message 中的 Idx 必須存在於 **`.agent/Workflow_Plan_index.md`**
- State Gate 會自動檢測變更路徑並驗證對應的 Index
- 任務範例：
  - ✅ 新增/修改 dev-team workflow 流程
  - ✅ 更新 State Gate 驗證邏輯
  - ✅ 改善 CI/CD pipeline
  - ✅ 新增 Agent 技能工具
  - ✅ 優化工程治理規範

---

### `doc/**`（不含 `.agent/`）- 專案功能開發領域

**所有權**: 產品功能、業務邏輯、交付物

**包含內容**:
- `doc/plans/` - 專案功能開發的 Plan 文件（Idx-001~008 等）
- `doc/logs/` - 專案功能開發的 Log 文件（Idx-001~008 等）
- `doc/Implementation_Plan_index.md` - 專案功能開發任務追蹤表
- `doc/ADR/` - 架構決策記錄
- `doc/runbooks/` - 運維手冊
- 其他產品/技術文件

**變更規範**:
- 修改此領域的檔案時，commit message 中的 Idx 必須存在於 **`doc/Implementation_Plan_index.md`**
- State Gate 會自動檢測變更路徑並驗證對應的 Index
- 任務範例：
  - ✅ 新增 Meta 廣告數據分析功能
  - ✅ 實作報表生成邏輯
  - ✅ 優化 UI/UX 體驗
  - ✅ 整合多通路數據（Shopee、Momo）
  - ✅ 修復業務邏輯 bug

---

### `core/**`, `utils/**`, `scripts/**`, `ui/**`, `pages/**` - 混合領域

**所有權**: 根據變更目的判斷

**判斷規則**:
1. **若變更目的是支援 workflow/治理改善** → 歸屬 `.agent/` 領域
   - 範例：新增腳本供 State Gate 使用、優化 CI 流程所需的工具函數
   - Index: `.agent/Workflow_Plan_index.md`

2. **若變更目的是支援專案功能開發** → 歸屬 `doc/` 領域
   - 範例：新增 KPI 計算邏輯、改善報表 UI、修復數據處理 bug
   - Index: `doc/Implementation_Plan_index.md`

**變更規範**:
- 混合變更（同時涉及兩個領域）應**分別提交**：
  - 先完成 workflow 改善部分（commit with Idx from Workflow Index）
  - 再完成功能開發部分（commit with Idx from Project Index）
- 若無法分離，需在 Plan 中明確說明並由 Coordinator 決策使用哪一份 Index

---

## 🚦 State Gate 自動路由規則

State Gate（`.agent/scripts/validate_state_gate.py`）會根據 **git staged 變更路徑** 自動選擇 Index：

```python
# 偽代碼
if any(file.startswith(".agent/") for file in changed_files):
    index_file = ".agent/Workflow_Plan_index.md"
else:
    index_file = "doc/Implementation_Plan_index.md"
```

**優先級**：
- 只要變更中**包含任一 `.agent/**` 路徑**，就會驗證 **Workflow Index**
- 否則驗證 **Project Index**

---

## 📋 Index 選擇快速參考表

| 變更內容範例 | 歸屬領域 | 使用 Index | Plan/Log 位置 |
|------------|---------|-----------|--------------|
| 修改 `.agent/workflows/dev-team.md` | Workflow | `.agent/Workflow_Plan_index.md` | `.agent/plans/`, `.agent/logs/` |
| 新增 `.agent/skills/new_skill.py` | Workflow | `.agent/Workflow_Plan_index.md` | `.agent/plans/`, `.agent/logs/` |
| 更新 State Gate 驗證邏輯 | Workflow | `.agent/Workflow_Plan_index.md` | `.agent/plans/`, `.agent/logs/` |
| 新增 Meta 數據分析功能 | Project | `doc/Implementation_Plan_index.md` | `doc/plans/`, `doc/logs/` |
| 修改 `core/kpi_calc.py` 計算邏輯 | Project | `doc/Implementation_Plan_index.md` | `doc/plans/`, `doc/logs/` |
| 優化 `ui/steps.py` UI 體驗 | Project | `doc/Implementation_Plan_index.md` | `doc/plans/`, `doc/logs/` |
| 修復 `scripts/meta_adapter.py` bug | Project | `doc/Implementation_Plan_index.md` | `doc/plans/`, `doc/logs/` |
| 改善 CI/CD workflow | Workflow | `.agent/Workflow_Plan_index.md` | `.agent/plans/`, `.agent/logs/` |

---

## ⚠️ 常見問題

### Q1: 如何判斷我的任務屬於哪個領域？

**A**: 問自己以下問題：
- 這次變更是為了**改善開發流程/工具鏈/治理**嗎？ → Workflow 領域
- 這次變更是為了**交付新功能/修復業務邏輯/改善用戶體驗**嗎？ → Project 領域

### Q2: 我同時修改了 `.agent/` 和 `core/` 的檔案，該怎麼辦？

**A**:
1. 評估變更是否可以分離為兩個獨立任務
2. 若可分離：分別建立兩個 Plan，使用各自的 Index，分別提交
3. 若不可分離：在 Plan 中說明原因，由 Coordinator 決策使用哪一份 Index（通常優先使用 Workflow Index）

### Q3: State Gate 選錯 Index 了怎麼辦？

**A**:
1. 檢查你的 git staged 檔案列表（`git status`）
2. 確認是否有 `.agent/**` 路徑在 staged 區
3. 若路由邏輯確實有誤，請在 `.agent/Workflow_Plan_index.md` 中登記新任務來修正 State Gate

### Q4: 舊的 `doc/plans/Idx-009~018_*.md` 去哪了？

**A**:
- 這些 workflow 改善任務的 Plan/Log 已遷移至 `.agent/plans/` 和 `.agent/logs/`
- 它們現在在 `.agent/Workflow_Plan_index.md` 中追蹤
- `doc/Implementation_Plan_index.md` 已移除這些項目，只保留專案功能開發任務

---

## 📚 相關文件

- `.agent/Workflow_Plan_index.md` - Workflow 改善任務追蹤表
- `doc/Implementation_Plan_index.md` - 專案功能開發任務追蹤表
- `.agent/workflows/dev-team.md` - Dev-Team 工作流程
- `.agent/workflows/AGENT_ENTRY.md` - Agent 入口規範
- `ivy_house_rules.md` - 艾薇手工坊系統開發核心守則

---

**最後更新**: 2026-01-19
**維護者**: Dev-Team Workflow
