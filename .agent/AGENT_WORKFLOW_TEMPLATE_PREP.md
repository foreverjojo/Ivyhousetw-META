# Agent Workflow Template - 準備發佈

## 📦 需要打包的內容

### 1. 核心檔案

```
agent-workflow-template/
├── .agent/
│   ├── workflows/
│   │   ├── AGENT_ENTRY.md
│   │   └── dev-team.md
│   ├── roles/
│   │   ├── planner.md
│   │   ├── engineer.md
│   │   ├── qa.md
│   │   └── domain_expert.md (template)
│   ├── skills/
│   │   ├── code_reviewer.py
│   │   ├── doc_generator.py
│   │   ├── test_runner.py
│   │   ├── explore_cli_tool.md
│   │   └── skill_whitelist.json (empty template)
│   ├── scripts/
│   │   ├── sendtext.sh ⭐
│   │   ├── run_codex_template.sh ⭐
│   │   ├── auto_execute_plan.sh ⭐
│   │   └── setup_workflow.sh
│   ├── state/ (empty, for sendtext bridge)
│   └── templates/
│       └── handoff_template.md
├── tools/
│   ├── sendtext-bridge/ ⭐
│   │   ├── extension.js
│   │   ├── package.json
│   │   ├── README.md
│   │   ├── LICENSE
│   │   └── sendtext-bridge-0.0.3.vsix
│   └── SENDTEXT_BRIDGE_SETUP.md
├── doc/
│   ├── plans/
│   │   └── Idx-000_plan.template.md
│   ├── logs/
│   │   └── Idx-000_log.template.md
│   └── implementation_plan_index.md (template)
├── .devcontainer/
│   └── devcontainer.json (optional, 範例)
├── project_rules.md (template)
├── README.md
└── LICENSE
```

### 2. 新增的核心功能 ⭐

#### SendText Bridge 擴充
- **目的**：在 Dev Container 環境下使用 `terminal.sendText` API
- **功能**：
  - 發送文字到終端（可控制是否執行）
  - 等待 Codex CLI 完成（自動監測）
  - 固定目標 terminal（避免被搶走）

#### 自動化執行腳本
- `sendtext.sh`：CLI wrapper 呼叫 SendText Bridge
- `run_codex_template.sh`：批次執行 Codex CLI（JSONL 審計）
- `auto_execute_plan.sh`：發送 Plan → 監測完成 → QA 提示

### 3. 文件需求

#### README.md（主文件）
```markdown
# Agent Workflow Template

多代理協作開發工作流程模板，整合 GitHub Copilot 與 Codex CLI。

## 特色

- ✅ 多代理角色定義（Planner / Engineer / QA / Expert）
- ✅ 自動化執行流程（Codex CLI 整合）
- ✅ Cross-QA 規則
- ✅ SendText Bridge（Dev Container 支援）
- ✅ JSONL 審計記錄
- ✅ L2 自動回滾

## 快速開始

### 方式 1：使用 GitHub Template（推薦）

1. 點擊 "Use this template"
2. Clone 新專案
3. 執行初始化：
   ```bash
   ./.agent/scripts/setup_workflow.sh .
   ```
4. 安裝 SendText Bridge（若使用 Dev Container）

### 方式 2：手動複製

```bash
git clone https://github.com/YOUR_ORG/agent-workflow-template.git
cd agent-workflow-template
./.agent/scripts/setup_workflow.sh /path/to/your-project
```

## 使用指南

### 1. 配置專案

編輯 `project_rules.md` 填入專案資訊。

### 2. 啟動 Dev Team

在 VS Code 中：

```
/dev-team
```

### 3. Codex CLI 自動化

```bash
# 自動化執行（監測完成 → QA 提示）
.agent/scripts/auto_execute_plan.sh doc/plans/Idx-XXX_plan.md
```

## 文件

- [Dev Team Workflow](.agent/workflows/dev-team.md)
- [Agent Entry](.agent/workflows/AGENT_ENTRY.md)
- [SendText Bridge Setup](tools/SENDTEXT_BRIDGE_SETUP.md)

## 需求

- VS Code 1.95+
- GitHub Copilot (建議)
- Codex CLI 0.80+ (選用)
- Dev Container (若使用 SendText Bridge)
```

#### CONTRIBUTING.md
```markdown
# Contributing

## 如何貢獻

1. Fork this repo
2. Create feature branch
3. 測試變更
4. Submit PR

## 測試

```bash
# 測試 setup script
./test_setup.sh

# 測試 SendText Bridge
./test_sendtext_bridge.sh
```

## 版本發佈

1. 更新 CHANGELOG.md
2. 更新版本號（若 SendText Bridge 有變）
3. 建立 Git tag
```

### 4. GitHub Template 設定

在 GitHub repo settings：

1. ✅ Template repository
2. 添加 Topics:
   - `agent-workflow`
   - `github-copilot`
   - `codex-cli`
   - `vscode-extension`
   - `dev-container`

### 5. 授權

- 建議使用 MIT License
- SendText Bridge 擴充需獨立 LICENSE

---

## 🚀 發佈步驟

### Phase 1：本地整理

1. [ ] 建立新 repo `agent-workflow-template`
2. [ ] 複製核心檔案（參考上方結構）
3. [ ] 測試 setup_workflow.sh
4. [ ] 撰寫 README.md
5. [ ] 添加範例 `.devcontainer/devcontainer.json`

### Phase 2：GitHub 發佈

1. [ ] Push 到 GitHub
2. [ ] 設定為 Template repository
3. [ ] 添加 Topics
4. [ ] 建立 Release（v1.0.0）
5. [ ] 撰寫 Release Notes

### Phase 3：測試驗證

1. [ ] 使用 Template 建立測試專案
2. [ ] 執行完整流程（Plan → Execute → QA）
3. [ ] 確認 SendText Bridge 正常運作
4. [ ] 收集反饋改進

---

## 📝 建議的 Repo 描述

**Short Description:**
```
Multi-agent development workflow template with GitHub Copilot & Codex CLI integration
```

**Full Description:**
```
A production-ready template for multi-agent collaborative development workflows. 
Features automated execution, Cross-QA rules, and SendText Bridge for Dev Container environments.

✅ Planner / Engineer / QA / Expert roles
✅ Codex CLI automation with monitoring
✅ JSONL audit logging
✅ L2 auto-rollback
✅ VS Code Extension (SendText Bridge)
```

---

## 🎯 未來改進

1. **CI/CD 整合**：自動測試 setup script
2. **多語言支援**：英文版文件
3. **視覺化工具**：Dashboard 顯示執行狀態
4. **Plugin 系統**：支援自訂技能擴充

---

**建立日期**: 2026-01-13
**維護者**: @foreverjojo
