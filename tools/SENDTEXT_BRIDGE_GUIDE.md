# 📡 SendText Bridge 完整使用指南

> **版本**: v0.0.3
> **適用環境**: VS Code Dev Container
> **更新日期**: 2026-01-13

---

## 📖 目錄

1. [什麼是 SendText Bridge？](#什麼是-sendtext-bridge)
2. [為什麼需要它？](#為什麼需要它)
3. [安裝步驟](#安裝步驟)
4. [驗證安裝](#驗證安裝)
5. [使用方式](#使用方式)
6. [API 文件](#api-文件)
7. [進階用法](#進階用法)
8. [疑難排解](#疑難排解)
9. [安全性說明](#安全性說明)
10. [常見問題](#常見問題)

---

## 🤔 什麼是 SendText Bridge？

SendText Bridge 是一個 VS Code 擴充，在 **Dev Container（Remote）** 端啟動一個 **僅限本機 `127.0.0.1`** 的 HTTP 服務。

它允許你在 container 內使用 `curl` 或腳本呼叫 VS Code 的 `terminal.sendText()` API，實現：

- ✅ 在對話框中直接向終端機發送文字
- ✅ 控制是否「立即執行」（按 Enter）
- ✅ 精準控制互動式程式輸入（如 `/status` + Enter）
- ✅ 監測 git status 變更（自動完成檢測）

---

## 💡 為什麼需要它？

### 問題背景

在 **Dev Container** 環境中，你無法直接從 Shell 腳本呼叫 VS Code Extension API。

例如，你想在對話框中說：

> **「向 Codex CLI 終端機發送這段 Plan」**

傳統方式需要：
1. 複製 Plan 內容
2. 手動切換到終端機
3. 貼上並執行

這在自動化場景中非常不便。

### SendText Bridge 解決方案

有了 SendText Bridge，你可以：

```bash
# 在對話框執行
.agent/scripts/sendtext.sh text "請執行 Plan" --execute

# 文字會自動發送到 Codex CLI 終端機並執行
```

---

## 🚀 安裝步驟

### 前置需求

- ✅ VS Code 1.85+
- ✅ Dev Container 環境
- ✅ Node.js 18+ (用於打包 VSIX)

### 步驟 1: 打包 VSIX

```bash
cd tools/sendtext-bridge

# 使用 npx 打包（不需要全域安裝 vsce）
npx --yes @vscode/vsce package --allow-missing-repository --no-dependencies
```

**輸出**：`sendtext-bridge-0.0.3.vsix`

### 步驟 2: 安裝擴充到 Dev Container

**方法 A: 使用 Remote `code` CLI（推薦）**

```bash
# 在 Dev Container 內執行
code --install-extension tools/sendtext-bridge/sendtext-bridge-0.0.3.vsix --force
```

**方法 B: 使用 VS Code UI**

1. 按 `Ctrl+Shift+P`
2. 輸入 `Extensions: Install from VSIX...`
3. 選擇 `tools/sendtext-bridge/sendtext-bridge-0.0.3.vsix`

### 步驟 3: 重新載入 Window

1. 按 `Ctrl+Shift+P`
2. 輸入 `Developer: Reload Window`
3. 等待 VS Code 重新啟動

---

## ✅ 驗證安裝

### 檢查 HTTP 服務

在 Dev Container 內執行：

```bash
curl -sS http://127.0.0.1:38765/health
```

**預期輸出**：
```json
{"ok":true}
```

### 檢查 Token 檔案

```bash
ls -la .agent/state/sendtext_bridge_token
cat .agent/state/sendtext_bridge_token
```

**預期輸出**：
- 檔案存在，權限 `600`（僅擁有者可讀）
- 內容為 40 字元的隨機字串

### 檢查 Info 檔案

```bash
cat .agent/state/sendtext_bridge_info.json
```

**預期輸出**：
```json
{
  "port": 38765,
  "host": "127.0.0.1",
  "tokenFile": "/workspaces/your-project/.agent/state/sendtext_bridge_token",
  "endpoints": {
    "/health": "GET - Health check",
    "/send": "POST - Send text to terminal",
    "/enter": "POST - Send Enter key",
    "/wait": "POST - Wait for git status changes"
  },
  "version": "0.0.3"
}
```

---

## 📝 使用方式

### A. 使用 CLI Wrapper（推薦）

專案提供了封裝腳本 `.agent/scripts/sendtext.sh`，簡化使用。

#### 1. 發送文字並執行

```bash
.agent/scripts/sendtext.sh text "codex" --execute
```

**等同於**：在終端機輸入 `codex` 並按 Enter

#### 2. 發送文字不執行

```bash
.agent/scripts/sendtext.sh text "/status"
```

**等同於**：在終端機輸入 `/status`（游標停在行尾）

#### 3. 單獨發送 Enter

```bash
.agent/scripts/sendtext.sh enter
```

**等同於**：在終端機按 Enter

#### 4. 組合使用（互動式程式）

```bash
# 先輸入指令
.agent/scripts/sendtext.sh text "/status"

# 暫停 1 秒（讓使用者看到輸入內容）
sleep 1

# 再按 Enter
.agent/scripts/sendtext.sh enter
```

---

### B. 使用 curl（進階）

#### 準備 Token

```bash
TOKEN=$(cat .agent/state/sendtext_bridge_token)
PORT=38765
```

#### 1. 發送文字並執行

```bash
curl -sS -X POST "http://127.0.0.1:${PORT}/send" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"text":"codex","execute":true}'
```

#### 2. 發送文字不執行

```bash
curl -sS -X POST "http://127.0.0.1:${PORT}/send" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"text":"/status","execute":false}'
```

#### 3. 單獨發送 Enter

```bash
curl -sS -X POST "http://127.0.0.1:${PORT}/enter" \
  -H "Authorization: Bearer ${TOKEN}"
```

#### 4. 監測 git status 完成

```bash
curl -sS -X POST "http://127.0.0.1:${PORT}/wait" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"timeout":300000,"checkInterval":2000}'
```

**參數說明**：
- `timeout`: 最大等待時間（毫秒），預設 300000（5 分鐘）
- `checkInterval`: 輪詢間隔（毫秒），預設 2000（2 秒）

**回應範例**：
```json
{
  "ok": true,
  "completed": true,
  "elapsed": 12345
}
```

---

## 📚 API 文件

### 端點清單

| 端點 | 方法 | 功能 | 需要 Token |
|------|------|------|-----------|
| `/health` | GET | 健康檢查 | ❌ |
| `/send` | POST | 發送文字 | ✅ |
| `/enter` | POST | 發送 Enter | ✅ |
| `/wait` | POST | 監測完成 | ✅ |

---

### 1. `/health` - 健康檢查

**請求**：
```bash
GET /health
```

**回應**：
```json
{
  "ok": true
}
```

**用途**：驗證 HTTP 服務是否啟動

---

### 2. `/send` - 發送文字到終端機

**請求**：
```bash
POST /send
Authorization: Bearer <token>
Content-Type: application/json

{
  "text": "codex",
  "execute": true
}
```

**參數**：
- `text` (必填): 要發送的文字
- `execute` (選填): 是否立即執行（按 Enter），預設 `false`

**回應**：
```json
{
  "ok": true
}
```

**錯誤回應**：
```json
{
  "ok": false,
  "error": "No text provided"
}
```

---

### 3. `/enter` - 發送 Enter 鍵

**請求**：
```bash
POST /enter
Authorization: Bearer <token>
```

**回應**：
```json
{
  "ok": true
}
```

**用途**：與 `/send` (execute: false) 組合使用，實現精準控制

---

### 4. `/wait` - 監測 git status 完成

**請求**：
```bash
POST /wait
Authorization: Bearer <token>
Content-Type: application/json

{
  "timeout": 300000,
  "checkInterval": 2000
}
```

**參數**：
- `timeout` (選填): 最大等待時間（毫秒），預設 300000（5 分鐘）
- `checkInterval` (選填): 輪詢間隔（毫秒），預設 2000（2 秒）

**回應（成功）**：
```json
{
  "ok": true,
  "completed": true,
  "elapsed": 12345
}
```

**回應（逾時）**：
```json
{
  "ok": false,
  "completed": false,
  "error": "Timeout waiting for changes"
}
```

**工作原理**：
1. 每隔 `checkInterval` 毫秒執行 `git status --porcelain`
2. 若輸出不為空（有變更），回傳 `completed: true`
3. 若超過 `timeout` 仍無變更，回傳 `completed: false`

---

## 🔥 進階用法

### 1. 自動化執行 Plan

使用 `auto_execute_plan.sh` 實現完整自動化：

```bash
.agent/scripts/auto_execute_plan.sh doc/plans/Idx-009_plan.md
```

**流程**：
1. 讀取 Plan 檔案
2. 發送到 Codex CLI 終端機（`sendtext.sh text --execute`）
3. 呼叫 `/wait` 端點監測完成（最多 5 分鐘）
4. 完成後輸出 QA prompt

### 2. 批次執行多個 Plan

```bash
for plan in doc/plans/Idx-*.md; do
  echo "執行: $plan"
  .agent/scripts/auto_execute_plan.sh "$plan"
  sleep 5  # 每個 Plan 間隔 5 秒
done
```

### 3. 客製化監測邏輯

```bash
# 監測特定檔案變更（不限 git status）
while true; do
  if [[ -f "output.txt" ]]; then
    echo "✅ 檔案已產生"
    break
  fi
  sleep 2
done
```

### 4. 整合到 CI/CD

```yaml
# .github/workflows/auto-execute.yml
- name: Execute Plan
  run: |
    .agent/scripts/auto_execute_plan.sh doc/plans/Idx-001_plan.md
```

---

## 🐛 疑難排解

### 問題 1: curl 回傳 "Connection refused"

**可能原因**：
- SendText Bridge 未安裝或未啟動
- VS Code 未重新載入

**解決方法**：
```bash
# 1. 檢查擴充是否安裝
code --list-extensions | grep sendtext-bridge

# 2. 重新安裝
code --install-extension tools/sendtext-bridge/*.vsix --force

# 3. 重新載入 Window
# Ctrl+Shift+P → Developer: Reload Window
```

---

### 問題 2: Token 檔案不存在

**可能原因**：
- `.agent/state/` 目錄未建立
- SendText Bridge 啟動失敗

**解決方法**：
```bash
# 1. 手動建立目錄
mkdir -p .agent/state

# 2. 重新載入 Window（讓擴充重新啟動）

# 3. 檢查 VS Code 輸出視窗（Output → SendText Bridge）
```

---

### 問題 3: `/wait` 端點一直逾時

**可能原因**：
- Codex CLI 尚未執行完成
- git worktree 不乾淨（有未提交的變更）

**解決方法**：
```bash
# 1. 檢查 git status
git status

# 2. 若有變更，先提交
git add .
git commit -m "Checkpoint"

# 3. 重新執行 auto_execute_plan.sh
```

---

### 問題 4: 文字未發送到正確的終端機

**可能原因**：
- 終端機名稱不是 "Codex CLI"
- 有多個終端機，選錯了

**解決方法**：
修改 `extension.js` 中的終端機名稱：

```javascript
const terminal = vscode.window.terminals.find(t => t.name === 'YOUR_TERMINAL_NAME');
```

---

## 🔒 安全性說明

### 1. 僅限本機存取

HTTP 服務僅監聽 `127.0.0.1`，**不對外開放**。

```javascript
server.listen(port, '127.0.0.1', () => {
  console.log(`Listening on http://127.0.0.1:${port}`);
});
```

### 2. Token 驗證

所有需要認證的端點（`/send`, `/enter`, `/wait`）都需要 Bearer Token。

Token 儲存於 `.agent/state/sendtext_bridge_token`，權限 `600`（僅擁有者可讀）。

### 3. 隨機 Token 生成

Token 使用 `crypto.randomBytes(30).toString('hex')` 生成（40 字元）。

每次 VS Code 重新載入時會重新生成。

### 4. 檔案權限

```bash
chmod 600 .agent/state/sendtext_bridge_token  # 僅擁有者可讀寫
chmod 644 .agent/state/sendtext_bridge_info.json  # 公開可讀
```

### 5. .gitignore 排除

確保敏感檔案不會被提交：

```gitignore
.agent/state/
```

---

## ❓ 常見問題

### Q1: 為什麼要用 HTTP 服務，不直接用 IPC？

**A**: Dev Container 環境中，Shell 腳本無法直接呼叫 VS Code Extension API。HTTP 服務提供了一個標準化的橋接方案，使用 curl 即可呼叫。

---

### Q2: 可以在本機（非 Dev Container）使用嗎？

**A**: 理論上可以，但不推薦。SendText Bridge 設計用於 Dev Container 環境，本機環境有更好的方案（如直接呼叫 VS Code CLI）。

---

### Q3: 可以同時監測多個終端機嗎？

**A**: 目前版本 v0.0.3 不支援。未來版本（v1.2.0）將新增多終端機支援。

---

### Q4: `/wait` 端點會影響效能嗎？

**A**: 輪詢模式會增加 CPU 使用率（每 2 秒執行 `git status`）。未來版本將使用 `inotify` / `fswatch` 優化。

---

### Q5: 可以自訂監測條件嗎？

**A**: 目前版本僅支援 `git status` 監測。可以在 `extension.js` 中修改 `checkCompletion` 函數實現自訂邏輯。

---

### Q6: 如何升級到新版本？

```bash
# 1. 打包新版 VSIX
cd tools/sendtext-bridge
npx --yes @vscode/vsce package

# 2. 安裝新版（--force 覆蓋舊版）
code --install-extension *.vsix --force

# 3. 重新載入 Window
```

---

## 📊 效能考量

### CPU 使用率

**輪詢模式**（`/wait` 端點）：
- 預設每 2 秒執行一次 `git status`
- 對小型專案影響微小（< 1% CPU）
- 大型專案建議調整 `checkInterval` 至 5000ms

**建議**：
```javascript
// 調整輪詢間隔（減少 CPU 使用）
{
  "timeout": 300000,
  "checkInterval": 5000  // 5 秒
}
```

### 記憶體使用

- 擴充本身：< 10 MB
- HTTP 服務：< 5 MB
- 總計：< 15 MB（可忽略不計）

---

## 🔮 未來改進

### v1.2.0 (計畫中)
- [ ] 多終端機支援
- [ ] `/status` 端點（查詢執行狀態）
- [ ] 使用 `inotify` / `fswatch` 取代輪詢
- [ ] WebSocket 即時通知

### v2.0.0 (長期目標)
- [ ] 發佈到 VS Code Marketplace
- [ ] 支援自訂監測條件
- [ ] 進度回報（％ 完成度）
- [ ] 整合 GitHub Actions

---

## 📧 支援與回饋

- **GitHub Issues**: [回報問題](https://github.com/foreverwow001/agent-workflow-template/issues)
- **Discussions**: [討論與建議](https://github.com/foreverwow001/agent-workflow-template/discussions)

---

**版本**: v0.0.3
**最後更新**: 2026-01-13
**作者**: GitHub Copilot
**授權**: MIT License
