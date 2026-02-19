# Architecture Decision Records (ADR)

> **用途**：記錄重大架構決策及其理由，方便未來追溯與知識傳承
> **格式**：每個決策一個檔案，命名為 `NNNN-title.md`

---

## 📋 決策清單

| # | 標題 | 狀態 | 日期 |
|---|------|------|------|
| [0001](0001-use-streamlit-for-ui.md) | 採用 Streamlit 作為 UI 框架 | ✅ 已接受 | 2025-12-01 |
| [0002](0002-openrouter-unified-api.md) | 採用 OpenRouter 作為統一 LLM API | ✅ 已接受 | 2025-12-15 |
| [0003](0003-multi-agent-workflow.md) | 採用多代理工作流程治理 | ✅ 已接受 | 2026-01-09 |

---

## 📝 如何新增 ADR

1. 複製範本：`cp doc/adr/0000-template.md doc/adr/NNNN-title.md`
2. 填寫所有區塊
3. 更新本索引檔
4. 提交 commit：`docs: add ADR-NNNN title`

---

## 🔗 參考資源

- [ADR GitHub](https://adr.github.io/)
- [Markdown Any Decision Records](https://adr.github.io/madr/)
