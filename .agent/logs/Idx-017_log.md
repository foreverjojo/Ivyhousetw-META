# Idx-017 Log｜從 Implementation Plan 移除 MCP Roadmap

**執行日期**：2026-01-18
**執行者**：OpenCode
**狀態**：✅ 已完成

## 1. 任務內容
- 你確認「MCP 概念不再需要納入本專案的 roadmap / implementation plan」。
- 目標是降低文件歧義：避免後續誤以為必須持續推 MCP（例如 Database MCP）。

## 2. 調整策略
- Implementation Plan：改成「工具整合/技能管理」描述，不再以 MCP 作為優先策略或階段名稱。
- 既有實作保留：repo 中 `.agent/mcp/` 與 `doc/MCP_USAGE.md` 不刪除，但不再作為 roadmap 的後續必做項。

## 3. 變更清單（文件）
- `doc/Implementation_Plan_index.md`
  - Phase 2.3：將「MCP 優先策略」文字改成中性描述（以實際落地方式為準）
  - Phase 4 Stage 2：改名為「工具整合（GitHub Explorer）」；移除 Database MCP 待辦
  - 記事：移除/改寫 MCP 戰略相關敘述（避免造成後續誤解）

## 4. 驗證
- 純文件變更：不影響程式執行。
