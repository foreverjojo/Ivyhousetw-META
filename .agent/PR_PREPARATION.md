# 🚀 PR Preparation: Template v1.1.0 Integration

> **目標**：將 Ivyhousetw-META 專案的自動化改進合併到 `agent-workflow-template`
> **版本**：v1.0.0 → v1.1.0
> **日期**：2026-01-13

---

## 📦 需要合併的檔案清單

### 1️⃣ 新增檔案（New Files）

#### A. SendText Bridge Extension
```
tools/sendtext-bridge/
├── extension.js              ← 核心邏輯（v0.0.3，包含 /wait 端點）
├── package.json              ← 擴充配置（v0.0.3）
├── README.md                 ← 安裝與使用指南
└── sendtext-bridge-0.0.3.vsix ← 預編譯版本（方便直接安裝）
```

**說明**：
- `/send` 端點：發送文字到終端機（可選執行）
- `/wait` 端點：監測 git status 變更（輪詢模式，timeout 300s）
- 僅監聽 `127.0.0.1`（安全性考量）
- Token 驗證機制（`.agent/state/sendtext_bridge_token`）

#### B. 自動化執行腳本
```
.agent/scripts/
├── auto_execute_plan.sh      ← 自動化執行（發送 → 等待 → QA 提示）
├── run_codex_template.sh     ← 批次執行（同步回傳）
└── sendtext.sh               ← SendText Bridge CLI wrapper
```

**說明**：
- `auto_execute_plan.sh`：實現 Step 3 的「自動化模式」
- `run_codex_template.sh`：實現 Step 3 的「批次模式」
- `sendtext.sh`：簡化 curl 呼叫，提供 `text` / `enter` 子命令

#### C. 使用指南
```
tools/
└── SENDTEXT_BRIDGE_GUIDE.md  ← 完整使用指南（新建）
```

#### D. 發佈準備文件
```
.agent/
├── AGENT_WORKFLOW_TEMPLATE_PREP.md  ← 發佈準備文件
└── CHANGELOG_v1.1.0.md              ← 版本更新記錄
```

---

### 2️⃣ 修改檔案（Modified Files）

#### A. Workflow 文件
```
.agent/workflows/dev-team.md
```

**主要變更**：
- ✅ Step 3 新增「執行模式」章節：
  - 模式 A：GitHub Copilot 執行
  - 模式 B：Codex CLI 執行（批次模式 vs 自動化模式）
- ✅ 新增「執行模式比較表」
- ✅ 新增「完成流程」（建立 Log → 刪除 Plan → Git commit）
- ✅ Step 4 新增「觸發時機」說明（3 種模式）

**變更行數**：約 50 行新增

#### B. 移植腳本
```
.agent/scripts/setup_workflow.sh
```

**主要變更**：
- ✅ 6 步驟 → 8 步驟
- ✅ Step 6：複製 SendText Bridge 擴充與腳本
- ✅ Step 7：建立 `tools/SENDTEXT_BRIDGE_SETUP.md`
- ✅ 更新目錄結構輸出（包含 `tools/`, `.agent/scripts/`, `.agent/state/`）

**變更行數**：約 80 行新增

#### C. 可攜性指南
```
.agent/PORTABLE_WORKFLOW.md
```

**主要變更**（建議）：
- ✅ 新增「工具章節」（SendText Bridge 安裝）
- ✅ 更新「必須移植的檔案結構」（包含 `tools/`）
- ✅ 新增「工具驗證」步驟（檢查 HTTP 服務是否啟動）

**變更行數**：約 30 行新增

#### D. README.md
```
README.md
```

**主要變更**（建議）：
- ✅ 特色章節新增「自動化執行」
- ✅ 工具清單新增「SendText Bridge」
- ✅ 使用範例新增「自動化執行」範例
- ✅ 安裝步驟新增「工具安裝」

**變更行數**：約 40 行新增

---

### 3️⃣ 目錄結構變更

#### 新增目錄
```
tools/                         ← 新增（存放擴充與工具）
  └── sendtext-bridge/

.agent/state/                  ← 新增（存放 runtime 狀態）
  ├── sendtext_bridge_token
  └── sendtext_bridge_info.json
```

#### 更新 .gitignore
```
# Agent Workflow Runtime State
.agent/state/
.agent/backup/

# VS Code Extensions
*.vsix

# Temporary Files
*.tmp
*.log
```

---

## 📋 合併前檢查清單

### 功能驗證
- [ ] SendText Bridge 在 Dev Container 中可正常安裝
- [ ] `/send` 端點功能正常（文字發送到終端機）
- [ ] `/wait` 端點功能正常（監測 git status 變更）
- [ ] `auto_execute_plan.sh` 完整流程測試
- [ ] `sendtext.sh` CLI wrapper 功能正常

### 文件完整性
- [ ] README.md 更新完整（功能說明、安裝步驟、使用範例）
- [ ] CHANGELOG.md 記錄所有變更
- [ ] PORTABLE_WORKFLOW.md 包含工具移植步驟
- [ ] SendText Bridge 有獨立使用指南

### 相容性測試
- [ ] setup_workflow.sh 在空專案中可正常執行
- [ ] 舊專案可透過「只複製 tools/」的方式升級
- [ ] 未安裝 SendText Bridge 時，舊模式仍可正常運作

### 安全性檢查
- [ ] Token 機制正常（隨機生成、檔案權限 600）
- [ ] HTTP 服務僅監聽 127.0.0.1
- [ ] 無 Hard-coded 敏感資訊
- [ ] .gitignore 正確排除 `.agent/state/`

---

## 🔄 合併流程建議

### Phase 1: 核心檔案合併
1. 複製 `tools/sendtext-bridge/` 整個目錄
2. 複製 `.agent/scripts/auto_execute_plan.sh`
3. 複製 `.agent/scripts/run_codex_template.sh`
4. 複製 `.agent/scripts/sendtext.sh`

### Phase 2: 文件更新
1. 更新 `.agent/workflows/dev-team.md`
2. 更新 `.agent/scripts/setup_workflow.sh`
3. 更新 `README.md`
4. 新增 `tools/SENDTEXT_BRIDGE_GUIDE.md`
5. 新增 `CHANGELOG.md`

### Phase 3: 測試與驗證
1. 在測試專案執行 `setup_workflow.sh`
2. 驗證所有檔案正確複製
3. 測試 SendText Bridge 安裝流程
4. 執行完整的自動化執行流程

### Phase 4: 發佈
1. 建立 Git Tag `v1.1.0`
2. 撰寫 Release Notes（參考 CHANGELOG.md）
3. 更新 README.md 的版本標籤
4. 通知現有使用者升級

---

## 📊 預估影響

### 新增功能
- ✅ 自動化執行模式（發送 Plan → 監測完成 → QA）
- ✅ SendText Bridge 擴充（終端機文字注入）
- ✅ 批次執行模式（run_codex_template.sh）
- ✅ 完整的工具生態系統（tools/）

### 檔案統計
- **新增檔案**：8 個
- **修改檔案**：4 個
- **新增程式碼**：約 500 行
- **修改程式碼**：約 200 行

### 向下相容性
- ✅ 舊專案無需修改即可運作
- ✅ 新功能為「選用」而非「必須」
- ✅ 未安裝 SendText Bridge 時，手動模式仍可用

---

## 🎯 合併後驗收標準

### 必須通過的測試
1. **空專案初始化測試**
   ```bash
   ./setup_workflow.sh /tmp/test-project
   cd /tmp/test-project
   # 驗證所有檔案存在
   ```

2. **SendText Bridge 安裝測試**
   ```bash
   cd tools/sendtext-bridge
   npx --yes @vscode/vsce package
   code --install-extension *.vsix --force
   # Reload Window 後驗證
   curl http://127.0.0.1:38765/health
   ```

3. **自動化執行測試**
   ```bash
   .agent/scripts/auto_execute_plan.sh doc/plans/Idx-001_plan.md
   # 驗證：發送 → 等待 → QA 提示
   ```

4. **文件完整性測試**
   - [ ] README.md 所有連結可正常點擊
   - [ ] PORTABLE_WORKFLOW.md 步驟可正常執行
   - [ ] SENDTEXT_BRIDGE_GUIDE.md 所有範例可運作

---

## 📝 合併後的 TODO

### 短期（v1.1.x）
- [ ] 收集社群反饋
- [ ] 修正潛在 bug
- [ ] 新增使用範例（影片或截圖）
- [ ] 撰寫疑難排解文件

### 中期（v1.2.0）
- [ ] 支援多終端機監測
- [ ] 新增 `/status` 端點（查詢執行狀態）
- [ ] 優化 `/wait` 輪詢邏輯（減少 CPU 使用）
- [ ] 支援 WebSocket（即時通知）

### 長期（v2.0.0）
- [ ] SendText Bridge 發佈到 VS Code Marketplace
- [ ] 整合 GitHub Actions（自動化測試）
- [ ] 建立 Docker Image（開箱即用）
- [ ] 多語言支援（英文文件）

---

## 📧 聯絡與支援

- **GitHub Issues**: [agent-workflow-template/issues](https://github.com/foreverwow001/agent-workflow-template/issues)
- **Discussions**: [agent-workflow-template/discussions](https://github.com/foreverwow001/agent-workflow-template/discussions)

---

**最後更新**: 2026-01-13
**準備者**: GitHub Copilot
**審核者**: [待指定]
