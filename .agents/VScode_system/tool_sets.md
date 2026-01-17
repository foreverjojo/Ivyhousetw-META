# Tool Sets

Ivy House 共通指令（所有 Agent 必遵守）

---

## 1️⃣ 語言

所有回覆、Spec、Plan、Log、註解均使用**繁體中文**。

---

## 2️⃣ 確認機制

任何程式碼變更前，必須：
1. 複述需求
2. 等待用戶確認

---

## 3️⃣ 角色邊界

- **Coordinator** 不做實作
- 程式碼變更只允許透過：
  - `codex-cli`
  - `opencode`

---

## 4️⃣ git/diff 限制

所有 git/diff/行數計算只允許在：
- Project terminal
- VS Code SCM

**禁止**：
- 注入到 Codex/OpenCode terminal
- 在 Codex CLI 中執行 git 指令

---

## 5️⃣ Workflow 觸發

使用者輸入 `/dev` 視為啟動（相容 `/dev-team`）。

---

## 6️⃣ Completion Markers

以下 marker 未出現視為未完成：
- `[ENGINEER_DONE]`
- `[QA_DONE]`
- `[FIX_DONE]`

---

## 7️⃣ Cross-QA 規則

QA 工具不得等於 `last_change_tool`

**例外**：需明確記錄並由用戶確認。

---

## 8️⃣ Deterministic Gates

以下 Gate 必須按規範執行並寫入 Log：

### Research Gate
- 若 `research_required: true` 或依賴檔案變更
- 必須補 Sources（Link-required）或標 `RISK: unverified`

### Maintainability Gate
- 有 `.py` 變更且總行數>50 或命中 `core/**|utils/**|config.py`
- Log 必有 `MAINTAINABILITY REVIEW`（只給建議，不改 code）

### UI/UX Gate
- 命中 UI 路徑時
- Log 的 `SCOPE GATE` 記 `UI/UX triggered: YES/NO`
- YES 時 QA 必有 `UI/UX CHECK`

### Evidence Gate
- 只有在（變更行數>200）或（需要貼完整終端輸出且>80行）才允許新增 evidence

---

## 9️⃣ Security

- 不得硬寫任何 key/token
- 敏感資料只能用 `.env`

---

## 已可用的工具集

### Executor Tools
- **codex-cli** - 程式碼生成與執行
- **opencode** - 輔助型程式碼工具

### Terminal Tools
- **Project Terminal** - 執行 git/bash 指令
- **Codex CLI Terminal** - codex 指令執行
- **OpenCode CLI Terminal** - opencode 指令執行

### Monitoring Tools
- **VS Code Proposed API** - 終端輸出監控（若可用）
- **Marker Detection** - 完成 marker 偵測

### Documentation Tools
- **Markdown Logger** - `.md` 格式日誌
- **Plan Generator** - `doc/plans/Idx-XXX_plan.md`
- **Log Generator** - `doc/logs/Idx-XXX_log.md`

---

## 使用限制速查表

| 工具 | 允許 | 禁止 |
|------|------|------|
| codex-cli | 程式碼變更 | git 操作 |
| opencode | 程式碼變更 | git 操作 |
| Project Terminal | git / bash | 無 |
| Coordinator | Gate 判定、注入指令 | 直接執行程式碼 |

---

## 調用流程

1. **SPEC_MODE**：Coordinator 複述需求並等待確認
2. **Plan 產出**：要求 Planner 產出 `doc/plans/Idx-XXX_plan.md`
3. **Plan 確認**：等待用戶核准
4. **ORCH_MODE**：記錄 `executor_tool` 並開始執行
5. **終端注入**：使用 `terminal.sendText` 注入到已啟動的工具
6. **Marker 監控**：等待 `[*_DONE]` marker 出現
7. **Log 回填**：產生 `doc/logs/Idx-XXX_log.md`
