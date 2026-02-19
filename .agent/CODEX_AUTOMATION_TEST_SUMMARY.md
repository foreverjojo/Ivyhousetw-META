# Codex CLI 自動化測試總結

## 測試日期
2026-01-12

## 測試環境
- OS: Debian GNU/Linux 13 (trixie) in Dev Container
- Codex CLI: v0.80.0
- Terminal: VS Code integrated terminal (bash)
- 執行方式: GitHub Copilot 透過 run_in_terminal 工具

## 測試方法與結果

### ✅ 成功的方法

#### 1. `codex exec` 非互動模式
```bash
codex exec "your prompt here"
```

**結果**: ✅ **成功**
- 可正常執行並產出結果
- 適合自動化 QA 流程
- 輸出直接到 stdout，易於擷取
- **已驗證**: 成功完成第三輪 QA 並得到 PASS 判定

**實測案例**:
```bash
codex exec "請審查 Idx-009 的三個檢查點並給出 PASS/FAIL"
# 輸出: PASS (含完整審查過程)
```

---

### ❌ 失敗的方法

#### 2. 帶 prompt 的互動模式
```bash
codex "fix lint errors"
```

**結果**: ❌ **失敗**
- 錯誤: `Error: stdout is not a terminal`
- 原因: Codex 偵測到 stdout 被 redirect/pipe，拒絕啟動互動 TUI

#### 3. Pipe 輸入到 codex
```bash
echo "prompt" | codex
```

**結果**: ❌ **失敗**
- 錯誤: `Error: stdin is not a terminal`
- 原因: Codex 要求 stdin 必須是真實 TTY

#### 4. script 工具模擬 TTY
```bash
script -q -c "codex 'prompt'" /tmp/log
```

**結果**: ❌ **失敗**
- 錯誤: `Error: The cursor position could not be read within a normal duration`
- 原因: Codex TUI 需要完整的 TTY 功能（cursor position, terminal size 等）

#### 5. Python pty 模組
```python
master, slave = pty.openpty()
subprocess.Popen(['codex', prompt], stdin=slave, stdout=slave)
```

**結果**: ❌ **失敗**
- 錯誤: `Error: The cursor position could not be read within a normal duration`
- 原因: 即使有 pseudo-terminal，Codex 仍偵測到不完整的 TTY 環境

#### 6. tmux send-keys（互動模式）
```bash
tmux send-keys -t codex-session "long prompt" C-m
```

**結果**: ❌ **不穩定**
- 問題: 大量文字輸入時，Codex TUI 狀態管理會卡住或不回應
- 原因: Codex 有自己的複雜 TUI 框架，外部注入大量文字會造成狀態不一致

#### 7. expect 腳本
```bash
expect -c 'spawn codex; expect "›"; send "prompt\r"'
```

**結果**: ❌ **環境缺 expect**
- 狀態: Dev Container 未安裝 expect
- 評估: 即使安裝，預期仍會遇到 cursor position 問題

---

## 技術分析

### Codex CLI 的 TTY 檢查機制

Codex CLI 在啟動時會執行以下檢查：
1. **stdin 檢查**: `isatty(0)` - 必須是真實 TTY
2. **stdout 檢查**: `isatty(1)` - 必須是真實 TTY
3. **Cursor position 查詢**: 發送 ANSI escape sequence `\x1b[6n` 並等待回應
4. **Terminal size 查詢**: `ioctl(TIOCGWINSZ)`

### 為何 `codex exec` 可以運作？

`codex exec` 是專為自動化/CI 設計的**非互動模式**：
- 不啟動 TUI
- 不需要 cursor position
- 接受非 TTY 的 stdin/stdout
- 執行完畢直接輸出結果並退出

### 為何其他方法都失敗？

當執行 `codex` 或 `codex "prompt"` 時：
- Codex 會啟動**完整的 TUI**（Terminal User Interface）
- TUI 使用了複雜的終端控制（cursor movement, alternate screen buffer, 等）
- 這些功能需要**真實的 TTY**，pseudo-terminal 無法完全模擬
- GitHub Copilot 透過 `run_in_terminal` 執行命令時，terminal 被 redirect，不符合 Codex 的 TTY 要求

---

## 結論與建議

### 推薦方案

**在自動化場景下，使用 `codex exec`**:

```bash
# 單次 QA
codex exec "$(cat qa_prompt.txt)"

# 整合到腳本
QA_RESULT=$(codex exec "審查 Idx-009 並回答 PASS/FAIL")
if echo "$QA_RESULT" | grep -q "PASS"; then
    echo "QA 通過"
else
    echo "QA 失敗"
fi
```

### 何時使用互動模式

**必須在真實 terminal 手動執行**:
1. 開啟 VS Code Terminal
2. 直接執行 `codex`
3. 手動貼上 prompt 或與 Codex 對話

### PowerShell 可行嗎？

**不可行**。問題不在 shell 類型（bash/PowerShell/zsh），而在：
- Codex CLI 的 TTY 要求
- 自動化工具（run_in_terminal）的 I/O redirect 機制

無論用哪種 shell，只要是透過自動化工具執行，都會遇到相同的 TTY 檢查失敗。

---

## 已驗證的成功案例

### Idx-009 第三輪 QA

**執行方式**:
```bash
codex exec "$(cat .agent/.qa_prompt_round3.txt)"
```

**結果**:
- ✅ 成功審查所有檔案
- ✅ 檢測到 L2 rollback 描述不一致
- ✅ 修正後重新審查，最終判定 PASS

**驗證時間**: 2026-01-12
**總耗時**: ~2-3 分鐘（含 Codex 分析時間）

---

## 更新建議

### 更新 `.agent/scripts/run_codex_template.sh`

把腳本中的 Codex 執行方式改為：
```bash
# 原本（不穩定）
python3 "$TERMINAL_MANAGER" send-command "$TERMINAL_ID" "codex --plan $PLAN_FILE"

# 改為（穩定）
codex exec "$(cat $PLAN_FILE)"
```

### 更新 `.agent/TERMINAL_MANAGEMENT.md`

明確說明：
- Codex 互動模式（`codex`）僅供人工使用
- 自動化場景必須使用 `codex exec`
- Terminal Manager 的 send-command 不適用於 Codex CLI

---

## 參考資料

- Codex CLI 官方文件: https://github.com/openai/codex
- 測試 log 檔案:
  - `.agent/.qa_test.log` - exec 模式成功案例
  - `.agent/.qa_round3_full.log` - 完整 QA 執行記錄
  - `.agent/.qa_final_verdict.log` - 最終 PASS 判定
