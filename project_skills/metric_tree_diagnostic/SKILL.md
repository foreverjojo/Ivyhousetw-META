---
name: metric-tree-diagnostic
description: Run a deterministic full-funnel metric tree diagnostic for Meta weekly reports; triggers when user asks for 指標樹/全漏斗診斷, summarizes funnel bottlenecks and next actions without guessing missing metrics.
---

# 指標樹診斷法（全漏斗指標樹）

## 何時用

- 使用者要求「執行指標樹診斷法 / 全漏斗診斷 / metric tree」。
- 週報只看到 ROAS 變差，但不知道問題出在「流量/到站/加車/結帳/購買」哪一段。

## 核心邏輯（指標樹）

- **Level 1（結果層）**：先看 ROAS 是否達標（預設 > 2.5；可在 skill 內調整門檻）
- **Level 2（成本層）**：把 ROAS 拆成 `ROAS ≈ AOV / CPA`，判斷是 CPA 變高還是 AOV 變低
- **Level 3（流量層）**：若 CPA 變高，把 CPA 拆成 `CPA ≈ CPM / (CTR × CVR)`，判斷是 CPM 變貴、CTR 下降（素材/受眾訊息）、或 CVR 下降（頁面/產品/結帳）

## 輸入依賴

- `report_summary.json` 的 `kpi.meta.funnel`：
  - `link_clicks`, `landing_page_views`, `add_to_cart`, `initiate_checkout`
- `kpi.meta` 的 spend / purchases / purchase_value / roas

若缺少某些欄位，技能必須明確標示「未提供」，禁止臆測。

## 輸出

在版本資料夾產出 `skill_metric_tree_diagnostic.json`，包含：

- `roas_primary`：若網站 purchase value 為 0 但平台有值，改用 platform ROAS 作主口徑（避免追蹤異常誤判）
- `metric_tree_summary`：三層拆解摘要（Level1/2/3）
- `funnel_rates`：LPV/Click、ATC/LPV、IC/ATC、Purchase/IC、Purchase/LPV
- `suspected_bottlenecks`：推測最可能壞掉的段落（只依輸入數字，不重算 KPI）
- `recommendations`：可落地的下一步（A/B 最小改動）

## 在本專案如何啟動

在「本週手動輸入」的 `note_for_consultants` 或 `analysis_command` 加上關鍵字：

- `執行指標樹診斷法`
- `全漏斗診斷`
- `metric tree`

UI 在 Step C 前會自動執行 deterministic skill，並把結果注入到 LLM 的 `_context.skills` 中，供 Step C/E/F 引用。

## Prompt 範本（貼給 AI）

把這段貼在「給顧問/主持人的備註」或 `analysis_command`：

> 執行「指標樹診斷法（Metric Tree）」：
> Level1 先判斷 ROAS 是否達標（>2.5）。
> 若不達標，Level2 把 ROAS 拆成 AOV/CPA，說明是 CPA 變高還是 AOV 變低。
> 若 CPA 變高，Level3 再把 CPA 拆成 CPM/(CTR×CVR)，指出是 CPM、CTR 或 CVR 哪一段最可能出問題。
> 同時用漏斗事件（Click→LPV→ATC→IC→Purchase）補充定位，並提出 3 個可執行任務（含 KPI/止損）。
