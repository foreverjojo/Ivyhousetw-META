Ivy House｜CrewAI + OpenRouter + Replit + Streamlit
Meta 週會 MVP → Skills → Multi-Channel → Console Roadmap（Implementation Plan v1）
0) 目標與成功定義（Success Criteria）

核心目標（Phase 1）
每週一次，輸入（Meta Adset CSV + Meta Ads CSV + 官網 Excel）→ deterministic KPI → LLM 洞察（不重算）→ 週會產物（draft/final）→ 全落盤可追溯。

成功定義（Phase 1 必達）

同一份檔案（fingerprint 相同）重跑：不新增版本資料夾

快篩（BCD）→ 最終（BCEF）：同 fp、同 vdir，只補齊缺的產物

任一步失敗：停在當步、有清楚錯誤、可 Force 重跑

history 為真值：UI rerun 不影響真值（重開頁仍可從落盤恢復）

1) Scope 鎖定（避免跑偏）
Phase 1（MVP v1）In Scope：只做這些

Inputs：Meta Adset CSV、Meta Ads CSV、官網 Excel（第一工作表）

Step B：build_report_summary() → report_summary.json

Step C：generate_report_insights() → report_insights.json（只解讀，不重算數字）

Step D：Moderator draft → meeting_draft.md + workflow_state_draft.json

Step E：三顧問 A/B/C → consultant_notes.json

Step F：Moderator final → meeting.md + workflow_state.json

History 落盤結構（week_id 主鍵 + fp 版本 + latest 指標）

Phase 1（MVP v1）Out of Scope：明確不做（先不要碰）

✅ Skills（延後到 Phase 2）

✅ 多智能體 Console UI（延後到 Phase 3）

✅ 蝦皮/ momo 報表解析（延後到 Phase 2）

GA4/CAPI 自動串接、資料庫、排程、權限、多用戶、向量記憶、全功能 BI

依據（推理）：你目前最大風險是「口徑漂移/版本語意漂移」，先把 deterministic+落盤跑穩再擴。

2) Roadmap（把你問的 3 件事明確放進計畫）
Phase 1：Meta + 官網週會 MVP（現在做）

Streamlit Orchestrator + history 落盤

B/C/D/E/F 跑通、可追溯、可驗收

Phase 2：Skills + Multi-Channel 報表擴充（蝦皮 / momo）

加入 Skills 工作（以 repo 文件 + 可測函式契約方式落地，不先做 UI 功能）

新增 adapters：蝦皮廣告/銷售、momo 廣告/銷售

引入 Unified KPI Schema（跨通路同口徑）

Phase 3：Console UI（你截圖那種「多智能體對話介面」方向）

先做 Streamlit 多頁 Console（Run 列表 / 訊息流 / 局部重跑）

再視需要升級成獨立 Web Console（React/Next + API）

3) 架構與檔案結構（可長期維護）
A) 分層原則

Streamlit（app.py）：只管 UI、流程 orchestration、落盤與顯示

scripts/：全是可測試的純函式（deterministic 計算 / LLM 呼叫 / 模板組裝）

schemas/：所有輸出/輸入的 JSON schema 或範例（避免口徑漂移）

docs/：欄位規格、流程規格、驗收規格

history/：真值（每週可追溯）

B) Repo 建議結構
/app.py
/scripts/
  kpi_calc.py
  llm_insights.py
  consultants.py
  moderator.py
  adapters/
    meta_adapter.py
    web_adapter.py
    shopee_ads_adapter.py        (Phase 2)
    shopee_sales_adapter.py      (Phase 2)
    momo_ads_adapter.py          (Phase 2)
    momo_sales_adapter.py        (Phase 2)
/schemas/
  report_summary.v1.json
  report_insights.v1.json
  consultant_notes.v1.json
  workflow_state.v1.json
  unified_kpi.v1.json            (Phase 2)
/docs/
  IMPLEMENTATION_PLAN.md
  FIELD_SPECS_META.md
  FIELD_SPECS_SHOPEE.md          (Phase 2)
  FIELD_SPECS_MOMO.md            (Phase 2)
  ACCEPTANCE_TESTS.md
/history/...

4) 資料與版本規格（不再改語意）
A) week_id

格式固定：YYYY-Www（W 補零）

prev_week 只靠 week_id 排序，不用 date_range 推導

B) fp（版本碼）

fp 只由 deterministic key 產生：
sha/size(meta_adset, meta_ads, web_excel) + detail_level

不含：generated_at、檔名、manual_inputs（若要納入，Phase 2 再討論）

C) latest.json（已修正）

只存相對路徑：rel_path: versions/fp-xxxx

D) mismatch 判斷（避免 inputs.json 缺欄位就亂跳）

mismatch 只用：latest.fp != current_fp_code

5) Milestones（每個都能分派/驗收/復盤）
M0｜環境穩定

交付物：Replit 可跑、secrets 設好、requirements 固定
驗收：Streamlit 起得來，能讀 secrets

M1｜History 落盤與版本規則（你現在已接近完成）

交付物：week_id/fp/latest/inputs/pipeline_state 全落盤
驗收：

同 fp 重跑不新增版本

快篩→最終同 vdir

M2｜Deterministic KPI（B）欄位規格鎖定（關鍵）

交付物：report_summary.json schema v1 + 欄位缺失報錯
驗收：同檔案跑兩次，數字完全一致；缺欄位能指出哪一欄

M3｜LLM 洞察（C）+ 顧問（E）不改數字

交付物：report_insights.json、consultant_notes.json schema v1
驗收：LLM 不得產生另一套 KPI（只引用 report_summary）

M4｜Moderator（D/F）週會模板固定

交付物：meeting_draft/meeting + workflow_state_draft/workflow_state
驗收：每週會議可直接貼用；「策略快照」固定輸出（未填也顯示未填）

6) Skills 工作（Phase 2）要怎麼放，才不會讓 MVP 爆炸

Skills 在這個專案的正確定位：不是 UI 功能，而是「可重用的規格+操作手冊」，同時對應到 scripts 的函式契約與測試。

建議新增（Phase 2）

/skills/parse_reports.md：各通路欄位規格與容錯策略

/skills/generate_insights.md：insights schema、禁重算規則、引用格式

/skills/moderate_meeting.md：meeting 模板固定段落、輸出規範

進入 Phase 2 的門檻

連續 3 週：同 fp 不增資料夾、快篩→最終同 vdir、產物齊全

至少 10 次 run：錯誤可控、可復跑、可追溯 pipeline_state

7) Console UI（Phase 3）— 對齊你截圖的方向，但先走最省成本路線
Phase 3 最小可行 Console（先 Streamlit，多頁）

Page A：Runs 列表（week_id / fp / mode / status / last_step）

Page B：訊息流檢視（顧問 A/B/C/Moderator 分 tab，依 artifacts 呈現）

Page C：局部重跑（只重跑 C 或 E，不動 B；或重跑某顧問）

等你確定多人協作/產品化，再升級成獨立 Console。

8) Multi-Channel（蝦皮 + momo）擴充策略（Phase 2）
原則：Adapter 化 + Unified KPI Schema

每個通路：各自解析 → 統一輸出 unified_kpi.v1.json

Moderator/顧問都只吃 unified schema（避免每加一個通路就改 prompt）

Phase 2 交付物

scripts/adapters/shopee_*、scripts/adapters/momo_*

schemas/unified_kpi.v1.json

meeting 模板新增「通路損益總覽」區塊（Phase 3 或 Phase 2.5）

9) 你可能漏寫但超關鍵的 5 件事（已直接納入計畫）

各通路欄位規格表（Field Specs）

沒有這個就會每週都在修 parsing

文件落點：docs/FIELD_SPECS_*.md

Unified KPI Schema（跨通路同口徑）

沒有就會口徑漂移、Moderator/prompt 每次改

文件落點：schemas/unified_kpi.v1.json（Phase 2）

schemas/ 作為「契約」

每個輸出 JSON 都要有版本化 schema（v1/v2）

減少「後面跟一開始不一樣」

最小驗收測試清單（Acceptance Tests）

不用完整 pytest 也要有 5 個 case（見下一節）

文件落點：docs/ACCEPTANCE_TESTS.md

Meta/蝦皮/momo 匯出欄位固定策略

Meta：你已確定缺欄位用 manual_inputs 補

蝦皮/momo：也要先定「固定匯出欄位」+「缺欄位行為」