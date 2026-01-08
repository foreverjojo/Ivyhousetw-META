# 變更日誌

所有重要的專案變更都會記錄在此檔案中。

格式基於 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)，
本專案遵循 [語意化版本控制](https://semver.org/spec/v2.0.0.html)。

## [未發布]

### 規劃中
- Phase 4: Streamlit Crew Console MVP
- Trace ID 追蹤系統

## [0.3.0] - 2026-01-04

### 新增
- **Phase 3 多通路擴充完成**
  - 蝦皮整合 (shopee_adapter.py + Golden Test)
  - MOMO 整合 (momo_adapter.py + Golden Test)
- **P2 觀測性基礎建設**
  - 結構化 Logging (`core/logging.py`)
  - LLM 呼叫監控 (`core/llm_monitor.py`)
  - 版本管理機制 (VERSION, CHANGELOG.md)
- **工具探索流程改善**
  - CLI 工具探索 SOP (`.agent/skills/explore_cli_tool.md`)
  - 工具使用指南 (`doc/TOOL_USAGE.md`)
  - 更新 QA 角色與 dev-team workflow

### 變更
- Implementation Plan 更新：Phase 3 狀態同步

### 修正
- MOMO adapter: 修正 time_range 預設值以通過 Schema 驗證
- MOMO adapter: 優化 MOMO_COL_MAP 使用，提高可維護性

## [0.2.0] - 2026-01-04

### 新增
- **工程補強計畫 P1 完成**
  - 統一資料模型 (`schemas/unified_ad_data.json`)
  - Meta to Unified 轉換器 (`scripts/adapters/meta_adapter.py`)
  - 資料契約文件 (`doc/DATA_CONTRACT.md`)
- **驗收標準 (DoD)**
  - `doc/ACCEPTANCE_CRITERIA.md`
  - Golden Test 框架 (`tests/golden/`)
  - KPI 計算回歸測試
  - pytest 安裝與驗證

### 變更
- CI/CD Pipeline: 配置 Ruff linting

## [0.1.0] - 2026-01-03

### 新增
- **Phase 2.3 完成：Google Drive 整合**
  - Service Account 認證
  - 自動子資料夾分類 (reports/, assets/)
  - 媒體素材上傳與備份
- **總司令模式 (Commander Mode)**
  - 協作與審核機制優化
  - 技能注入 (Skill Injection)
- **Agent Skills 基礎架構**
  - `code_reviewer.py` - 自動代碼審查
  - `doc_generator.py` - 文件生成
  - `test_runner.py` - 測試執行工具
  - GitHub Explorer 動態技能獲取
- **三顧問多模態模型升級**
  - OpenRouter 共用 Key 機制
  - 支援 GPT-5.2, Gemini 3.0 Pro, Claude Opus 4.5

### 變更
- app.py 模組化重構 (1234行 → 808行)
  - 建立 `utils/`, `core/`, `ui/` 模組

### 資安
- 金鑰安全修補：`ifp.env` 加入 `.gitignore`
- 建立 `ifp.env.example` 範本檔

## [0.0.1] - 2026-01-02

### 新增
- 初始版本
- 核心功能 M0-M4 完成
- 開發團隊工作流程建立
- 艾薇手工坊系統開發核心守則

---

[Unreleased]: https://github.com/yourrepo/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/yourrepo/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/yourrepo/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yourrepo/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/yourrepo/releases/tag/v0.0.1
