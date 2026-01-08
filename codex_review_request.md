# Streamlit 即時渲染優化方案 - 技術審查請求

## 🎯 審查目的

請以技術審查專家的角色,對 Streamlit 效能優化計劃進行交叉分析，確保方案可行性與風險可控。

---

## 📋 背景問題

我們的 Streamlit 報告生成系統在兩個步驟中存在使用者體驗問題：

### Step C（LLM Insights 生成）

**現況**：
- 使用 `st.spinner()` 顯示等待訊息
- 同步呼叫 `generate_report_insights()`，需時 10-30 秒
- 僅在 API 完成後才一次性渲染結果
- 使用者不知道進度，等待體驗焦慮

**技術細節**：
- 檔案位置：`ui/steps.py:run_step_c()` (Line 469-522)
- API 呼叫：`scripts/llm_insights.py:generate_report_insights()`
- 已有 `realtime_container` 參數，但僅在完成後渲染一次

### Step E（三顧問諮詢）

**現況**：
- 三個 AI 顧問（成效 A / 視覺 B / 策略 C）**順序執行**
- 每位顧問需時 15-30 秒，總計 **45-90 秒**
- 同樣使用 `st.spinner()`，缺乏細節反饋
- 每位顧問完成後才顯示該顧問結果（已有 callback 機制）

**技術細節**：
- 檔案位置：`ui/steps.py:run_step_e()` (Line 569-626)
- 核心邏輯：`scripts/consultants.py:generate_consultant_notes()`
- API 呼叫：`scripts/consultants.py:_openrouter_chat_completion()` (同步函式)

---

## 💡 提出的解決方案

### 方案 A：快速改善（預計 1-2 小時）

**改動內容**：
1. 將 `st.spinner()` 替換為 `st.status()`，顯示階段性進度
   - Step C: 「🔍 正在分析本週 KPI」→「🤖 LLM 正在生成洞察」→「✅ 完成」
   - Step E: 「📊 成效顧問 A 正在分析」→「🎨 視覺顧問 B」→「🧠 策略顧問 C」→「✅ 完成」

2. 新增 **Skeleton Screen**（骨架屏）在等待時預覽結構
   - 新增 `scripts/json_to_readable.py:render_skeleton_insight()`
   - 新增 `scripts/json_to_readable.py:render_skeleton_consultant(role)`

3. 利用現有的 `realtime_container` 機制，改善初始化顯示

**優勢**：
- ✅ 無需改動 `scripts/` 業務邏輯
- ✅ 立即改善使用者體驗（進度可見性）
- ✅ 符合 Streamlit 最佳實踐

**限制**：
- ❌ 仍需等待完整 API 回應才能顯示結果
- ❌ 無法看到 LLM 生成的即時過程

---

### 方案 B：中期改善（預計 4-6 小時）

**改動內容**：
1. 改造 `scripts/consultants.py:_openrouter_chat_completion()` 支援 `stream=True`
2. 使用 `st.write_stream()` 逐 token 顯示 LLM 輸出
3. 改寫 `scripts/json_to_readable.py` 支援漸進式解析

**挑戰**：
- ⚠️ **OpenRouter API 的 streaming 模式與 `response_format: {"type": "json_object"}` 可能衝突**
- ⚠️ 需要設計「不完整 JSON」的顯示策略（先顯示原始文字？完成後格式化？）
- ⚠️ 錯誤處理更複雜（中斷、超時、格式錯誤）

---

## 🔍 需要你審查的重點

請基於你對 **Streamlit**、**Python async** 和 **LLM API** 的了解，評估：

### 1. 方案 A 技術可行性
- `st.status()` 和 Skeleton Screen 是否真的能改善體驗？
- 有沒有更好的 Streamlit 原生解決方案（如 `@st.fragment`、`st.empty()`）？
- 骨架屏的設計是否合理？

### 2. 方案 B 風險評估
- OpenRouter 的 **streaming 模式與 JSON 輸出模式**是否真的衝突？
- 有沒有替代方案（例如要求 LLM 分段輸出、使用 markdown 格式）？
- 流式解析 JSON 的技術難度如何（例如用 `json.loads()` 逐行解析 SSE）？

### 3. 並行執行可能性
- Step E 的三個顧問是否可以用 `asyncio` 或 `ThreadPoolExecutor` **並行執行**？
- 需要注意什麼（OpenRouter rate limit、Streamlit 的 threading 限制）？
- 是否會影響現有的 `on_consultant_done` callback 機制？

### 4. 檔案變更完整性
- 計劃中提到要修改：
  - `ui/steps.py` (run_step_c, run_step_e)
  - `pages/02_report_generation.py`（一鍵最終流程）
  - `scripts/json_to_readable.py`（新增骨架屏函式）
- 是否遺漏了其他關鍵檔案（例如 `scripts/consultants.py` 的 callback 機制）？

### 5. 實作優先序建議
- 你認為應該先做方案 A 還是直接上方案 B？
- 或者有第三種更優策略（例如先並行化三顧問，再考慮 streaming）？
- 如果做方案 A，有沒有需要預留的接口設計（方便未來升級到方案 B）？

---

## 📊 期望的審查輸出

請提供以下格式的分析：

```markdown
## ✅ 優勢分析
[對方案 A/B 的優勢評估]

## ⚠️ 風險評估
[潛在的技術風險、相容性問題]

## 💡 改進建議
[具體的技術改進建議，例如 API 設計、錯誤處理]

## 📋 實作優先序
1. [第一階段應做什麼]
2. [第二階段...]
3. [可選的後續優化...]
```

---

## 🗂️ 相關檔案參考

這份分析將用於決定最終實作路徑，請務必從**工程實務角度**給出建議：

- **主要檔案**：
  - `c:\Users\forev\.gemini\antigravity\brain\5248081b-ca5e-4885-a113-af49060675e5\implementation_plan.md.resolved`（完整計劃）
  - `ui/steps.py` (run_step_c, run_step_e)
  - `pages/02_report_generation.py`
  - `scripts/consultants.py`
  - `scripts/llm_insights.py`
  - `scripts/json_to_readable.py`

- **專案根目錄**：
  - `c:\Users\forev\OneDrive\4-管理專用\Jonas\AI生成\廣告數據報告\ivyhousetw ad analyzer\Ivyhousetw-META`

請基於實際的 Streamlit 和 Python 生態系統限制來評估，避免理論上可行但實務上難以實現的方案。謝謝！
