# Step C / Step E：即時轉自然語言顯示（UX）改善方案（詳細版）

本文件整理目前討論過的 Step C（LLM 洞察）與 Step E（三顧問）在 Streamlit 中「執行中/完成後」的自然語句呈現策略，並提供 3 組可落地的改善方案（含預期效益與風險）。同時，根據既有 `report_insights.json`（2025-W49 範例）分析，提出「初稿必留欄位」建議（actions 可縮到 6 條）。

---

## 1) 背景與共識

### 1.1 我們要解的問題
- 使用者不需要 token 級 streaming，只希望「生成初稿更快」且過程不要像卡住。
- Step C 與 Step E 目前為同步阻塞呼叫；結果只能在 API 回來後才完整可用。

### 1.2 關鍵限制（很重要）
- **顯示層（`st.text()` / `st.markdown()`）幾乎不會讓 LLM 變快**：Step C/Step E 的主要耗時在 OpenRouter API 生成（token/模型速度/排隊）。
- 顯示層能改善：
  - 等待體感（進度可見、骨架先出）
  - 大量 markdown 重排時的 UI 卡頓（若存在頻繁更新）

---

## 2) 現況觀察（以 2025-W49 的 Step C 產出為例）

參考檔案（單一樣本）：`history/2025-W49/meta/versions/fp-f4ac3026/report_insights.json`

### 2.1 結構與訊息密度
該份 report_insights 包含：
- `executive_summary` 5 條
- `what_worked` 5 條
- `what_didnt` 5 條
- `diagnostics`（traffic / conversion / creative，各為多句）
- `actions` 8 條（每條含 owner/task/why/kpi/stoploss）
- `data_issues` 6 條
- `open_questions` 6 條

### 2.2 token/字數的粗估（用於「縮減」目標）
以該份 JSON 文本做粗估（非精準 tokenizer）：
- 整體約 **~2,900 tokens** 等級
- 其中最大宗是 `actions`（約 **~1,200 tokens** 佔比最高）

> 含意：若要「初稿更快」，最有感的不是改 `st.text()`，而是**縮短輸出（特別是 actions）**、或**改更快模型**、或**改並行（Step E）**。

---

## 3) Step C 初稿：建議必留欄位（actions 減到 6）

目標：在不丟掉「週會可決策」的關鍵資訊前提下，讓 Step C 初稿更短、更快，並且適合直接轉成自然語句顯示。

### 3.1 必留欄位（建議）
1. `insights_version`, `week_id`, `date_range`
2. `executive_summary`（**3–5 條**）：每條 1 句；**允許引用關鍵數字**（但避免在其他欄位重複貼同一組數字）
3. `diagnostics`（每段 **1–2 句**，最多 3 段：traffic / conversion / creative）
4. `actions`（**6 條**固定模板）：每條必含
   - `owner`
   - `task`（一句話）
   - `kpi`（一句話）
   - `stoploss`（一句話）
   - `why`（可選；若保留也建議壓成短語/半句）
5. `data_issues`（**Top 3–5**）：只留「會直接影響決策」的問題
6. `open_questions`（**3–5**）：每條一句話，避免重複 `data_issues`

### 3.2 可合併/去重策略（保留訊息但省字）
針對 2025-W49 範例，最大重複點是「平台/網站回傳不一致」：
- 建議只在 `executive_summary` 用一條寫完整數字與結論
- `data_issues` / `open_questions` 只引用「見重點#1」或用短語描述，不再重貼數字

### 3.3 預期縮短幅度（以同樣資訊密度的保守估計）
如果把 actions 改為 6 條、每條模板化並限字 + diagnostics 限句 + 去重：
- 目標輸出可壓到 **~1,400–1,600 tokens**（相對 ~2,900 約 **-45% ~ -55%**）
- 若生成時間主要被 completion tokens 主導，Step C 生成時間可望 **快約 30%–55%**（依模型與固定延遲而不同）

### 3.4 風險與緩解
- 風險：初稿變短可能讓使用者覺得「不夠細」
  - 緩解：提供「長版」按鈕（或最終流程）再產生完整版；初稿先快，精修再完整
- 風險：模板化過度導致可讀性變差
  - 緩解：自然語句顯示時，採「段落+小標」而非直接 dump JSON

---

## 4) 方案組合（2–3 組）供選擇

下列方案都涵蓋「即時（執行中）自然語句/狀態呈現」；差異在於是否追求「生成更快」與是否對 Step E 做並行。

### 方案 A｜低風險 UX：狀態 + 骨架 + 完成後自然語句（不動 LLM）
**做什麼**
- Step C/E 執行中：
  - 使用 `st.status()` 顯示階段（開始/正在呼叫/完成）
  - 在 `realtime_container` 先顯示 Skeleton（章節標題 +「生成中」）
- Step C/E 完成後：
  - 將 JSON 轉成「自然語句 markdown」一次性渲染

**預期效益**
- 體感提升：等待不再像卡住；使用者知道在跑哪一步
- 幾乎零風險：不改 LLM/資料結構；回歸容易

**風險**
- **總時間不會顯著下降**：LLM 呼叫仍是主要耗時
- 若 Skeleton/狀態設計不佳，可能被視為「多此一舉」

**適用情境**
- 你只想先穩定改善 UX，短時間就上線

---

### 方案 B｜加速初稿優先：Step C 短版輸出 + 自然語句顯示（建議優先做）
**做什麼**
- Step C 改為「短版初稿」：
  - actions 固定 **6 條**、模板化、限字
  - diagnostics 限句
  - 去重（重要數字只在一處出現）
  - 下修 `max_tokens`
- 顯示層仍做方案 A 的 `st.status()` + Skeleton
-（可選）提供「產出完整版」按鈕或在最終流程才跑長版

**預期效益**
- **真正變快**：token 減少 → completion 生成時間下降
- 仍保留週會決策所需：重點 + 診斷 + 6 條可執行行動 + 資料問題/待釐清

**風險**
- 初稿較精簡，少部分使用者可能需要補更多細節
  - 緩解：加「長版」或「追問生成」的 second-pass
- 若限字過嚴，可能造成語句不完整
  - 緩解：用「每條 1–2 句」而非硬砍字元；同時用 JSON schema 限制長度

**適用情境**
- 你最在意 Step C 慢、且不需要 streaming

---

### 方案 C｜整體等待大幅下降：Step E 並行 + 逐顧問自然語句更新（搭配方案 A 或 B）
**做什麼**
- Step E 將三顧問呼叫改為並行（例如 `ThreadPoolExecutor` 同時打 3 個 `requests.post`）
- UI 更新規則：
  - worker thread **不呼叫任何 `st.*`**
  - 主執行緒使用 `as_completed` 取得每位顧問結果後，立即轉自然語句顯示（A/B/C 依完成順序出現）
- Step C 可採 A（只 UX）或 B（短版加速）

**預期效益**
- Step E 總時間接近「最慢的顧問」而不是三者相加
- 使用者會逐段看到 A/B/C 結果（體感也更好）

**風險**
- 可能碰到 OpenRouter rate limit / timeout（同時三發）
  - 緩解：加入 retry/backoff；必要時限制最大並行數=2；或針對模型設置不同 timeout
- Streamlit threading/狀態同步踩雷（若在 worker 呼叫 `st.*`）
  - 緩解：嚴格保持 UI 更新在主執行緒；callback 只傳資料，不直接渲染

**適用情境**
- 你覺得 Step E 也慢，且願意承擔中等改動（但不是 streaming 的高複雜度）

---

## 5) 建議的落地優先序
1. **先做方案 B（Step C 短版初稿）**：這是最直接的速度提升來源
2. 同步做方案 A 的 UX（status + skeleton）：體感與可用性提升，且不影響邏輯
3. 若 Step E 仍痛，再做方案 C 的並行化（比 streaming 風險低、收益高）

---

## 6) 驗收方式（可量化）
- Step C：
  - completion tokens（從 OpenRouter usage）是否下降到目標（例如 ~45–55%）
  - p50/p90 生成時間是否下降（至少 p50 顯著下降）
  - 初稿是否能直接在週會派工（actions 6 條是否足夠）
- Step E：
  - 並行後總時間是否接近 max(A,B,C) 而非 sum(A+B+C)
  - 失敗情境（單顧問 timeout/429）是否仍能產出部分結果並提示

