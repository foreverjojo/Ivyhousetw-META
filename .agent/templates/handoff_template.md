# 工具切換提綱範本 (Handoff Template)

> **用途**：在 AI 工具之間切換時，確保上下文不遺失
> **適用場景**：Copilot Chat ↔ Continue ↔ Codex 切換

---

## 基本資訊

| 欄位 | 內容 |
|-----|------|
| **切換時間** | YYYY-MM-DD HH:MM |
| **從工具** | [Copilot Chat / Continue / Codex / Claude / Cursor] |
| **到工具** | [Copilot Chat / Continue / Codex / Claude / Cursor] |
| **切換原因** | [額度用盡 / 複雜對話 / 重大決策 / 超長上下文 / 其他] |

---

## 任務狀態

| 欄位 | 內容 |
|-----|------|
| **目前 Index** | Idx-___ |
| **Plan Status** | [NOT_STARTED / APPROVED / IN_PROGRESS / QA / CLOSED] |
| **Executor 決策** | [Codex / 直接實作 / 未決定] |
| **現在進行到** | [Plan / Implement / QA / Log] |

---

## 待處理項目

- [ ] 項目 1
- [ ] 項目 2
- [ ] 項目 3

---

## 關鍵檔案位置

| 檔案類型 | 路徑 |
|---------|------|
| **Plan** | `doc/plans/Idx-___plan.md` |
| **Log（預期）** | `doc/logs/Idx-___log.md` |
| **主要程式碼** | `scripts/...` |
| **測試檔案** | `tests/...` |

---

## 上下文摘要

### 目前討論到哪裡

[簡述當前進度]

### 關鍵決策

1. [決策 1]
2. [決策 2]

### 下一步是什麼

[明確的下一步行動]

---

## 注意事項

- [需要特別注意的事項]
- [可能的風險或陷阱]

---

## 切換 SOP

```
步驟 1：在原工具中填寫本提綱
        ↓
步驟 2：複製提綱內容
        ↓
步驟 3：切換到新工具，貼上提綱作為開場
        ↓
步驟 4：新工具基於提綱 + 工件（Index/Plan/Log）接續工作
        ↓
步驟 5：更新 .agent/handoff_log.jsonl（可選，用於審計）
```

---

## 核心原則

1. **同一時刻只有一個工具當 Moderator**（不要同時用兩個 Chat）
2. **切換時一定要用「提綱挈領」**（不靠記憶，靠文件）
3. **工件（Index / Plan / Log）是切換的橋樑**

---

**範本版本**：v1.0
**最後更新**：2026-01-10
