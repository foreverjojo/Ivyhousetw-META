# ADR-0002: 採用 OpenRouter 作為統一 LLM API

## 狀態

✅ 已接受

## 背景

專案需要呼叫多個 LLM 模型：
- **顧問 A（數據）**：需要強大的邏輯推理能力
- **顧問 B（視覺）**：需要多模態（圖片/影片分析）能力
- **顧問 C（策略）**：需要市場洞察和文案能力
- **Moderator**：需要總結和決策能力

傳統做法需要分別整合 OpenAI、Google、Anthropic 的 API，管理多把 API Key。

## 決策

採用 **OpenRouter** 作為統一的 LLM API Gateway：
- 使用單一 API Key 呼叫所有模型
- 透過模型名稱前綴切換供應商（如 `openai/gpt-4`, `anthropic/claude-3`）

## 理由

1. **單一金鑰管理**：減少 API Key 外洩風險
2. **統一介面**：所有模型使用相同的 API 格式（OpenAI 兼容）
3. **成本透明**：統一的計費和用量監控
4. **模型切換容易**：只需改變模型名稱，無需改代碼
5. **備援能力**：若某供應商當機，可快速切換

## 後果

### 優點

- 簡化 API Key 管理（1 把 vs 3+ 把）
- 統一的錯誤處理和重試邏輯
- 方便比較不同模型的表現

### 缺點

- 增加一層代理，可能有少量延遲
- 依賴 OpenRouter 的可用性
- 某些供應商專屬功能可能不支援

## 替代方案

### 方案 A: 直接對接各供應商 API

**描述**：分別使用 OpenAI、Anthropic、Google 的官方 SDK

**未採用原因**：
- 需要管理多把 API Key
- 每個供應商的 API 格式不同
- 錯誤處理邏輯需要分別實作

### 方案 B: LiteLLM

**描述**：開源的 LLM API 統一層

**未採用原因**：
- 需要自行部署和維護
- OpenRouter 已提供類似功能且免維護

## 相關資訊

- **決策者**：Jonas
- **決策日期**：2025-12-15
- **相關檔案**：`scripts/llm_insights.py`, `scripts/consultants.py`, `core/env_loader.py`
- **環境變數**：`OPENROUTER_API_KEY`

---

**最後更新**：2026-01-10
