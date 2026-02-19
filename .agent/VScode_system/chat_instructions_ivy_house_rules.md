# Chat Instructions: Ivy House Rules

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

## 總結表格

| 項目 | 規範 |
|------|------|
| 語言 | 繁體中文 |
| 確認 | 變更前須複述+確認 |
| 角色 | Coordinator 不做實作 |
| Git 操作 | 只在 Project terminal / SCM |
| 觸發 | `/dev` 或 `/dev-team` |
| Marker | `[*_DONE]` 必須出現 |
| Cross-QA | last_change_tool ≠ qa_tool |
| Gates | 4 種 Gate 必須檢查 |
| 安全 | 敏感資料 → .env |
