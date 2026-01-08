# 艾薇手工坊 (Ivy House TW) - 系統開發核心守則

## 1. 核心溝通與行為規範

- **語言限制：** 所有對話、程式碼註解、文檔說明，嚴格使用 **「繁體中文 (Traditional Chinese)」**。
- **Dev Team 規範：** 虛擬團隊成員 (Planner, Engineer, QA) 的所有產出物 (Spec, Plan, Report) 必須完全使用繁體中文。
- **確認機制：** 在執行任何程式碼撰寫或架構變更前，**必須先複述一次需求**，並詢問使用者：「請問我的理解是否正確，可以開始執行嗎？」
- **遇到困難時的應對：**
  - 若連續 2 次修正錯誤失敗，**禁止**盲目嘗試。
  - **必須**使用搜尋工具，搜尋「截至目前最新的解決方案」或相關 GitHub Issue。
  - 回報時請說：「我嘗試修復但失敗了，根據最新的網路資訊，問題可能出在...，建議我們改用...方法。」

## 2. 系統藍圖與開發策略 (Architecture Strategy)

- **架構模式：** 採用 **Monorepo (單一儲存庫)** 架構。未來所有子系統 (ERP, HR, Finance) 統一管理。
- **資料庫策略 (Strategy A)：** 採用 **單一大資料庫 (Monolithic Database)**。
  - 所有系統共用同一個 DB 實例，以 `JOIN` 保持高效查詢。
  - **命名隔離：** 透過表格前綴區分模組 (如 `hr_`, `erp_`, `sys_`)。
  - **邏輯邊界：** 程式碼層級禁止跨模組直接 `INSERT/UPDATE`，必須呼叫該模組的 Service/API。
  - **未來彈性：** 保持模組間低耦合，以備未來遷移至微服務架構。
- **開發優先序 (Inside-Out Strategy)：**
  1. **Core:** 基礎資料建置 (商品、BOM、人員)。
  2. **Logic:** 內部訂單與庫存邏輯。
  3. **Finance:** 財務結算。
  4. **External:** 外部介面串接。

## 3. 開發流程與部署 (Workflow)

- **Git Flow：**
  1. **Local Dev:** 本地修改代碼。
  2. **Local Test:** **必須**在本地瀏覽器測試無誤。
  3. **Confirmation:** 確認功能正常後，才可執行 Push。
  4. **Deployment:** Push 至 `main` 分支觸發 Cloudflare Pages 自動部署。
- **Commit 訊息：** 遵循 Conventional Commits (如 `feat: 新增功能`, `fix: 修復問題`, `refactor: 重構`).

## 4. 開發技術規範

- **模組化路由**：程式碼須按功能拆分 (如 `/modules/parsers/`, `/modules/core/`)
- **檔案長度規範（分級制）**：
  - **主程式** (app.py, main.py): 建議 ≤ 600 行，嚴禁超過 800 行
  - **UI 模組** (ui/*.py): 建議 ≤ 500 行，嚴禁超過 600 行
  - **業務邏輯** (core/*.py, scripts/*.py): 建議 ≤ 400 行，嚴禁超過 500 行
  - **工具模組** (utils/*.py): 建議 ≤ 300 行，嚴禁超過 400 行
  - **測試檔案** (tests/*.py): 建議 ≤ 500 行，嚴禁超過 1000 行
- **檔案註釋**：每個檔案第一行必須說明該檔案用途、職責。
- **前端規範：**
  - **視覺風格：** 嚴格遵循「IVY FOODIE PALACE」品牌色系 (Cream, Ivy Green, Gold)。
  - **操作回饋：** 所有耗時操作必須有 Loading 動畫與 Toast 提示。
- **後端/API (未來)：** 建議使用 Node.js 或 Python，優先選擇 LTS 版本。

## 5. 資安與敏感資料 (Security)

- **絕對禁止：** 嚴禁將 API Key、密碼、Token 直接寫入源碼。
- **強制規範：** 所有敏感資料必須透過 `.env` 環境變數讀取。
- **Mock Data：** 本地開發一律使用模擬數據，確保無 Key 也能運行測試。

> **備註：** 本專案 (`picking-order-analyzer`) 目前為獨立運作的 MVP。未來將遷移至 Monorepo 架構下的 `/apps/picking-analyzer` 目錄。

## 6. Agent 自動化規範 (Agentic Workflow)

為確保跨 Session 開發的連續性，避免重複開啟終端機：

- **連線持久化 (Session Persistence)：**
    - ✅ **強制紀錄**：啟動長效型程序（如 `codex`, `npm run dev`, `streamlit`）時，Agent 必須將其 `Command ID` 與 `Process Name` 寫入 `.agent/active_sessions.json`。
    - ✅ **優先重用**：在執行指令前，先檢查 `.agent/active_sessions.json`，若有可用的 `Command ID` 則優先使用 `send_command_input` 進行操作。
- **QA 自動化標準：**
    - 雖然可以重用終端，但 QA 驗證邏輯仍須封裝為獨立腳本（如 `tests/verify_xxx.py`），以確保測試的可重複性與非互動式執行。
