# 自訂 OpenCode Agents 說明

本專案已配置以下自訂 agents，可以在 OpenCode UI 中通過 Tab 鍵切換選擇：

## 可用 Agents

### 1. meta-expert (Meta 廣告數據專家)
- **用途**：處理 Meta Ads API 整合、數據分析和 KPI 計算
- **專長**：
  - ROAS、CTR、CPC、CPM 等指標計算
  - Meta API 串接和數據提取
  - 廣告數據分析和優化建議
- **權限**：允許檔案編輯和命令執行

### 2. qa-reviewer (品質保證審查員)
- **用途**：程式碼品質審查、測試執行和規範檢查
- **專長**：
  - 程式碼風格和 lint 檢查
  - 測試套件執行和分析
  - 安全漏洞檢測（API key 洩漏等）
  - 檔案長度和複雜度檢查
- **權限**：禁止檔案編輯，只允許命令執行

## 如何使用

1. **在 OpenCode 中啟動**：確保 OpenCode 正在運行
2. **切換 Agent**：使用 Tab 鍵在 Build、Plan、meta-expert、qa-reviewer 之間切換
3. **直接調用**：在訊息中使用 `@meta-expert` 或 `@qa-reviewer`

## 重新載入配置

如果修改後沒有生效：
1. 重新啟動 OpenCode
2. 檢查 OpenCode 是否正確安裝在專案中（確認 .opencode/package.json 存在）

## 配置格式

Agents 使用 Markdown 格式：
- **文件名**：成為 agent 名稱
- **Frontmatter**：YAML 配置（description, mode, model, tools, permissions 等）
- **內容**：系統提示（prompt）

## 配置位置

- Agent 配置文件：`.opencode/agents/` （Markdown 格式）
- 自訂命令：`.opencode/commands/` （Markdown 格式）

## 注意事項

- 自訂 agents 會自動與內建的 `build` 和 `plan` agents 一起載入
- 確保 agent 名稱唯一且有意義
- 根據任務需求配置適當的權限和工具
- Primary agents (mode: primary) 可以通過 Tab 鍵切換
