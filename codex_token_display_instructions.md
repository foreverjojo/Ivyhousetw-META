你好！我是 Antigravity，已更新完 Token 顯示功能的實施計劃，整合了你之前提出的三個風險提醒。

請協助實作 Token 顯示功能（只做 Step C，Step E 之後再做）。

## 核心改動

### 1. scripts/llm_insights.py

**任務 1-1：修改 `_openrouter_chat_completion()` 回傳 tuple**

在 Line 27-92 範圍內：
- 將回傳型別從 `str` 改為 `Tuple[str, Dict[str, int]]`
- 在 return 前提取 usage（已有的 L70-73 邏輯保持）
- 回傳格式：`return (content, {"prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...})`

**任務 1-2：修改 `generate_report_insights()` 使用可選參數**

在 Line 116-182 範圍內：
1. 新增參數：`return_usage: bool = False`
2. 修改回傳型別：`Union[Dict[str, Any], Tuple[Dict[str, Any], Dict[str, int]]]`
3. **關鍵改動**：累計 repair token
   - 第一次呼叫：`content, usage_main = _openrouter_chat_completion(...)`
   - Repair 時：`content2, usage_repair = _openrouter_chat_completion(...)`
   - 累計：`total_usage = {各欄位相加}`
4. 最後：
   ```python
   if return_usage:
       return (out, total_usage)
   return out  # 向後相容
   ```

### 2. ui/steps.py

**任務 2：修改 `run_step_c()` 顯示 token**

在 Line 503-526 範圍內（已經有 st.status 的版本）：
1. 修改 L513（或類似位置）的呼叫：
   ```python
   insights, usage = generate_report_insights(
       rs_with_context(...),
       return_usage=True
   )
   ```

2. 在 realtime_container 渲染洞察後，加上 token 顯示（約 L519-524）：
   ```python
   if realtime_container is not None:
       try:
           readable = render_report_insights(insights)
           realtime_container.markdown(readable)
           
           # 新增：Token 用量顯示
           realtime_container.caption(
               f"📊 Token 用量：總計 {usage['total_tokens']:,} "
               f"（輸入 {usage['prompt_tokens']:,}｜輸出 {usage['completion_tokens']:,}）"
           )
       except Exception as e:
           logger.warning("即時渲染失敗", error=str(e))
   ```

## 重點提醒

1. **向後相容**：舊的呼叫者（不傳 `return_usage` 或傳 `False`）仍正常運作
2. **累計 repair token**：避免低估成本
3. **顯示位置**：放在 `realtime_container`（與洞察內容一起），不要放在 `st.status` 裡
4. **格式**：使用 `st.caption()`，格式為「總計 X（輸入 Y｜輸出 Z）」

## 規範提醒

- 遵循 ivy_house_rules.md
- 檔案開頭保留中文用途註釋
- 無 Hard-code API Key
- 單檔不超過 500 行

請實作後回報修改的檔案與關鍵行號。完成後我會進行 QA 交叉審核。
