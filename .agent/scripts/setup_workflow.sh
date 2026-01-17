#!/bin/bash
# setup_workflow.sh - 快速初始化 Agent Workflow 到新專案
# 用法: ./setup_workflow.sh /path/to/new-project [project-name]

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 取得腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$(dirname "$SCRIPT_DIR")"  # .agent 目錄

# 檢查參數
if [ -z "$1" ]; then
    echo -e "${RED}❌ 錯誤：請提供目標專案路徑${NC}"
    echo ""
    echo "用法: ./setup_workflow.sh /path/to/new-project [project-name]"
    echo ""
    echo "範例:"
    echo "  ./setup_workflow.sh /workspaces/my-new-project"
    echo "  ./setup_workflow.sh /workspaces/my-new-project \"我的新專案\""
    exit 1
fi

TARGET="$1"
PROJECT_NAME="${2:-New Project}"

echo -e "${BLUE}🚀 Agent Workflow 初始化工具${NC}"
echo "=================================="
echo -e "來源: ${YELLOW}$SOURCE${NC}"
echo -e "目標: ${YELLOW}$TARGET${NC}"
echo -e "專案: ${YELLOW}$PROJECT_NAME${NC}"
echo ""

# 確認目標目錄
if [ ! -d "$TARGET" ]; then
    echo -e "${YELLOW}📁 目標目錄不存在，正在建立...${NC}"
    mkdir -p "$TARGET"
fi

# Step 1: 建立目錄結構
echo -e "${BLUE}[1/6] 建立目錄結構...${NC}"
mkdir -p "$TARGET/.agent/workflows"
mkdir -p "$TARGET/.agent/roles"
mkdir -p "$TARGET/.agent/skills"
mkdir -p "$TARGET/.agent/scripts"
mkdir -p "$TARGET/.agent/state"
mkdir -p "$TARGET/.agent/templates"
mkdir -p "$TARGET/.agent/backup"
mkdir -p "$TARGET/.agent/mcp"
mkdir -p "$TARGET/doc/plans"
mkdir -p "$TARGET/doc/logs"
mkdir -p "$TARGET/tools"
echo -e "${GREEN}  ✅ 目錄結構建立完成${NC}"

# Step 2: 複製 Workflow 檔案
echo -e "${BLUE}[2/6] 複製 Workflow 檔案...${NC}"
cp "$SOURCE/workflows/AGENT_ENTRY.md" "$TARGET/.agent/workflows/"
cp "$SOURCE/workflows/dev-team.md" "$TARGET/.agent/workflows/"
echo -e "${GREEN}  ✅ Workflow 檔案複製完成${NC}"

# Step 3: 複製 Roles 檔案
echo -e "${BLUE}[3/6] 複製 Roles 檔案...${NC}"
cp "$SOURCE/roles/planner.md" "$TARGET/.agent/roles/"
cp "$SOURCE/roles/engineer.md" "$TARGET/.agent/roles/"
cp "$SOURCE/roles/qa.md" "$TARGET/.agent/roles/"
# 建立通用的 domain_expert.md 模板
cat > "$TARGET/.agent/roles/domain_expert.md" << 'EOF'
```markdown
---
description: 領域專家 (Domain Expert) - 負責專業領域審核
---
# Role: 領域專家 (Domain Expert)

## 核心職責
你是本專案的領域專家。你的工作是檢視 Planner 的 Spec，確認專業邏輯是否正確。

## 專案背景
- [請依專案調整此段描述]

## 任務流程
1. 檢視 Planner 的 Spec
2. 確認專業邏輯是否正確
3. 提供專業建議
4. 產出審核報告

## 產出格式
```markdown
## 📊 領域專家審核

### 涉及的專業邏輯
- [列出相關邏輯]

### 建議
- [任何改進或注意事項]

### 結論
✅ 通過 / ⚠️ 需要修正
```

## 必須遵守的規則檔案
> - 📜 `project_rules.md` - 專案開發核心守則
```
EOF
echo -e "${GREEN}  ✅ Roles 檔案複製完成${NC}"

# Step 4: 複製 Skills 檔案
echo -e "${BLUE}[4/6] 複製 Skills 檔案...${NC}"
if [ -f "$SOURCE/skills/code_reviewer.py" ]; then
    cp "$SOURCE/skills/code_reviewer.py" "$TARGET/.agent/skills/"
fi
if [ -f "$SOURCE/skills/doc_generator.py" ]; then
    cp "$SOURCE/skills/doc_generator.py" "$TARGET/.agent/skills/"
fi
if [ -f "$SOURCE/skills/test_runner.py" ]; then
    cp "$SOURCE/skills/test_runner.py" "$TARGET/.agent/skills/"
fi
if [ -f "$SOURCE/skills/SKILL.md" ]; then
    cp "$SOURCE/skills/SKILL.md" "$TARGET/.agent/skills/"
fi
if [ -f "$SOURCE/skills/explore_cli_tool.md" ]; then
    cp "$SOURCE/skills/explore_cli_tool.md" "$TARGET/.agent/skills/"
fi

# 建立空的 skill_whitelist.json
echo '{"whitelist": [], "last_updated": "'$(date -Iseconds)'"}' > "$TARGET/.agent/skills/skill_whitelist.json"
echo -e "${GREEN}  ✅ Skills 檔案複製完成${NC}"

# Step 5: 複製 Templates 並建立初始檔案
echo -e "${BLUE}[5/6] 建立模板與初始檔案...${NC}"
if [ -f "$SOURCE/templates/handoff_template.md" ]; then
    cp "$SOURCE/templates/handoff_template.md" "$TARGET/.agent/templates/"
fi

# 建立 active_sessions.json
echo '{"sessions": [], "created": "'$(date -Iseconds)'"}' > "$TARGET/.agent/active_sessions.json"

# 建立 Implementation Plan Index
cat > "$TARGET/doc/implementation_plan_index.md" << EOF
# Implementation Plan Index

> 此文件追蹤所有開發任務的規劃與執行狀態。

## 任務索引

| Task ID | 名稱 | 狀態 | 建立日期 | 完成日期 | 負責人 |
|---------|------|------|---------|---------|--------|
| Idx-001 | [首個任務] | Planning | $(date +%Y-%m-%d) | - | - |

## 狀態說明

- **Planning**: 規劃中
- **Approved**: 已核准，待執行
- **In Progress**: 執行中
- **QA**: 品管審查中
- **Completed**: 已完成
- **On Hold**: 暫停
- **Cancelled**: 已取消
EOF

# 建立 Plan 模板
cat > "$TARGET/doc/plans/Idx-000_plan.template.md" << 'EOF'
# Idx-NNN: [任務名稱]

> 建立日期: YYYY-MM-DD
> 狀態: Planning

---

## 📄 開發規格書

### 目標
[描述這次修改要達成什麼]

### 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| xxx.py | 修改 | ... |
| yyy.py | 新增 | ... |

### 邏輯細節
[具體說明每個檔案要改什麼]

### 驗收條件
- [ ] 條件 1
- [ ] 條件 2
- [ ] 條件 3

### 注意事項
- [資安注意事項]
- [效能注意事項]
- [相容性注意事項]

### 風險評估
| 風險 | 機率 | 影響 | 緩解措施 |
|------|------|------|---------|
| ... | 低/中/高 | 低/中/高 | ... |

---

## 審核紀錄

| 日期 | 審核者 | 結果 | 備註 |
|------|--------|------|------|
| - | - | - | - |
EOF
echo -e "${GREEN}  ✅ 模板與初始檔案建立完成${NC}"

# Step 6: 複製執行腳本（不含 VS Code 擴充）
echo -e "${BLUE}[6/6] 複製執行腳本...${NC}"

copy_script() {
    local src="$1"
    local dst="$2"
    if [ -f "$src" ]; then
        cp "$src" "$dst"
        chmod +x "$dst/$(basename "$src")" 2>/dev/null || true
    fi
}

	copy_script "$SOURCE/scripts/run_codex_template.sh" "$TARGET/.agent/scripts/"
	# Note: Terminal Bridge Server 已移除；終端注入與監控改由 VS Code 內建 terminal.sendText + Proposed API 處理。

echo -e "${GREEN}  ✅ 執行腳本複製完成${NC}"

# Step 7: 建立專案規則檔模板
echo -e "${BLUE}[7/7] 建立專案規則檔...${NC}"
cat > "$TARGET/project_rules.md" << EOF
# $PROJECT_NAME - 系統開發核心守則

## 1. 核心溝通與行為規範

- **語言規範：** 所有對話、程式碼註解、文檔說明，使用 **繁體中文 (Traditional Chinese)**。
- **確認機制：** 在執行任何程式碼撰寫或架構變更前，**必須先複述一次需求**，並詢問使用者確認。
- **遇到困難時的應對：**
  - 若連續 2 次修正錯誤失敗，**禁止**盲目嘗試。
  - **必須**使用搜尋工具，搜尋最新的解決方案。

## 2. 系統架構策略

- **架構模式：** [請填入：Monorepo / Multi-repo / Monolith / Microservices]
- **技術棧：** [請填入主要技術]

## 3. 開發流程

- **Git Flow：**
  1. Local Dev → Local Test → Confirmation → Push
  2. Commit 訊息遵循 Conventional Commits
- **分支策略：** [請填入：main / develop / feature branches]

## 4. 開發技術規範

- **檔案長度規範（分級制）**：
  - 主程式: 建議 ≤ 600 行，嚴禁超過 800 行
  - UI 模組: 建議 ≤ 500 行，嚴禁超過 600 行
  - 業務邏輯: 建議 ≤ 400 行，嚴禁超過 500 行
  - 工具模組: 建議 ≤ 300 行，嚴禁超過 400 行
- **檔案註釋**：每個檔案第一行必須說明該檔案用途。

## 5. 資安與敏感資料

- **絕對禁止：** 嚴禁將 API Key、密碼、Token 直接寫入源碼。
- **強制規範：** 所有敏感資料必須透過 \`.env\` 環境變數讀取。

## 6. Agent 自動化規範

- **連線持久化**：啟動長效型程序時，必須將其記錄至 \`.agent/active_sessions.json\`。
- **QA 自動化**：驗證邏輯須封裝為獨立腳本。

EOF
echo -e "${GREEN}  ✅ 專案規則檔建立完成${NC}"

# 更新 AGENT_ENTRY.md 中的必讀清單路徑
echo -e "${BLUE}[額外] 更新 AGENT_ENTRY.md 必讀清單...${NC}"
sed -i 's|./ivy_house_rules.md|./project_rules.md|g' "$TARGET/.agent/workflows/AGENT_ENTRY.md"
sed -i 's|./docs/implementation_plan_index.md|./doc/implementation_plan_index.md|g' "$TARGET/.agent/workflows/AGENT_ENTRY.md"
echo -e "${GREEN}  ✅ AGENT_ENTRY.md 更新完成${NC}"

# 完成訊息
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Agent Workflow 初始化完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}📝 後續步驟：${NC}"
	echo "  1. 編輯 $TARGET/project_rules.md 填入專案資訊"
	echo "  2. 編輯 $TARGET/.agent/roles/domain_expert.md 客製化領域專家"
	echo "  3. 在 VS Code 開啟專案，測試輸入 /dev-team"
	echo ""
echo -e "${BLUE}📁 已建立的結構：${NC}"
echo "  $TARGET/"
echo "  ├── .agent/"
	echo "  │   ├── workflows/ (AGENT_ENTRY.md, dev-team.md)"
	echo "  │   ├── roles/ (planner, engineer, qa, domain_expert)"
	echo "  │   ├── scripts/ (run_codex_template.sh)"
	echo "  │   ├── state/ (runtime state; tokens/log)"
	echo "  │   └── templates/"
echo "  ├── tools/"
echo "  │   └── (reserved)"
echo "  │   └── templates/"
echo "  ├── doc/"
echo "  │   ├── plans/ (Idx-000_plan.template.md)"
echo "  │   └── implementation_plan_index.md"
echo "  └── project_rules.md"
echo ""
