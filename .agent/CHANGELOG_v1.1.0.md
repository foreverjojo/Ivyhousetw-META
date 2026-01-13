# 📝 Changelog: v1.1.0

> **Release Date**: 2026-01-13
> **Code Name**: Automation Boost
> **Type**: Minor Release (Feature Addition)

---

## 🎉 Highlights

本次更新新增了**自動化執行系統**，大幅提升了 Codex CLI 協作效率：

- ✨ **SendText Bridge Extension**：在 Dev Container 中實現終端機文字注入
- 🚀 **自動化執行模式**：Plan 發送後自動監測完成並提示 QA
- 📦 **完整工具生態**：批次執行、CLI wrapper、安裝腳本一應俱全
- 📚 **文件完善**：新增使用指南、升級 Workflow 說明

---

## ✨ New Features

### 1. SendText Bridge Extension (v0.0.3)

**位置**: `tools/sendtext-bridge/`

**功能**：
- **HTTP Bridge**: 在 Dev Container 內啟動 HTTP 服務（`127.0.0.1:38765`）
- **`/send` 端點**: 發送文字到 VS Code 終端機
  - 支援「輸入不執行」模式（`execute: false`）
  - 支援「輸入並執行」模式（`execute: true`）
- **`/wait` 端點**: 監測 git status 變更（自動完成檢測）
  - 輪詢模式（預設 2 秒間隔）
  - 可設定 timeout（預設 5 分鐘）
  - 回傳執行時間（elapsed）
- **`/enter` 端點**: 單獨發送 Enter 鍵
- **`/health` 端點**: 健康檢查
- **Token 驗證**: 隨機生成 token，保存於 `.agent/state/sendtext_bridge_token`

**使用場景**：
- 在對話框中向 Codex CLI 終端機發送 Plan
- 精準控制互動式程式輸入（如 `/status` + Enter）
- 自動化執行完成監測

**安全性**：
- 僅監聽 `127.0.0.1`（不對外開放）
- Token 隨機生成（40 字元）
- 檔案權限 600（僅擁有者可讀）

---

### 2. 自動化執行腳本

**位置**: `.agent/scripts/`

#### A. `auto_execute_plan.sh`

**功能**：實現「發送 Plan → 監測完成 → 提示 QA」的完整自動化流程

**流程**：
1. 讀取 Plan 檔案內容
2. 呼叫 `sendtext.sh` 發送到 Codex CLI 終端機
3. 呼叫 SendText Bridge `/wait` 端點（最多等待 5 分鐘）
4. 監測 git status 變更（輪詢模式，2 秒間隔）
5. 完成後輸出 QA prompt（提示使用者執行 QA）

**使用方式**：
```bash
.agent/scripts/auto_execute_plan.sh doc/plans/Idx-009_plan.md
```

**相依性**：
- SendText Bridge 已安裝並啟動
- `.agent/state/sendtext_bridge_token` 存在
- `jq` 已安裝（解析 JSON）
- Codex CLI 終端機已開啟

#### B. `run_codex_template.sh`

**功能**：批次執行模式（同步回傳結果）

**特色**：
- 使用 `codex exec` 執行
- 立即回傳 exit code
- JSONL 審計記錄（`.agent/codex_executions.jsonl`）
- 失敗時自動觸發 L2 Rollback

**使用方式**：
```bash
.agent/scripts/run_codex_template.sh doc/plans/Idx-009_plan.md
```

#### C. `sendtext.sh`

**功能**：SendText Bridge CLI wrapper（簡化 curl 呼叫）

**子命令**：
- `text <內容> [--execute]`: 發送文字（可選執行）
- `enter`: 單獨發送 Enter 鍵

**使用方式**：
```bash
# 發送並執行
.agent/scripts/sendtext.sh text "codex" --execute

# 先送文字，不 Enter
.agent/scripts/sendtext.sh text "/status"

# 單獨送 Enter
.agent/scripts/sendtext.sh enter
```

**環境變數**：
- `SENDTEXT_BRIDGE_PORT`: 自訂 port（預設 38765）
- `SENDTEXT_BRIDGE_TOKEN_FILE`: 自訂 token 檔案路徑

---

### 3. Workflow 文件更新

**位置**: `.agent/workflows/dev-team.md`

**新增章節**：

#### Step 3 執行模式擴充

新增「執行模式」說明：

**模式 A：GitHub Copilot 執行**
- 適用於：小規模修改（1-3 個檔案）、需要即時反饋
- 執行方式：由 Copilot 直接在 IDE 中實作

**模式 B：Codex CLI 執行**
- **批次模式**：使用 `run_codex_template.sh`（同步，立即回傳）
- **自動化模式**：使用 `auto_execute_plan.sh`（發送 → 監測 → QA 提示）

#### 執行模式比較表

| 模式 | 執行方式 | 回傳時機 | 監測機制 | 適用情境 |
|------|---------|---------|---------|---------|
| 批次模式 | `run_codex_template.sh` | 立即（exit code） | 無 | 快速驗證、測試 |
| 自動化模式 | `auto_execute_plan.sh` | 監測完成後 | `/wait` 端點 | 正式執行、無需手動等待 |

#### Step 4 觸發時機

新增「QA 觸發時機」說明：
- **批次模式**：執行完成後立即 QA
- **自動化模式**：`auto_execute_plan.sh` 完成後提示 QA prompt
- **手動模式**：Codex CLI 完成後手動呼叫 QA

#### 完成流程

新增「QA PASS 後續流程」：
1. 建立 Log：`doc/logs/Idx-XXX_log.md`
2. 刪除 Plan：`doc/plans/Idx-XXX_plan.md`
3. Git Commit：記錄所有變更

---

### 4. 移植腳本升級

**位置**: `.agent/scripts/setup_workflow.sh`

**變更**：6 步驟 → 8 步驟

**新增步驟**：

#### Step 6: 複製 SendText Bridge

```bash
# 複製擴充本體
cp -r "$SOURCE/../tools/sendtext-bridge" "$TARGET/tools/"

# 複製執行腳本
cp "$SOURCE/scripts/sendtext.sh" "$TARGET/.agent/scripts/"
cp "$SOURCE/scripts/auto_execute_plan.sh" "$TARGET/.agent/scripts/"
cp "$SOURCE/scripts/run_codex_template.sh" "$TARGET/.agent/scripts/"

# 設定執行權限
chmod +x "$TARGET/.agent/scripts/"*.sh
```

#### Step 7: 建立安裝說明

自動建立 `tools/SENDTEXT_BRIDGE_SETUP.md`，包含：
- 安裝步驟（打包 VSIX、安裝擴充）
- 驗證步驟（檢查 HTTP 服務）
- 使用範例（CLI wrapper）

**新增目錄**：
- `tools/`（存放擴充與工具）
- `.agent/state/`（存放 runtime 狀態）
- `.agent/scripts/`（執行腳本）

---

## 🔧 Improvements

### 1. 目錄結構優化

**新增目錄**：
```
your-project/
├── tools/                        ← 新增
│   └── sendtext-bridge/
│       ├── extension.js
│       ├── package.json
│       ├── README.md
│       └── *.vsix
├── .agent/
│   ├── scripts/                  ← 擴充
│   │   ├── sendtext.sh          ← 新增
│   │   ├── auto_execute_plan.sh ← 新增
│   │   └── run_codex_template.sh ← 新增
│   └── state/                    ← 新增（runtime 狀態）
│       ├── sendtext_bridge_token
│       └── sendtext_bridge_info.json
```

### 2. .gitignore 更新

**新增排除項目**：
```gitignore
# Agent Workflow Runtime State
.agent/state/
.agent/backup/

# VS Code Extensions
*.vsix

# Temporary Files
*.tmp
*.log
```

### 3. 執行權限自動設定

`setup_workflow.sh` 現在會自動設定所有 `.sh` 檔案的執行權限：
```bash
chmod +x "$TARGET/.agent/scripts/"*.sh
```

---

## 📚 Documentation

### 新增文件

1. **tools/SENDTEXT_BRIDGE_GUIDE.md**
   - 完整使用指南
   - 安裝步驟（Dev Container 環境）
   - 使用範例（curl / CLI wrapper）
   - 疑難排解

2. **.agent/PR_PREPARATION.md**
   - 合併準備文件
   - 檔案清單
   - 檢查清單
   - 測試步驟

3. **.agent/AGENT_WORKFLOW_TEMPLATE_PREP.md**
   - 發佈準備文件
   - 完整檔案結構
   - README 草稿
   - 發佈步驟

### 更新文件

1. **README.md**（建議更新）
   - 特色章節新增「自動化執行」
   - 工具清單新增「SendText Bridge」
   - 使用範例新增自動化執行範例

2. **.agent/PORTABLE_WORKFLOW.md**（建議更新）
   - 新增「工具章節」
   - 更新「檔案結構」
   - 新增「工具驗證」步驟

---

## 🐛 Bug Fixes

### 1. SendText Bridge README 內部連結問題

**問題**：打包 VSIX 時，內部連結會導致打包失敗

**解決**：
- 移除所有 `[.agent/scripts/sendtext.sh]` 內部連結
- 改為純文字描述「專案內建腳本位於 `.agent/scripts/`」

### 2. setup_workflow.sh 路徑問題

**問題**：相對路徑假設可能導致複製失敗

**解決**：
- 使用 `SCRIPT_DIR` 和 `dirname` 計算正確路徑
- 新增錯誤處理（檔案不存在時提示）

---

## ⚠️ Breaking Changes

**無破壞性變更**

本次更新**完全向下相容**：
- ✅ 舊專案無需修改即可運作
- ✅ 新功能為「選用」而非「必須」
- ✅ 未安裝 SendText Bridge 時，手動模式仍可用

---

## 🔄 Migration Guide

### 從 v1.0.0 升級到 v1.1.0

#### 選項 1：完整重新初始化（推薦新專案）

```bash
# 使用新版 setup_workflow.sh
.agent/scripts/setup_workflow.sh /path/to/new-project
```

#### 選項 2：手動複製（現有專案）

```bash
# 1. 複製 SendText Bridge
mkdir -p tools
cp -r /path/to/template/tools/sendtext-bridge tools/

# 2. 複製執行腳本
cp /path/to/template/.agent/scripts/sendtext.sh .agent/scripts/
cp /path/to/template/.agent/scripts/auto_execute_plan.sh .agent/scripts/
cp /path/to/template/.agent/scripts/run_codex_template.sh .agent/scripts/
chmod +x .agent/scripts/*.sh

# 3. 建立 state 目錄
mkdir -p .agent/state

# 4. 更新 .gitignore
cat >> .gitignore << EOF
.agent/state/
*.vsix
EOF

# 5. 安裝 SendText Bridge（可選）
cd tools/sendtext-bridge
npx --yes @vscode/vsce package
code --install-extension *.vsix --force
# Reload Window
```

#### 選項 3：僅升級 Workflow 文件

```bash
# 更新 dev-team.md（複製新版相關章節）
# 手動合併 Step 3 的「執行模式」說明
```

---

## 📊 Statistics

### 程式碼變更統計

- **新增檔案**: 8 個
- **修改檔案**: 4 個
- **新增程式碼**: 約 500 行
- **修改程式碼**: 約 200 行
- **新增文件**: 約 1000 行

### 功能覆蓋範圍

- **SendText Bridge Extension**: 100% 功能完成
- **自動化執行腳本**: 100% 功能完成
- **CLI Wrapper**: 100% 功能完成
- **Workflow 文件**: 100% 更新完成
- **移植腳本**: 100% 升級完成

### 測試覆蓋率

- **單元測試**: N/A（Shell 腳本）
- **整合測試**: ✅ 手動測試通過
- **端對端測試**: ✅ 完整流程測試通過
- **相容性測試**: ✅ 舊專案相容性驗證通過

---

## 🙏 Acknowledgments

- **GitHub Copilot**: 程式碼實作與文件撰寫
- **Codex CLI**: 批次執行與自動化靈感
- **VS Code Extension API**: SendText Bridge 實現基礎

---

## 📅 Roadmap

### v1.1.x (Patch Releases)
- [ ] 修正潛在 bug
- [ ] 新增使用範例（影片/截圖）
- [ ] 疑難排解文件

### v1.2.0 (Next Minor)
- [ ] 多終端機支援
- [ ] `/status` 端點（查詢執行狀態）
- [ ] WebSocket 即時通知
- [ ] 優化輪詢邏輯（減少 CPU 使用）

### v2.0.0 (Next Major)
- [ ] SendText Bridge 發佈到 Marketplace
- [ ] GitHub Actions 自動化測試
- [ ] Docker Image（開箱即用）
- [ ] 多語言文件支援

---

## 📝 Notes

### 已知限制

1. **SendText Bridge 限制**:
   - 僅支援 Dev Container 環境
   - 需要手動安裝擴充（未發佈到 Marketplace）
   - 輪詢模式可能增加 CPU 使用率

2. **自動化執行限制**:
   - 依賴 git status 檢測（需乾淨 worktree）
   - 最多等待 5 分鐘（可調整）
   - 需要 `jq` 工具（解析 JSON）

3. **相依性需求**:
   - Node.js 18+ (打包 VSIX)
   - jq (JSON 解析)
   - curl (HTTP 呼叫)
   - VS Code 1.85+ (擴充 API)

### 未來改進方向

1. **效能優化**:
   - 使用 `inotify` / `fswatch` 取代輪詢
   - WebSocket 即時通知
   - 降低 CPU 使用率

2. **使用體驗**:
   - 發佈到 VS Code Marketplace（一鍵安裝）
   - 提供預建的 Docker Image
   - 自動檢測環境並安裝工具

3. **功能擴充**:
   - 支援多終端機監測
   - 支援自訂監測條件（不限 git status）
   - 提供進度回報（％ 完成度）

---

**Release Tag**: `v1.1.0`
**Release Date**: 2026-01-13
**Released by**: GitHub Copilot
**Approved by**: [待指定]
