# 4-pending.md — Coordinator 專屬 agent skills & MCP PoC 清單 ✅

日期：2026-01-24
作者：GitHub Copilot

---

## 目的 🎯
彙整針對 **Coordinator** 角色（Plan/Gate/審計/簽核）可用的 agent skills 與 MCP server 建議，並依照實作優先順序列出 PoC（Proof-of-Concept）步驟、估時與驗收準則（DoD），供下一步執行與分派。

---

## 快速結論 ✨
- 發現 repo 已具備可立即運用的技能：`plan_validator.py`、`git_stats_reporter.py`、`github_explorer.py`、`test_runner.py`、`code_reviewer.py`（可直接做 PoC）。
- 建議優先採取 **小步快跑**：先把本地 skills 做成 Gate → 再加入 Semgrep 掃描與 Evidence Aggregator → 最後做 MCP server（Task Master / GitMCP）整合與 LangSmith 觀測。这样可以最快獲得 ROI 並維持安全性。

---

## 優先 PoC 清單（依實作順序）

1) Plan Validator（本地 skill，現有） — 低風險 / 快速回報 ✅
   - 為何：強制 Plan 格式與必要標記（例如 `[ENGINEER_DONE]` / `EXECUTION_BLOCK`），避免流程缺漏。
   - 現有檔案：`.agent/skills/plan_validator.py`
   - PoC 步驟：
     1. 對範例 Plan（如 `doc/plans/Idx-YYY*.md` 或 `.agent/plans/1-pending.md`）執行：
        `python .agent/skills/plan_validator.py <plan_file>`
     2. 建 CI job：PR/merge 前執行，若 `status != pass` 則 fail PR。
   - 估時：1–3 小時（CI rule + 簡單報告格式化）
   - 驗收準則（DoD）：輸出 JSON（status: pass|fail|error），CI 能解析並阻擋未通過的 Plan。
   - 依賴：CI runner、測試 Plan 範例。

2) Git Metrics（本地 skill，現有） — 幫助判定 maintainability/UX gate ✅
   - 為何：以變更規模與路徑快速判定是否需更高等級 Review（例如 core/、ui/ 的修改需更嚴格 gate）。
   - 現有檔案：`.agent/skills/git_stats_reporter.py`
   - PoC 步驟：
     1. 在本地產生 diff：`git diff --numstat > /tmp/diff_stats.txt`
     2. 執行：`python .agent/skills/git_stats_reporter.py /tmp/diff_stats.txt`
     3. 將結果串回 PR（或在 CI step 製成 artifact）。
   - 估時：1–3 小時
   - DoD：能產生 `triggers`（maintainability_gate / ui_ux_gate），CI 能根據 triggers 拋出告警。
   - 依賴：CI/PR hook 能夠提供 diff。

3) Test Runner & CI Evidence（本地 skill，現有） — 提供測試/coverage 證據 ✅
   - 為何：Coordinator 需要可驗證的 evidence（測試狀態、coverage）來判定 release gate。
   - 現有檔案：`.agent/skills/test_runner.py`
   - PoC 步驟：在 CI step 執行 `python .agent/skills/test_runner.py` 並把 JSON 結果彙整到證據報告。
   - 估時：1–4 小時（視 CI 複雜度）
   - DoD：能在 PR/Plan 中呈現 `passed/failed`、詳細失敗訊息，且 CI 可根據 fail 使 PR 未通過。

4) Semgrep Wrapper（新 skill） — 安全/政策掃描（高優先）🔒
   - 為何：在任何外部技能引入或 PR 合併之前做安全檢查，降低注入或敏感資訊風險。
   - 建議檔名：`.agent/skills/semgrep_scan.py`
   - PoC 步驟：
     1. 建立基本 rules（或採用 org 規則集）並放置 `semgrep.yml`。
     2. Wrapper 執行：`semgrep --config semgrep.yml --json --output /tmp/semgrep.json`，再轉為 skill JSON 輸出。
     3. CI step：若出現 high-severity findings，則 fail PR。
   - 估時：4–8 小時（含規則選擇與 CI 整合）
   - DoD：能產生 severity-labeled findings、可被 Evidence Aggregator 讀取、CI 能阻擋 high severity findings。
   - 注意：對外 skill（透過 `github_explorer.py` 下載的）在加入前必須跑 semgrep 與 `code_reviewer.py`。

5) Evidence Aggregator（新 skill） — Gate Report 聚合器 🧾
   - 為何：把 Plan Validator / Git Metrics / Semgrep / Test Runner 的輸出彙整成單一 gate report（Markdown + JSON）供 Coordinator 檢閱與審核。
   - 建議檔名：`.agent/skills/evidence_aggregator.py`
   - PoC 步驟：
     1. 定義 aggregator schema（status, checks[], summary, links_to_raw）。
     2. 實作 aggregator 接口，讀取其他 skills 的 JSON 輸出，合成報告並放到 artifact/PR comment。
   - 估時：4–8 小時
   - DoD：可產出 human-readable gate report，並支援 `pass|warn|fail` three-state 判定。

6) Task Parser / Task Master Wrapper（MCP server 或 skill） — 中期目標 🔁
   - 為何：把 PRD/Plan 自動解析為 tasks，支援 Coordinator 的 Task 分配與追蹤（可直接導入 Task Master MCP 或先做輕量 local parser）。
   - 建議做法：先做 local parser skill（`.agent/skills/task_parser.py`）做基本切分與 mapping；通過 PoC 後再接 Task Master MCP。
   - PoC 步驟：
     1. 撰寫 sample Plan，驗證 parser 能輸出 tasks JSON（title, owner, estimate, deps）。
     2. 若成功，再做 Task Master（MCP）整合 PoC（測試 task ↔ Plan 的 round-trip）。
   - 估時：local parser 4–8 小時；Task Master MCP 整合 1–3 天。
   - DoD：能從 Plan 產出至少 5 個可追蹤 tasks，並可回溯到 Plan 位置。

7) LangSmith / Tracing Wrapper（觀測） — 長期優先 🛰️
   - 為何：對於 Agent / Coordinator 的行為追蹤、稽核與可視化很重要（事件追蹤、推斷來源、模型輸出）。
   - 建議檔名：`.agent/skills/langsmith_wrapper.py`（或用現有貴司 observability 平台）。
   - PoC：把 aggregator 的 gate events 上報到 LangSmith（或 OTel endpoint）。
   - 估時：1–2 天（取決於 API 與帳號權限）
   - DoD：可查詢單一 Plan 的 trace 與相關 gate decisions。

8) Approval / Sign-off Skill（整合 GitHub/Slack） — 流程自動化
   - 為何：自動發起審核、收集簽核結果並更新 Plan/PR（需要 audit 與簽章）。
   - 建議檔名：`.agent/skills/approval_signoff.py`
   - 估時：4–8 小時
   - DoD：能發起 sign-off 請求並把結果回寫到 Plan（保留 timestamp 與 reviewer）。

---

## MCP Servers（建議整合）
- **Task Master**：PRD→task parsing、task orchestration（高優先，助力 Coordinator）。
- **GitMCP / Context7 / Serena**：文件化 repo 與 semantic code search（中期優先，可改善 Plan ↔ Code 的對位）。
- **Semgrep MCP**：作為安全 policy 的 central gate（高優先）。
- **MCP Inspector**：用於測試/驗證 MCP server 的兼容性與行為。

> 先以 local skills 做 Proof-of-Value，再逐步把成熟功能接到 MCP server（降低 blast radius）。

---

## 風險、合規與注意事項 ⚠️
- **不得**透過 Codex / OpenCode terminal 直接執行 Git 操作（依 `.agent/roles/coordinator.md` 規範）。
- 新增或下載外部技能前，必須經過 `github_explorer.py` 的 preview → 使用者確認 → `code_reviewer.py` / `semgrep_scan` 的掃描。
- 新技能加入需更新 `skill_manifest.json` 與 `skill_whitelist.json`，並產生審計 log（`audit.log`）。
- 所有 skill 輸出應遵守可被 aggregator 解析的 JSON schema（統一欄位：`status`, `summary`, `details`）。

---

## 建議的 PoC 時程與分工 ⏱️
1. Day 0–1：Plan Validator (CI rule) + Git Stats Reporter (PR hook) — Engineer + QA 簡單驗證（~1–2 日）
2. Day 1–3：Test Runner 整合與 Evidence Aggregator 初版（~1–2 日）
3. Day 3–7：Semgrep Wrapper 與 rule tuning（~2–4 日）
4. Week 2：Task Parser PoC → Task Master MCP PoC（視情況延展）
5. Week 3：LangSmith / Tracing 與 Approval Skill（如有需求）

---

## 下一步（請回覆選擇）
- A) 同意順序並由我先執行 PoC1: **Plan Validator + CI rule**（我會提交 PR，並在 CI 加入測試）。
- B) 先做 **Semgrep Wrapper**（如果你希望先強化安全）。
- C) 先做 **Task Master MCP** PoC（如想優先驗證自動 task 解析）。

---

## 附註
- 相關現有檔案：`.agent/skills/plan_validator.py`, `.agent/skills/git_stats_reporter.py`, `.agent/skills/test_runner.py`, `.agent/skills/code_reviewer.py`, `.agent/skills/github_explorer.py`。
- 參考文件：`.agent/roles/coordinator.md`（必須遵守）、`skill_manifest.json` / `skill_whitelist.json`（上線前需更新）。


---

*檔案由 GitHub Copilot 自動生成供團隊審閱。*
