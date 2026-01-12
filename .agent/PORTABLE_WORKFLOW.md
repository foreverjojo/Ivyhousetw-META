# 🚀 Portable Workflow Guide

> 本文件說明如何將此 Workflow 系統移植到其他專案。

---

## 📦 必須移植的檔案結構

```
new-project/
├── .agent/
│   ├── workflows/
│   │   ├── AGENT_ENTRY.md       ✅ 核心入口（通用）
│   │   └── dev-team.md          ✅ 團隊流程（通用）
│   ├── roles/
│   │   ├── planner.md           ✅ 規劃師（通用）
│   │   ├── engineer.md          ✅ 工程師（通用）
│   │   ├── qa.md                ✅ 品管員（通用）
│   │   └── domain_expert.md     ⚙️ 領域專家（需客製）
│   ├── skills/
│   │   ├── SKILL.md             ✅ 技能說明（通用）
│   │   ├── code_reviewer.py     ✅ 代碼審查（通用）
│   │   ├── doc_generator.py     ✅ 文件生成（通用）
│   │   ├── test_runner.py       ✅ 測試執行（通用）
│   │   ├── explore_cli_tool.md  ✅ CLI 探索（通用）
│   │   └── skill_whitelist.json ⚙️ 白名單（需客製）
│   ├── templates/
│   │   └── handoff_template.md  ✅ 交接模板（通用）
│   └── active_sessions.json     🔄 執行時生成
├── doc/
│   ├── plans/
│   │   └── Idx-000_plan.template.md  ✅ Plan 模板
│   └── implementation_plan_index.md  🆕 需新建
└── project_rules.md             ⚙️ 專案規則（取代 ivy_house_rules.md）
```

---

## 🔧 移植步驟

### Step 1: 複製核心檔案

```bash
# 設定來源與目標
SOURCE="/workspaces/ivyhousetw ad analyzer/Ivyhousetw-META"
TARGET="/path/to/new-project"

# 複製 .agent 目錄
cp -r "$SOURCE/.agent" "$TARGET/"

# 複製 doc 模板
mkdir -p "$TARGET/doc/plans"
cp "$SOURCE/doc/plans/Idx-000_plan.template.md" "$TARGET/doc/plans/" 2>/dev/null || echo "模板不存在，稍後建立"
```

### Step 2: 建立專案規則檔

建立 `project_rules.md`（取代 `ivy_house_rules.md`），包含：

```markdown
# [專案名稱] - 系統開發核心守則

## 1. 核心溝通規範
- 語言：繁體中文 / English
- 確認機制：執行前必須複述需求

## 2. 架構策略
- [依專案調整]

## 3. 開發流程
- Git Flow: [依專案調整]

## 4. 技術規範
- 檔案長度：主程式 ≤ 600 行
- [其他規範]

## 5. 資安紅線
- 絕對禁止 Hard-code API Key
```

### Step 3: 更新 AGENT_ENTRY.md 必讀清單

編輯 `.agent/workflows/AGENT_ENTRY.md`，更新必讀檔案路徑：

```markdown
## 1) 必讀檔案
1. `./.agent/workflows/dev-team.md`
2. `./project_rules.md`              ← 改為專案規則檔
3. `./doc/implementation_plan_index.md`
```

### Step 4: 客製化領域專家角色

將 `meta_expert.md` 改為專案適用的領域專家：

| 專案類型 | 領域專家角色 |
|---------|-------------|
| Meta 廣告分析 | Meta Expert (數據計算) |
| 電商系統 | E-commerce Expert (訂單/庫存) |
| 金融系統 | Finance Expert (合規/計算) |
| API 開發 | API Expert (設計/安全) |

### Step 5: 初始化 Index

建立空的 `doc/implementation_plan_index.md`：

```markdown
# Implementation Plan Index

| Task ID | 名稱 | 狀態 | 建立日期 | 完成日期 |
|---------|------|------|---------|---------|
| Idx-001 | [首個任務] | Planning | YYYY-MM-DD | - |
```

---

## 🔄 快速移植腳本

```bash
#!/bin/bash
# setup_workflow.sh - 快速初始化 Agent Workflow

set -e

# 檢查參數
if [ -z "$1" ]; then
    echo "用法: ./setup_workflow.sh /path/to/new-project"
    exit 1
fi

TARGET="$1"
SOURCE="$(dirname "$0")/.."

echo "🚀 初始化 Agent Workflow..."

# 建立目錄結構
mkdir -p "$TARGET/.agent/workflows"
mkdir -p "$TARGET/.agent/roles"
mkdir -p "$TARGET/.agent/skills"
mkdir -p "$TARGET/.agent/templates"
mkdir -p "$TARGET/doc/plans"

# 複製通用檔案
cp "$SOURCE/.agent/workflows/AGENT_ENTRY.md" "$TARGET/.agent/workflows/"
cp "$SOURCE/.agent/workflows/dev-team.md" "$TARGET/.agent/workflows/"
cp "$SOURCE/.agent/roles/planner.md" "$TARGET/.agent/roles/"
cp "$SOURCE/.agent/roles/engineer.md" "$TARGET/.agent/roles/"
cp "$SOURCE/.agent/roles/qa.md" "$TARGET/.agent/roles/"
cp "$SOURCE/.agent/skills/code_reviewer.py" "$TARGET/.agent/skills/"
cp "$SOURCE/.agent/skills/doc_generator.py" "$TARGET/.agent/skills/"
cp "$SOURCE/.agent/skills/test_runner.py" "$TARGET/.agent/skills/"
cp "$SOURCE/.agent/skills/SKILL.md" "$TARGET/.agent/skills/"
cp "$SOURCE/.agent/templates/handoff_template.md" "$TARGET/.agent/templates/"

# 建立空的 active_sessions.json
echo '{"sessions": []}' > "$TARGET/.agent/active_sessions.json"

# 建立空的 Index
cat > "$TARGET/doc/implementation_plan_index.md" << 'EOF'
# Implementation Plan Index

| Task ID | 名稱 | 狀態 | 建立日期 | 完成日期 |
|---------|------|------|---------|---------|
| - | - | - | - | - |
EOF

echo "✅ Workflow 初始化完成！"
echo "📝 請記得："
echo "   1. 建立 project_rules.md"
echo "   2. 更新 AGENT_ENTRY.md 必讀清單"
echo "   3. 客製化領域專家角色"
```

---

## 📋 移植 Checklist

- [ ] 複製 `.agent/` 目錄
- [ ] 建立 `project_rules.md`（專案規則）
- [ ] 更新 `AGENT_ENTRY.md` 必讀清單
- [ ] 客製化領域專家角色
- [ ] 建立 `doc/implementation_plan_index.md`
- [ ] 建立 `doc/plans/` 目錄
- [ ] 測試：執行 `/dev-team` 確認流程正常

---

## 🎯 GitHub Template 方案（進階）

1. 建立新 Repo：`agent-workflow-template`
2. 只放 workflow 相關檔案
3. 設定為 GitHub Template Repository
4. 未來用 "Use this template" 建立新專案

---

## ⚠️ 注意事項

1. **路徑調整**：`ivy_house_rules.md` → `project_rules.md`
2. **領域專家**：`meta_expert.md` 需依專案客製
3. **技能擴充**：新專案可能需要新增專用技能
4. **Index 獨立**：每個專案有自己的 `implementation_plan_index.md`
