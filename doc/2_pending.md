# 2_pending.md - AI Agent 工作流程系統待整合項目

> **文件狀態**: Pending Review  
> **建立日期**: 2025-01-12  
> **來源文件**:
> - `Agent_Workflow_System_Overview_v3.md`
> - `SimpleMem_MCP_Workflow_Guide.md`
> - Expert Analysis (Conversation Context)

---

## 目錄

1. [執行摘要](#1-執行摘要)
2. [Agent Workflow System Overview](#2-agent-workflow-system-overview)
3. [SimpleMem MCP Workflow Guide](#3-simplemem-mcp-workflow-guide)
4. [專家分析與建議](#4-專家分析與建議)
5. [階段性實施計劃](#5-階段性實施計劃)
6. [優先行動項目](#6-優先行動項目)
7. [附錄：原始文件內容](#7-附錄原始文件內容)

---

## 1. 執行摘要

### 1.1 文件概述

本文件彙整了 AI Agent 多角色協作開發工作流程系統的兩個核心架構文件，並提供專家分析與階段性實施建議。

**核心概念**:
- **SSOT (Single Source of Truth)**: 以 Repo 為唯一權威資料來源
- **三層記憶架構**: Chat History → SimpleMem → Repo
- **雙軌工作流**: Chat Workflow (探索) vs Dev Workflow (交付)
- **State Gate 系統**: 8 階段閘門控制任務生命週期

### 1.2 關鍵建議

| 優先級 | 項目 | 時程 |
|--------|------|------|
| P0 | 建立 `doc/handoffs/` 目錄結構 | 立即 |
| P1 | 完成 2-3 次手動 Handoff 測試 | 1-2 週 |
| P2 | 整合 SimpleMem MCP | 3-6 個月 |
| P3 | Coordinator Agent 升級 | 6-12 個月 |

---

## 2. Agent Workflow System Overview

> 來源: `Agent_Workflow_System_Overview_v3.md`

### 2.1 核心架構概念

#### 2.1.1 SSOT (Single Source of Truth)

```
┌─────────────────────────────────────────────────────┐
│                    SSOT 架構                         │
├─────────────────────────────────────────────────────┤
│  Chat History (短期記憶)                             │
│       ↓                                             │
│  SimpleMem (結構化決策記憶)                          │
│       ↓                                             │
│  Repository (唯一權威來源)                           │
│       • /doc/plans/*.md                             │
│       • /doc/logs/*.md                              │
│       • /doc/handoffs/*.md                          │
└─────────────────────────────────────────────────────┘
```

**原則**:
- Repo 是唯一權威資料來源
- Chat History 是暫存，不可依賴
- SimpleMem 是索引，指向 Repo 檔案

#### 2.1.2 Tooling 整合策略

| 工具 | 定位 | 適用場景 |
|------|------|----------|
| **Continue** | 探索 Agent | Chat Workflow、快速驗證想法 |
| **Copilot** | 精準編輯 Agent | Dev Workflow、程式碼實作 |
| **Codex CLI** | 批次執行 Agent | 大規模重構、自動化任務 |

**切換時機判斷**:
```
IF 任務類型 == "探索/研究" THEN
    使用 Continue (Chat Workflow)
ELSE IF 任務類型 == "精確實作" THEN
    使用 Copilot (Dev Workflow)
ELSE IF 任務類型 == "批次處理" THEN
    使用 Codex CLI
END IF
```

#### 2.1.3 Agent / Subagent / Skill 分層

```
┌─────────────────────────────────────────────────────┐
│                    Agent 層                         │
│  • 決策制定者                                        │
│  • 任務規劃與分配                                    │
│  • 擁有 Gate 權限                                    │
├─────────────────────────────────────────────────────┤
│                   Subagent 層                       │
│  • 分析與研究                                        │
│  • 不可直接修改程式碼                                 │
│  • 向上報告結果                                      │
├─────────────────────────────────────────────────────┤
│                    Skill 層                         │
│  • 純執行模組                                        │
│  • 無決策權                                          │
│  • 可被任何層級呼叫                                  │
└─────────────────────────────────────────────────────┘
```

### 2.2 Workflow 分離設計

#### 2.2.1 Chat Workflow (探索型)

**特性**:
- 無 Gate 限制
- 不寫入 Repo
- 產出為 Handoff Package
- 適用工具: Continue

**流程**:
```
User Question → Research → Analysis → Insight → Handoff Package
```

**Handoff Package 結構**:
```markdown
## Context
- 問題背景
- 已嘗試方案

## Decision
- 決策結論
- 選擇理由

## Next Steps
- 建議行動
- 優先順序

## References
- 相關檔案路徑
- SimpleMem entity IDs
```

#### 2.2.2 Dev Workflow (交付型)

**特性**:
- 8 Gate 控制
- 寫入 Repo
- 產出為可執行程式碼
- 適用工具: Copilot, Codex CLI

**8 Gate 系統**:

| Gate | 名稱 | 檢查點 |
|------|------|--------|
| G0 | TICKET_RECEIVED | 任務接收確認 |
| G1 | PLANNED | 計劃核准 |
| G2 | APPROVED | 方案核准 |
| G3 | IN_PROGRESS | 開發進行中 |
| G4 | CODE_COMPLETE | 程式碼完成 |
| G5 | QA_PASSED | QA 通過 |
| G6 | LOGGED | 日誌記錄完成 |
| G7 | CLOSED | 任務關閉 |

### 2.3 Insight 記錄機制

**何時記錄 Insight**:
- 發現新的設計模式
- 解決困難問題的方法
- 犯錯後的經驗教訓
- 效率提升的技巧

**Insight 結構**:
```markdown
## Insight: [標題]

### 情境
- 遇到什麼問題

### 發現
- 發現了什麼

### 應用
- 未來如何應用

### 標籤
- #category #subcategory
```

### 2.4 Skills Governance

**技能分類**:

| 類別 | 說明 | 範例 |
|------|------|------|
| **Core Skills** | 系統內建 | code_reviewer, test_runner |
| **Project Skills** | 專案特定 | domain_analyzer, report_generator |
| **User Skills** | 使用者自訂 | custom_formatter |

**技能安全等級**:
- **Level 0**: 唯讀，無風險
- **Level 1**: 可寫檔案，需確認
- **Level 2**: 可執行命令，需核准
- **Level 3**: 可存取外部服務，需授權

---

## 3. SimpleMem MCP Workflow Guide

> 來源: `SimpleMem_MCP_Workflow_Guide.md`

### 3.1 SimpleMem 概述

**定位**: 結構化記憶層，介於 Chat History 與 Repo 之間

**技術基礎**: SQLite-based MCP (Model Context Protocol)

**核心功能**:
- 持久化儲存決策歷程
- 支援跨 Session 查詢
- 提供關聯性搜尋

### 3.2 Triple Database 策略

```
┌─────────────────────────────────────────────────────┐
│                Triple Database 架構                  │
├─────────────────────────────────────────────────────┤
│  chat-knowledge.db                                  │
│  • Chat Workflow 產出                               │
│  • Insight 記錄                                     │
│  • 研究筆記                                         │
├─────────────────────────────────────────────────────┤
│  dev-plan.db                                        │
│  • Implementation Plans                             │
│  • Architecture Decisions                           │
│  • Task Breakdown                                   │
├─────────────────────────────────────────────────────┤
│  dev-log.db                                         │
│  • 執行日誌                                         │
│  • Gate 狀態記錄                                    │
│  • QA 報告                                          │
└─────────────────────────────────────────────────────┘
```

### 3.3 Chat Workflow 整合

**寫入時機**:
- 完成研究分析後
- 產出 Insight 時
- 建立 Handoff Package 時

**Entity 結構**:
```json
{
  "type": "insight|decision|research",
  "title": "簡短標題",
  "content": "詳細內容",
  "tags": ["category", "subcategory"],
  "references": ["file/path.md"],
  "created_at": "ISO8601",
  "session_id": "uuid"
}
```

### 3.4 Dev Workflow 整合

**讀取時機**:
- 任務開始前查詢相關決策
- 遇到問題時搜尋歷史解法
- QA 時對照原始需求

**寫入時機**:
- Gate 狀態變更時
- 產生 Log 時
- QA 報告完成時

### 3.5 Handoff 流程

```
┌─────────────────────────────────────────────────────┐
│              Chat → Dev Handoff 流程                 │
├─────────────────────────────────────────────────────┤
│  1. Chat Agent 完成研究                             │
│       ↓                                             │
│  2. 寫入 SimpleMem (chat-knowledge.db)              │
│       ↓                                             │
│  3. 產生 Handoff Package (含 entity ID)             │
│       ↓                                             │
│  4. Dev Agent 接收 Handoff                          │
│       ↓                                             │
│  5. 從 SimpleMem 拉取完整 Context                   │
│       ↓                                             │
│  6. 開始 Dev Workflow                               │
└─────────────────────────────────────────────────────┘
```

### 3.6 查詢模式

**關鍵字搜尋**:
```
simplemem search "authentication pattern"
```

**標籤過濾**:
```
simplemem list --tag=security --tag=api
```

**時間範圍**:
```
simplemem list --since="2025-01-01" --until="2025-01-12"
```

### 3.7 Governance 規則

| 規則 | 說明 |
|------|------|
| **不可取代 Repo** | SimpleMem 是索引，不是 SSOT |
| **必須記錄來源** | 每個 Entity 必須有 `references` 欄位 |
| **定期清理** | 超過 90 天未使用的 Entity 需審查 |
| **禁止敏感資料** | 密碼、Token 等禁止寫入 |

---

## 4. 專家分析與建議

### 4.1 風險評估

#### 4.1.1 高風險項目 (需優先處理)

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| **SimpleMem 依賴性** | 若 SimpleMem 服務不可用，Handoff 失敗 | 保持 Repo 檔案為 SSOT，SimpleMem 僅為輔助 |
| **工具切換摩擦** | Continue/Copilot/Codex 間切換成本高 | 建立清晰的切換 SOP，減少不必要切換 |
| **Gate 過度設計** | 8 Gate 可能造成流程僵化 | 允許小任務跳過部分 Gate |

#### 4.1.2 中風險項目

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| **Chat/Dev 邊界模糊** | 可能在 Chat 階段意外寫入 Repo | 明確定義 Chat Agent 為唯讀 |
| **Insight 過度記錄** | 雜訊過多導致搜尋困難 | 建立 Insight 品質標準 |
| **Triple DB 同步** | 三個資料庫可能不一致 | 定義同步檢查 Skill |

### 4.2 升級建議

#### 4.2.1 短期 (0-3 個月)

1. **建立 Handoff 目錄結構**
   ```
   doc/
   └── handoffs/
       ├── handoff.template.md
       ├── YYYYMMDD_taskname.md
       └── archive/
   ```

2. **Handoff Template 標準化**
   ```markdown
   # Handoff: [Task Name]
   
   ## Meta
   - From: Chat Agent (Continue)
   - To: Dev Agent (Copilot)
   - Date: YYYY-MM-DD
   - Session ID: (optional, for SimpleMem)
   
   ## Context
   [問題背景與研究過程]
   
   ## Decision
   [決策結論與選擇理由]
   
   ## Scope
   - In Scope: [明確範圍]
   - Out of Scope: [排除項目]
   
   ## Next Steps
   1. [具體行動項目]
   2. [優先順序]
   
   ## References
   - [相關檔案路徑]
   - [SimpleMem entity ID] (如有)
   ```

3. **測試 2-3 次手動 Handoff**
   - 驗證流程可行性
   - 收集改善回饋
   - 確認 Template 完整性

#### 4.2.2 中期 (3-6 個月)

1. **SimpleMem 整合**
   - 安裝 SimpleMem MCP
   - 建立 Triple DB
   - 訓練團隊使用

2. **自動化 Handoff**
   - 建立 `handoff_writer.py` Skill
   - 自動從 Chat 產出寫入 SimpleMem
   - 自動產生 Handoff 檔案

3. **Chat Workflow 正式化**
   - 定義 Chat Agent 角色
   - 建立 Chat-specific Skills
   - 設計 Insight 品質 Gate

#### 4.2.3 長期 (6-12 個月)

1. **Coordinator Agent 升級**
   - 自動判斷 Chat vs Dev Workflow
   - 自動分配工具 (Continue/Copilot/Codex)
   - 智能 Gate 管理

2. **跨專案知識共享**
   - 建立 Central SimpleMem
   - Insight 標籤標準化
   - 知識圖譜視覺化

### 4.3 Hybrid Approach 詳解

**推薦方案: SimpleMem 作為索引層，Repo 保持 SSOT**

```
┌─────────────────────────────────────────────────────┐
│                 Hybrid Architecture                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Chat Agent (Continue)                              │
│       │                                             │
│       ├──→ 寫入 SimpleMem (索引 + 摘要)             │
│       │         ↓                                   │
│       └──→ 寫入 Repo (完整 Handoff)                 │
│                 ↓                                   │
│  Dev Agent (Copilot)                                │
│       │                                             │
│       ├──→ 查詢 SimpleMem (快速定位)                │
│       │         ↓                                   │
│       └──→ 讀取 Repo (取得完整內容)                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**優點**:
- SimpleMem 加速搜尋與定位
- Repo 保持完整歷史記錄
- 即使 SimpleMem 失效，Repo 仍可用

**缺點**:
- 需要維護兩個資料來源
- 初期設定較複雜

---

## 5. 階段性實施計劃

### Phase 0: 基礎鞏固 (現在 - 1 個月)

**目標**: 在沒有 SimpleMem 的情況下，先跑通 Chat → Dev Handoff

**行動項目**:
- [x] 確認現有 Workflow 文件完整性
- [ ] 建立 `doc/handoffs/` 目錄
- [ ] 建立 `handoff.template.md`
- [ ] 執行 2-3 次手動 Handoff 測試
- [ ] 收集回饋並改善 Template

**成功指標**:
- Chat Agent 可產出符合 Template 的 Handoff
- Dev Agent 可從 Handoff 正確理解 Context
- 無需口頭補充說明

### Phase 1: Chat Workflow 正式化 (1-3 個月)

**目標**: 確立 Chat Workflow 的正式流程與產出標準

**行動項目**:
- [ ] 定義 Chat Agent 角色與邊界
- [ ] 建立 Chat-specific Skills (research, summarize, insight_writer)
- [ ] 設計 Insight 品質標準
- [ ] 建立 Chat → Dev 切換判斷樹
- [ ] 訓練團隊辨識 Chat vs Dev 場景

**成功指標**:
- Chat Workflow 有明確的 Entry Point
- Insight 記錄有一致的品質
- 團隊可正確判斷使用哪個 Workflow

### Phase 2: SimpleMem 整合 (3-6 個月)

**目標**: 將 SimpleMem 作為 Chat → Dev Handoff 的加速層

**行動項目**:
- [ ] 安裝並配置 SimpleMem MCP
- [ ] 建立 Triple DB (chat-knowledge, dev-plan, dev-log)
- [ ] 開發 `simplemem_writer.py` Skill
- [ ] 開發 `simplemem_reader.py` Skill
- [ ] 整合 Handoff Template 自動產生
- [ ] 訓練團隊使用 SimpleMem CLI

**成功指標**:
- Handoff 可自動寫入 SimpleMem
- Dev Agent 可從 SimpleMem 快速查詢相關 Context
- 查詢速度比純檔案搜尋快 50% 以上

### Phase 3: Coordinator 升級 (6-12 個月)

**目標**: 建立智能 Coordinator Agent，自動管理 Workflow 切換

**行動項目**:
- [ ] 設計 Coordinator Agent 架構
- [ ] 實作自動 Workflow 判斷
- [ ] 實作自動工具分配 (Continue/Copilot/Codex)
- [ ] 實作智能 Gate 管理
- [ ] 建立 Coordinator 效能監控

**成功指標**:
- 80% 以上任務可自動分配正確 Workflow
- 工具切換摩擦降低 50% 以上
- Gate 管理自動化率達 70% 以上

---

## 6. 優先行動項目

### P0 - 立即行動 (本週)

| 項目 | 負責人 | 預計完成 |
|------|--------|----------|
| 建立 `doc/handoffs/` 目錄 | - | 1 天 |
| 建立 `handoff.template.md` | - | 1 天 |
| 更新 README 說明 Handoff 流程 | - | 1 天 |

### P1 - 短期行動 (1-2 週)

| 項目 | 負責人 | 預計完成 |
|------|--------|----------|
| 執行第 1 次手動 Handoff 測試 | - | 3 天 |
| 收集回饋並改善 Template | - | 2 天 |
| 執行第 2 次手動 Handoff 測試 | - | 3 天 |
| 確認 Template 穩定 | - | 1 天 |

### P2 - 中期行動 (1-3 個月)

| 項目 | 負責人 | 預計完成 |
|------|--------|----------|
| 定義 Chat Agent 角色文件 | - | 1 週 |
| 建立 Insight 品質標準 | - | 1 週 |
| 開發 insight_writer Skill | - | 2 週 |
| Chat Workflow 試運行 | - | 2 週 |

### P3 - 長期行動 (3-6 個月)

| 項目 | 負責人 | 預計完成 |
|------|--------|----------|
| SimpleMem MCP 安裝配置 | - | 1 週 |
| Triple DB 設計與實作 | - | 2 週 |
| SimpleMem Skills 開發 | - | 3 週 |
| 整合測試與調優 | - | 2 週 |

---

## 7. 附錄：原始文件內容

### 7.1 Agent_Workflow_System_Overview_v3.md 摘要

**文件大綱**:
1. SSOT 架構設計
2. Tooling 整合策略 (Continue/Copilot/Codex)
3. Agent/Subagent/Skill 分層
4. Workflow 分離 (Chat vs Dev)
5. Insight 記錄機制
6. Skills Governance

**核心概念**:
- 強調 Repo 為唯一權威來源
- 區分探索型 (Chat) 與交付型 (Dev) 工作流
- 建立清晰的 Agent 權責劃分

### 7.2 SimpleMem_MCP_Workflow_Guide.md 摘要

**文件大綱**:
1. SimpleMem 技術概述
2. Triple Database 策略
3. Chat Workflow 整合
4. Dev Workflow 整合
5. Handoff 流程設計
6. 查詢模式與範例
7. Governance 規則

**核心概念**:
- SimpleMem 作為結構化記憶層
- 三個獨立資料庫分離關注點
- 明確的寫入時機與讀取時機

### 7.3 專家分析來源

本文件中的專家分析與建議，來自對上述兩份文件的綜合評估，考量因素包括：

- 實施複雜度
- 團隊學習曲線
- 風險與收益平衡
- 階段性推進可行性
- 現有工具整合成本

---

## 變更記錄

| 日期 | 版本 | 變更內容 |
|------|------|----------|
| 2025-01-12 | 1.0 | 初始版本，彙整兩份文件與專家分析 |

---

## 下一步

1. **審閱本文件** - 確認內容正確性
2. **建立 P0 項目** - 開始 `doc/handoffs/` 目錄建置
3. **排定 P1 測試** - 安排第一次手動 Handoff 測試
4. **回報進度** - 定期更新本文件狀態

---

*本文件由 AI Agent 系統自動產生，請人工審閱後確認。*
