---
description: 執行完整測試套件並產生覆蓋率報告
agent: build
model: anthropic/claude-3-5-sonnet-20241022
---
執行專案的完整測試套件，使用 pytest 並產生覆蓋率報告。

1. 運行測試：`pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html`
2. 檢查是否有失敗的測試
3. 如果有失敗，專注於失敗的測試並建議修復方案
4. 確保測試覆蓋率達標

請確保在執行前已安裝所有依賴：`pip install -r requirements.txt -r requirements-dev.txt`
