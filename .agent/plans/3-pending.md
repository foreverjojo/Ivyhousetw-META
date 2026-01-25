# pending_3.md — Serena + GitMCP vs Context7：分析與建議

**日期**: 2026-01-24
**作者**: GitHub Copilot
**狀態**: pending

---

## 🔎 快速結論（摘要）

- **Serena** 在大型 codebase 的「語意檢索 + 精準編輯」非常有價值，能顯著提高 agent 生成/修改程式碼的精準度與效率。
- **GitMCP** 可快速把 GitHub repository 轉成可被 agent 查詢的文件/代碼入口，短時間內降低 hallucination 並提供即刻成效。
- **Context7**（或 Ref.tools 類）專注於第三方 library/API 的版本化文件，能有效避免 API 誤用，建議作為 docs 補充來源。
- **建議順序**：先做 **Serena + GitMCP** PoC（重點驗證 code-level 編輯與文件上下文整合），同時把 **Semgrep / SonarQube** 作為結果的安全/品質門檻。

---

## 📋 候選 MCP 簡要比較

| MCP | 功能重點 | 優點 | 缺點 | 幫助程度 |
|---|---|---:|---|---:|
| **Serena** | Symbol-level semantic 檢索與編輯 | 精準定位/編輯、token 效率佳、開源 (MIT) | 記憶體/資源需求高、需 LSP/Redis 支援 | **非常高** |
| **GitMCP** | Repo-level docs / code search (fetch/search) | 快速降低 repo hallucination、易上手 | 主要 retrieval、非編輯工具 | **高** |
| **Context7 / Ref.tools** | 版本化 library/API docs | 有版本感知、避免 API misuse | 非編輯工具；可能有配額或商業限制 | **高（API 精確性）** |
| **Semgrep / SonarQube** | 靜態安全 / 品質掃描 | 規則多、可作 CI gate | 需設置規則/整合 | **必要**（品質門檻） |

---

## ✅ PoC 建議（最小可行驗證）

### PoC-A（推薦）— Serena + GitMCP 全流程驗證（3–8 小時）
- 目的：驗證 agent 使用 Serena 做 symbol 級檢索/編輯並依賴 GitMCP 提供文件上下文，最終生成的變更能通過測試與安全掃描。
- 步驟（概要）：
  1. 部署 Serena MCP（docker / `uvx`）並指向本專案（參考：`serena start-mcp-server` 指令）。
  2. 把 `gitmcp.io/{owner}/{repo}` 加為 MCP server（VSCode / Cursor / Claude client 設定）。
  3. 下測試指令：讓 agent "新增 endpoint 並生成對應 unit tests"，觀察生成流程。
  4. 自動執行測試與掃描：`pytest`、`ruff`、`semgrep`（或 SonarQube）並記錄結果。
  5. 成功標準：生成代碼通過測試；semgrep/sonar high/critical findings=0；人工審核可接受。

### PoC-B（快速驗證）— GitMCP 快速接入（1–2 小時）
- 目的：快速驗證 docs/search 對 agent 回應品質的提升。
- 步驟：在本地 client 加入 GitMCP，做有/無 GitMCP 的 A/B 對比測試。

### PoC-C（品質門檻）— Semgrep / SonarQube Gate（2–4 小時）
- 目的：把 agent 產出的變更自動化地做安全與品質檢查，作為 CI gate。

---

## ⚠️ 風險與緩解

- Serena 記憶體/CPU 使用高：先於 subset repo 做測試，設定 LSP/Redis 限制與 cache 策略。
- 有執行權限的 Desktop‑style MCP（例：Desktop Commander）存在權限/安全風險：務必啟用 sandbox、audit log、最小權限。
- 匯入第三方 skill 前請檢查 license（偏好 MIT/Apache）與走 `code_reviewer` 的安全檢查流程。

---

## 🎯 成功標準（KPI）

- PoC 中生成代碼的單元測試通過率 ≥ 95%（小樣本）
- semgrep / SonarQube 中高/致命漏洞為 0 或已被 triage
- agent 回答/生成的準確度（人工或自動化評估）提升 ≥ 20%

---

## ⏱ 時間估計 & 所需角色

- GitMCP 快速接入：1–2 小時（Engineer、Coordinator）
- Serena PoC（完整版）：3–8 小時（Engineer、Infra 支援）
- Semgrep/SonarQube gate：2–4 小時（Engineer、QA）

---

## 下一步（請選一項）

- **A**：執行 **Serena + GitMCP** 全流程 PoC（推薦）
- **B**：先做 **GitMCP 快速接入** 測試（快速回饋）
- **C**：先把 **Context7 / Ref.tools** 加為 library‑docs provider

---

## 參考連結
- Serena: https://github.com/oraios/serena
- GitMCP: https://github.com/idosal/git-mcp / https://gitmcp.io
- Semgrep: https://github.com/returntocorp/semgrep
- SonarQube MCP: https://github.com/SonarSource/sonarqube-mcp-server
- Ref.tools: https://ref.tools/mcp

---

## 🔭 擴展候選（Agent skills 與 MCP wrapper）

- **Aider** — 終端式 pair‑programming / surgical edits。類型：Agent skill（CLI / IDE）; MCP wrapper：`disler/aider-mcp-server` 可用；快速 PoC：在 dev container 以 inline comment 驅動 Aider 做小修，評估速度與正確率。風險：模型調校與執行權限需控制。

- **Sourcery** — 即時重構與 PR code review（IDE + GitHub app）。類型：Agent skill（服務 / IDE 插件）；快速 PoC：開啟 PR 自動建議，量測被接受比例與 code quality 改善。

- **unittest‑ai‑agent**（herchila/unittest‑ai‑agent）— Python unit test 自動生成。類型：Agent skill（CLI）；快速 PoC：為 1–2 個模組自動生成 pytest 測試並執行，評估覆蓋率與穩定性。

- **gpt‑engineer** — 專案生成 / 改進管線，適合 Prototype / feature scaffold。類型：Agent framework（CLI）；PoC：要求改進某 feature 的 codebase 並比較變更量與 test 結果。

- **Diffblue Cover** — 企業級 Java unit test 自動化（有 `diffblue/cover‑mcp` wrapper）。類型：商業產品（MCP wrapper 可使用）；用途：legacy Java code coverage uplift。

- **claude‑task‑master (Task Master)** — 任務拆解與 agent 工作流管理（MCP server, 多工具）。類型：MCP server；用途：把 PRD → 任務 pipeline 編排。

- **Octocode / GitMCP / Ref.tools / Serena**（前述）— 分別提供 research‑driven context、repo‑docs、API docs 與 symbol‑level 編輯能力（已在上文詳細說明）。

- **Semgrep / SonarQube / Snyk** — 靜態分析 / SCA MCPs，用於把 agent 產出做品質與安全的自動門檻。

---

## 🗂 建議實作優先順序（短期 → 長期，含時間估與驗收）

1) **短期：Quick wins（0.5–2 天）**
   - 目標：快速提升 developer productivity 與測試覆蓋。
   - 工具：**BoilrPy**、**smarlhens/python‑boilerplate**（scaffold 範本）、**Sourcery**（PR/IDE）、**unittest‑ai‑agent**。
   - 步驟：preview → download → run `code_reviewer` + `semgrep`/`bandit` → scaffold 範例 → run `pytest`/`ruff` → 若合格加入 `skill_manifest.json`。
   - 成功標準：scaffold 專案能跑通測試（CI / local），Sourcery 建議中 60% 被接受，生成測試通過率 ≥ 90%。

2) **短中期：Docs & Context（1–2 小時到 1 天）**
   - 目標：降低 hallucination，提升回答正確率。
   - 工具：**GitMCP**、**Ref.tools / Context7**。
   - 步驟：把 `gitmcp.io/{owner}/{repo}` 加入 client，做 A/B 測試（有/無 GitMCP），量化回應正確率。

3) **中期：Agent skills PoC（1–2 天）**
   - 目標：把 Aider 一類的 pair‑programming 與 unittest‑ai 的測試生成整合到 daily workflow。
   - 工具：**Aider**（可搭 MCP wrapper）+ **unittest‑ai‑agent**。
   - 成功標準：小修任務平均完成時間下降 ≥ 30%，自動生成測試被 accept 率 ≥ 50%。

4) **關鍵 PoC：Serena（3–8 小時）**
   - 目標：驗證 symbol‑level 檢索/編輯能在大型 repo 中正確定位與修改代碼且減少 token/循環。
   - 步驟：部署 Serena MCP（sse 或 stdio）、連到 agent client、執行「新增 endpoint + 生成 tests」場景，並跑 `pytest` + `semgrep`。
   - 成功標準：功能完整且 semgrep high/critical findings = 0，人工審核通過。

5) **品質門檻：Semgrep / SonarQube / Diffblue（視語言）**
   - 目標：把 agent 產出納入 CI gate（PR 變更前先檢查）。
   - 建議：若 repo 以 Java 為主，啟 Diffblue PoC；若以多語言則先整合 Semgrep 與 SonarQube。

6) **長期：流程化與自動化（數週）**
   - 目標：把 Task Master / Octocode / Octocode Research 等工具列入流程，建立以 research → plan → generate → verify 的閉環。

---

## ✅ 每項 PoC 的共同檢核清單（模板）

- 計畫與目標定義（驗收標準）
- Dependency & license 檢查（MIT/Apache 優先）
- `preview_skill` → 人工確認 → `download_skill`
- 自動化掃描：`code_reviewer`、`semgrep`、`bandit`（若適用）
- 執行測試：`pytest`、`ruff` 等
- 整合 CI gate（PR 時執行）
- 成功與量化指標回報（覆蓋率、測試通過率、接受率、時間節省）

---

## 下一步（請選一項）

- **A**：先做 **BoilrPy + smarlhens/python‑boilerplate**（快速上手 + scaffold PoC，0.5–1 天）
- **B**：先做 **Aider + Sourcery + unittest‑ai‑agent**（短期提升日常開發效率，1–2 天）
- **C**：執行 **Serena + GitMCP** 全流程 PoC（推薦；3–8 小時）
- **D**：整合 **Semgrep / SonarQube** 進 CI 作為品質門檻（1–2 天）
- **E**：把上述 Top 候選加入 `.agent/plans/pending_4.md` 並產出 PoC 清單（我可代為建立）

---

> 備註：本文件為本次「Serena vs GitMCP vs Context7」與擴展 agent skills（如 Aider, Sourcery, unittest‑ai 等）的分析與建議彙整。若要我直接執行 PoC，請回覆 A / B / C / D / E 並指定 owner（要我代跑或交給哪位工程師）。
