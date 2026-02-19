# Skill: Codex CLI Collaboration Bridge

## Context
本專案採用「總司令模式」：
- **Antigravity (IDE Agent)**：擔任「總司令」，負責規劃、Spec 撰寫、品質驗證 (QA) 與計畫追蹤。
- **Codex CLI (Terminal Agent)**：擔任「前線士兵」，負責執行大規模代碼撰寫與修改，以節省主 Agent 額度。

## 觸發條件
當使用者要求「使用 Codex 修復」、「用終端機改程式」或「執行大規模實作」時。

## 執行規則
1. **指示而非實作**：不要直接進入 `EXECUTION` 模式撰寫大量代碼，應產出「開發規格書 (Spec)」。
2. **生成 CLI 指令**：提供可在終端機運行的 `codex edit` 指令。
3. **格式規範**：
   ```bash
   codex edit <filename> --instruction "<引述規格書的具體要求>"
   ```
4. **驗證流程**：要求使用者執行完畢後回報，並由主 Agent 執行 `view_file` 與 `code_reviewer.py` 進行檢查。

## 優先序
1. 繁體中文註釋要求。
2. 500 行代碼限制要求。
3. 無 Hard-code API Key 要求。
