---
description: 檢查和修復程式碼風格與 lint 問題
agent: build
model: anthropic/claude-3-5-sonnet-20241022
---
檢查專案的程式碼風格和 lint 問題，使用 Ruff。

1. 運行 lint 檢查：`ruff check core utils scripts tests main.py --target-version=py311`
2. 檢查是否有風格問題
3. 如果有問題，自動修復：`ruff check --fix core utils scripts tests main.py`
4. 檢查格式：`ruff format --check core utils scripts tests main.py`
5. 如果格式不正確，自動格式化：`ruff format core utils scripts tests main.py`

遵循專案的程式碼風格規範：
- 行長：100 字元
- 引號：雙引號
- 縮排：4 空格
- 啟用規則：E, W, F, I, N, UP, B, C4
