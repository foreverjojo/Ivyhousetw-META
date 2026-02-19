---
description: 啟動開發團隊工作流程
agent: plan
model: anthropic/claude-3-5-sonnet-20241022
---
啟動專案的開發團隊工作流程，遵循 dev-team.md 的規範。

1. 確認用戶需求並說明開發目標
2. 閱讀 ivy_house_rules.md 確認核心規範
3. 如果是功能開發任務，產出 Plan 到 doc/plans/Idx-NNN_plan.md
4. 如果是工作流/治理改善任務，產出 Plan 到 .agent/plans/Idx-NNN_plan.md
5. 確保 Plan 包含必要的段落：
   - ## 📋 SPEC
   - ## 🔍 RESEARCH & ASSUMPTIONS
   - ## 🔒 SCOPE & CONSTRAINTS
6. 等待用戶確認後進入下一步

這個命令用於協調開發團隊的各個角色（Planner, Meta Expert, Engineer, QA）。
