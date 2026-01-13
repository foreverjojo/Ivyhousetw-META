# SendText Bridge（Dev Container）

這是一個 VS Code 擴充，會在 **Dev Container（Remote）** 端啟動一個 **僅限本機 `127.0.0.1`** 的 HTTP 服務。
你可以在 container 內用 `curl` / 腳本呼叫它，讓擴充代為執行 VS Code 的 `terminal.sendText(text, shouldExecute)`，達到：

- 把文字「輸入到終端」但 **不按 Enter**（相當於 `sendText(text, false)`）
- 或「輸入並執行」（相當於 `sendText(text, true)`）
- 也能單獨送 Enter

這個方法可以解決：在 Dev Container 內，單純跑 shell 指令無法像本機那樣直接呼叫 VS Code Extension API 的限制。

**註**：內部連結請參考專案 `.agent/scripts/sendtext.sh` 檔案。

---

## 你想達成的效果（最常用）

1) 在對話框說「向 terminal 發送 codex」→ `codex` 直接被送到終端並執行

2) 精準控制互動程式輸入：

- 先送 `/status` **不按 Enter**
- 再單獨送 Enter

---

## 安裝（推薦：用 Remote `code` CLI，避免 UI 一直轉）

此擴充必須安裝在 **Dev Container（Remote extensions）**，不是 Local。

1) 打包 VSIX：

```bash
cd tools/sendtext-bridge
npx --yes @vscode/vsce package --allow-missing-repository --no-dependencies
```

2) 在 container 內直接安裝到 Dev Container：

```bash
code --install-extension tools/sendtext-bridge/sendtext-bridge-*.vsix --force
```

3) 在 VS Code 執行一次 `Developer: Reload Window`（讓 extension 真正啟動）。

---

## 驗證是否安裝/啟動成功

extension 啟動後會：

- 監聽 `http://127.0.0.1:38765/health`
- 寫入 token / info 檔到 `.agent/state/`

在 container 內驗證：

```bash
curl -sS http://127.0.0.1:38765/health
ls -la .agent/state
cat .agent/state/sendtext_bridge_info.json
```

你應該會看到：

- `{"ok":true}`
- `.agent/state/sendtext_bridge_token`
- `.agent/state/sendtext_bridge_info.json`

---

## 使用方式（container 內）

### A) 用 curl（直接呼叫 HTTP bridge）

```bash
TOKEN=$(cat .agent/state/sendtext_bridge_token)

# 只輸入文字，不按 Enter
curl -sS -X POST http://127.0.0.1:38765/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"/status","execute":false}'

# 單獨送 Enter
curl -sS -X POST http://127.0.0.1:38765/enter \
  -H "Authorization: Bearer $TOKEN"
```

### B) 用專案腳本（推薦）

本 repo 已提供封裝腳本位於 `.agent/scripts/sendtext.sh`

範例：

```bash
# 發送並執行（等同 sendText("codex", true)）
./.agent/scripts/sendtext.sh text "codex" --execute

# 先送 /status 不 Enter
./.agent/scripts/sendtext.sh text "/status"

# 再單獨送 Enter
./.agent/scripts/sendtext.sh enter
```

---

## 重要：固定目標 terminal（避免送到錯的終端）

此 bridge **預設永遠發送到一個固定名字的 VS Code terminal：`Codex CLI`**。
這是為了避免「跑腳本的 bash 終端」搶走 active terminal，導致字被送錯地方。

---

## 避免 Python 擴充自動注入 `source .../activate`

如果你發現 terminal 會多出一段：

`source "/workspaces/.../.venv/.../activate"`

那通常是 VS Code 的 Python extension 針對 terminal 自動做「啟動環境」所注入的文字，會干擾像 Codex CLI 這種互動程式。

本 repo 已將下列設定關閉（需要 Reload 才會生效）：

- `.vscode/settings.json`：`python.terminal.activateEnvironment: false`
- `.devcontainer/devcontainer.json`：`python.terminal.activateEnvironment: false`

---

## 設定（Environment Variables）

- `SENDTEXT_BRIDGE_PORT`：預設 `38765`
- `SENDTEXT_BRIDGE_TOKEN`：可選；若有設，會直接使用它，不寫入 token 檔
- `SENDTEXT_BRIDGE_TERMINAL_NAME`：預設 `Codex CLI`（固定發送目標）
